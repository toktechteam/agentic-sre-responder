from __future__ import annotations

from kubernetes import client, config
from kubernetes.client import ApiException

from app.logging_config import get_logger
from app.models import Evidence, IncidentReport
from app.results import InvestigationResult

logger = get_logger(__name__)


async def k8s_investigation(report: IncidentReport) -> InvestigationResult:
    evidence: list[Evidence] = []
    links: list[str] = []

    # Load Kubernetes config
    try:
        config.load_incluster_config()
    except Exception:
        try:
            config.load_kube_config()
        except Exception as exc:
            logger.exception("kube_config_load_failed", extra={"error": str(exc)})
            evidence.append(
                Evidence(
                    source="k8s",
                    detail="Failed to load Kubernetes config",
                    severity="error",
                )
            )
            return InvestigationResult(evidence=evidence, links=links)

    core = client.CoreV1Api()
    apps = client.AppsV1Api()
    autoscaling = client.AutoscalingV1Api()

    namespace = _extract_namespace(report)

    # ---- REAL CLUSTER INSPECTION ----
    evidence.extend(_collect_pod_status(core, namespace))
    evidence.extend(_collect_events(core, namespace))
    evidence.extend(_collect_deployments(apps, namespace))
    evidence.extend(_collect_nodes(core))
    evidence.extend(_collect_hpas(autoscaling, namespace))
    evidence.extend(_collect_pod_logs(core, namespace))

    # ---- DEMO MODE EVIDENCE INJECTION ----
    _inject_demo_evidence(report, evidence)

    links.extend(_kubectl_links(namespace))
    return InvestigationResult(evidence=evidence, links=links)


# =========================
# DEMO EVIDENCE INJECTION
# =========================

def _inject_demo_evidence(report: IncidentReport, evidence: list[Evidence]) -> None:
    incident_type = report.incident_type.lower()

    if incident_type == "crashloop":
        evidence.extend(
            [
                Evidence(
                    source="kubernetes",
                    detail="Pod app-a is in CrashLoopBackOff with restart count > 5",
                    severity="error",
                ),
                Evidence(
                    source="container",
                    detail="Container startup failed due to missing required env var APP_A_REQUIRED",
                    severity="error",
                ),
                Evidence(
                    source="logs",
                    detail="Application logs: ValueError: APP_A_REQUIRED environment variable not set",
                    severity="error",
                ),
            ]
        )

    elif incident_type == "rollout_failure":
        evidence.extend(
            [
                Evidence(
                    source="deployment",
                    detail="Deployment app-b rollout failed: ImagePullBackOff",
                    severity="error",
                ),
                Evidence(
                    source="kubernetes",
                    detail="ReplicaSet app-b has 0 available replicas out of 1 desired",
                    severity="error",
                ),
                Evidence(
                    source="events",
                    detail="Failed to pull image demo-app-b:doesnotexist",
                    severity="error",
                ),
            ]
        )

    elif incident_type == "high_latency":
        evidence.extend(
            [
                Evidence(
                    source="application",
                    detail="High request latency detected (>3s p95) for app-a service",
                    severity="warning",
                ),
                Evidence(
                    source="config",
                    detail="ConfigMap app-a-config has LATENCY_MODE=on",
                    severity="warning",
                ),
                Evidence(
                    source="logs",
                    detail="Application logs indicate artificial latency injection enabled",
                    severity="info",
                ),
            ]
        )


# =========================
# HELPERS
# =========================

def _extract_namespace(report: IncidentReport) -> str:
    labels = report.raw_alert.get("labels", {}) if report.raw_alert else {}
    return labels.get("namespace") or "default"


def _collect_pod_status(core: client.CoreV1Api, namespace: str) -> list[Evidence]:
    evidence: list[Evidence] = []
    try:
        pods = core.list_namespaced_pod(namespace=namespace)
    except ApiException as exc:
        return [
            Evidence(
                source="k8s",
                detail=f"Failed to list pods: {exc}",
                severity="error",
            )
        ]

    for pod in pods.items:
        status = pod.status.phase or "unknown"
        restarts = 0
        reason = None

        if pod.status.container_statuses:
            for container in pod.status.container_statuses:
                restarts += container.restart_count or 0
                if container.state and container.state.waiting:
                    reason = container.state.waiting.reason

        detail = f"Pod {pod.metadata.name} status={status} restarts={restarts} reason={reason}"
        severity = "warning" if restarts > 0 or reason else "info"
        evidence.append(Evidence(source="k8s", detail=detail, severity=severity))

    return evidence


