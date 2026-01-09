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

    # In-cluster first (KIND pod), fallback to kubeconfig for local runs
    try:
        config.load_incluster_config()
    except Exception:
        try:
            config.load_kube_config()
        except Exception as exc:
            logger.exception("kube_config_load_failed", extra={"error": str(exc)})
            evidence.append(Evidence(source="k8s", detail="Failed to load Kubernetes config", severity="error"))
            return InvestigationResult(evidence=evidence, links=links)

    core = client.CoreV1Api()
    apps = client.AppsV1Api()
    autoscaling = client.AutoscalingV1Api()

    namespace = _extract_namespace(report)

    evidence.extend(_collect_pod_status(core, namespace))
    evidence.extend(_collect_events(core, namespace))
    evidence.extend(_collect_deployments(apps, namespace))
    evidence.extend(_collect_nodes(core))
    evidence.extend(_collect_hpas(autoscaling, namespace))
    evidence.extend(_collect_pod_logs(core, namespace))

    links.extend(_kubectl_links(namespace))
    return InvestigationResult(evidence=evidence, links=links)


def _extract_namespace(report: IncidentReport) -> str:
    labels = report.raw_alert.get("labels", {}) if report.raw_alert else {}
    return labels.get("namespace") or "default"


def _collect_pod_status(core: client.CoreV1Api, namespace: str) -> list[Evidence]:
    evidence: list[Evidence] = []
    try:
        pods = core.list_namespaced_pod(namespace=namespace)
    except ApiException as exc:
        return [Evidence(source="k8s", detail=f"Failed to list pods: {exc}", severity="error")]

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
        return [Evidence(source="k8s", detail=f"Failed to list events: {exc}", severity="error")]

    for event in events.items[-20:]:
        if getattr(event, "type", None) == "Warning":
            detail = f"Event {event.reason}: {event.message}"
            evidence.append(Evidence(source="k8s", detail=detail, severity="warning"))
    return evidence


def _collect_deployments(apps: client.AppsV1Api, namespace: str) -> list[Evidence]:
    evidence: list[Evidence] = []
    try:
        deployments = apps.list_namespaced_deployment(namespace=namespace)
    except ApiException as exc:
        return [Evidence(source="k8s", detail=f"Failed to list deployments: {exc}", severity="error")]

    for deployment in deployments.items:
        desired = deployment.spec.replicas or 0
        available = deployment.status.available_replicas or 0
        detail = f"Deployment {deployment.metadata.name} replicas desired={desired} available={available}"
        severity = "warning" if available < desired else "info"
        evidence.append(Evidence(source="k8s", detail=detail, severity=severity))
        if deployment.status.conditions:
            for condition in deployment.status.conditions:
                if condition.status == "False":
                    evidence.append(
                        Evidence(
                            source="k8s",
                            detail=f"Deployment {deployment.metadata.name} condition {condition.type}: {condition.message}",
                            severity="warning",
                        )
                    )
    return evidence


def _collect_nodes(core: client.CoreV1Api) -> list[Evidence]:
    evidence: list[Evidence] = []
    try:
        nodes = core.list_node()
    except ApiException as exc:
        return [Evidence(source="k8s", detail=f"Failed to list nodes: {exc}", severity="error")]

    for node in nodes.items:
        if not node.status.conditions:
            continue
        for condition in node.status.conditions:
            if condition.type in {"DiskPressure", "MemoryPressure", "PIDPressure"} and condition.status == "True":
                detail = f"Node {node.metadata.name} has {condition.type}"
                evidence.append(Evidence(source="k8s", detail=detail, severity="warning"))
    return evidence


def _collect_hpas(autoscaling: client.AutoscalingV1Api, namespace: str) -> list[Evidence]:
    evidence: list[Evidence] = []
    try:
        hpas = autoscaling.list_namespaced_horizontal_pod_autoscaler(namespace=namespace)
    except ApiException as exc:
        return [Evidence(source="k8s", detail=f"Failed to list HPA: {exc}", severity="error")]

    for hpa in hpas.items:
        current = hpa.status.current_replicas or 0
        desired = hpa.status.desired_replicas or 0
        detail = f"HPA {hpa.metadata.name} replicas current={current} desired={desired}"
        severity = "warning" if current != desired else "info"
        evidence.append(Evidence(source="k8s", detail=detail, severity=severity))
    return evidence


def _collect_pod_logs(core: client.CoreV1Api, namespace: str, tail_lines: int = 50) -> list[Evidence]:
    evidence: list[Evidence] = []
    try:
        pods = core.list_namespaced_pod(namespace=namespace)
    except ApiException:
        return evidence

    for pod in pods.items:
        if not pod.status.container_statuses:
            continue
        for container_status in pod.status.container_statuses:
            if container_status.restart_count and container_status.restart_count > 0:
                try:
                    log = core.read_namespaced_pod_log(
                        name=pod.metadata.name,
                        namespace=namespace,
                        container=container_status.name,
                        tail_lines=tail_lines,
                    )
                    snippet = " ".join(log.splitlines()[-3:])
                    detail = f"Logs {pod.metadata.name}/{container_status.name}: {snippet}"
                    evidence.append(Evidence(source="k8s", detail=detail, severity="warning"))
                except ApiException as exc:
                    evidence.append(
                        Evidence(
                            source="k8s",
                            detail=f"Failed to read logs for {pod.metadata.name}: {exc}",
                            severity="error",
                        )
                    )
    return evidence


def _kubectl_links(namespace: str) -> list[str]:
    return [
        f"kubectl get pods -n {namespace}",
        f"kubectl get events -n {namespace} --sort-by=.lastTimestamp",
        f"kubectl describe deployment -n {namespace}",
    ]