def _collect_events(core: client.CoreV1Api, namespace: str) -> list[Evidence]:
    evidence: list[Evidence] = []
    try:
        events = core.list_namespaced_event(namespace=namespace)
    except ApiException as exc:
        return [
            Evidence(
                source="k8s",
                detail=f"Failed to list events: {exc}",
                severity="error",
            )
        ]

    for event in events.items[-20:]:
        if getattr(event, "type", None) == "Warning":
            evidence.append(
                Evidence(
                    source="events",
                    detail=f"{event.reason}: {event.message}",
                    severity="warning",
                )
            )
    return evidence


def _collect_deployments(apps: client.AppsV1Api, namespace: str) -> list[Evidence]:
    evidence: list[Evidence] = []
    try:
        deployments = apps.list_namespaced_deployment(namespace=namespace)
    except ApiException as exc:
        return [
            Evidence(
                source="k8s",
                detail=f"Failed to list deployments: {exc}",
                severity="error",
            )
        ]

    for deployment in deployments.items:
        desired = deployment.spec.replicas or 0
        available = deployment.status.available_replicas or 0
        severity = "warning" if available < desired else "info"

        evidence.append(
            Evidence(
                source="deployment",
                detail=f"Deployment {deployment.metadata.name} desired={desired} available={available}",
                severity=severity,
            )
        )

    return evidence


def _collect_nodes(core: client.CoreV1Api) -> list[Evidence]:
    evidence: list[Evidence] = []
    try:
        nodes = core.list_node()
    except ApiException as exc:
        return [
            Evidence(
                source="k8s",
                detail=f"Failed to list nodes: {exc}",
                severity="error",
            )
        ]

    for node in nodes.items:
        for condition in node.status.conditions or []:
            if condition.type in {"DiskPressure", "MemoryPressure", "PIDPressure"} and condition.status == "True":
                evidence.append(
                    Evidence(
                        source="node",
                        detail=f"Node {node.metadata.name} has {condition.type}",
                        severity="warning",
                    )
                )
    return evidence


def _collect_hpas(autoscaling: client.AutoscalingV1Api, namespace: str) -> list[Evidence]:
    evidence: list[Evidence] = []
    try:
        hpas = autoscaling.list_namespaced_horizontal_pod_autoscaler(namespace=namespace)
    except ApiException as exc:
        return [
            Evidence(
                source="k8s",
                detail=f"Failed to list HPA: {exc}",
                severity="error",
            )
        ]

    for hpa in hpas.items:
        current = hpa.status.current_replicas or 0
        desired = hpa.status.desired_replicas or 0
        severity = "warning" if current != desired else "info"

        evidence.append(
            Evidence(
                source="hpa",
                detail=f"HPA {hpa.metadata.name} current={current} desired={desired}",
                severity=severity,
            )
        )

    return evidence


def _collect_pod_logs(
    core: client.CoreV1Api,
    namespace: str,
    tail_lines: int = 50,
) -> list[Evidence]:
    evidence: list[Evidence] = []
    try:
        pods = core.list_namespaced_pod(namespace=namespace)
    except ApiException:
        return evidence

    for pod in pods.items:
        if not pod.status.container_statuses:
            continue

        for container in pod.status.container_statuses:
            if container.restart_count and container.restart_count > 0:
                try:
                    logs = core.read_namespaced_pod_log(
                        name=pod.metadata.name,
                        namespace=namespace,
                        container=container.name,
                        tail_lines=tail_lines,
                    )
                    snippet = " ".join(logs.splitlines()[-3:])
                    evidence.append(
                        Evidence(
                            source="logs",
                            detail=f"{pod.metadata.name}/{container.name}: {snippet}",
                            severity="warning",
                        )
                    )
                except ApiException:
                    pass

    return evidence


def _kubectl_links(namespace: str) -> list[str]:
    return [
        f"kubectl get pods -n {namespace}",
        f"kubectl get events -n {namespace} --sort-by=.lastTimestamp",
        f"kubectl describe deployment -n {namespace}",
    ]

