import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from kubernetes import client, config
from kubernetes.client import ApiException

from app.logging_config import configure_logging, get_logger
from app.models import DemoAttackRequest, DemoInjectRequest, DemoWorkloadStatus, IncidentReport, IncidentSummary
from app.orchestrator import Orchestrator
from app.store import Store
from app.integrations.slack import SlackClient

logger = get_logger(__name__)

app = FastAPI(title="agentic-sre-responder", version="0.1.0")

DEMO_WORKLOADS = [
    {"namespace": "ns-a", "name": "app-a", "label_selector": "app=app-a", "configmap": "app-a-config"},
    {"namespace": "ns-b", "name": "app-b", "label_selector": "app=app-b"},
]


def _correlation_id(x_correlation_id: str | None) -> str:
    return x_correlation_id or str(uuid.uuid4())


@app.on_event("startup")
async def startup() -> None:
    configure_logging()
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    sqlite_path = os.environ.get("SQLITE_PATH", "/data/incidents.db")
    slack_webhook = os.environ.get("SLACK_WEBHOOK_URL")
    store = Store(redis_url=redis_url, sqlite_path=sqlite_path)
    await store.connect()
    slack = SlackClient(webhook_url=slack_webhook)
    orchestrator = Orchestrator(store=store, slack=slack)
    app.state.store = store
    app.state.orchestrator = orchestrator
    logger.info("startup_complete")


@app.on_event("shutdown")
async def shutdown() -> None:
    store: Store = app.state.store
    await store.close()
    logger.info("shutdown_complete")


def get_store() -> Store:
    return app.state.store


def get_orchestrator() -> Orchestrator:
    return app.state.orchestrator


def _load_cluster_config() -> None:
    try:
        config.load_incluster_config()
    except Exception:
        try:
            config.load_kube_config()
        except Exception as exc:
            logger.exception("kube_config_load_failed", extra={"error": str(exc)})
            raise HTTPException(status_code=503, detail="kube_config_unavailable") from exc


def _build_demo_attacker_client() -> client.ApiClient:
    token_path = os.environ.get("DEMO_ATTACKER_TOKEN_PATH")
    kubeconfig_path = os.environ.get("DEMO_ATTACKER_KUBECONFIG")
    if token_path:
        token_file = Path(token_path)
        if not token_file.exists():
            raise HTTPException(status_code=503, detail="demo_attacker_token_missing")
        token = token_file.read_text().strip()
        if not token:
            raise HTTPException(status_code=503, detail="demo_attacker_token_empty")
        host = os.environ.get("KUBERNETES_SERVICE_HOST")
        port = os.environ.get("KUBERNETES_SERVICE_PORT")
        if not host or not port:
            raise HTTPException(status_code=503, detail="demo_attacker_cluster_env_missing")
        configuration = client.Configuration()
        configuration.host = f"https://{host}:{port}"
        configuration.verify_ssl = True
        ca_path = os.environ.get("DEMO_ATTACKER_CA_PATH", "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
        if os.path.exists(ca_path):
            configuration.ssl_ca_cert = ca_path
        configuration.api_key = {"authorization": f"Bearer {token}"}
        return client.ApiClient(configuration)
    if kubeconfig_path:
        config.load_kube_config(config_file=kubeconfig_path)
        return client.ApiClient()
    raise HTTPException(status_code=503, detail="demo_attacker_credentials_not_configured")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/alert", response_model=IncidentReport)
async def alert_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_correlation_id: str | None = Header(default=None),
    store: Store = Depends(get_store),
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> IncidentReport:
    try:
        payload: dict[str, Any] = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid_json") from exc

    correlation_id = _correlation_id(x_correlation_id)
    report = await orchestrator.handle_alert(
        payload=payload,
        source="alertmanager",
        correlation_id=correlation_id,
        background_tasks=background_tasks,
    )
    return report


@app.post("/demo/inject", response_model=IncidentReport)
async def demo_inject(
    payload: DemoInjectRequest,
    background_tasks: BackgroundTasks,
    x_correlation_id: str | None = Header(default=None),
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> IncidentReport:
    correlation_id = _correlation_id(x_correlation_id)
    report = await orchestrator.handle_demo_alert(
        demo_request=payload,
        correlation_id=correlation_id,
        background_tasks=background_tasks,
    )
    return report


@app.post("/demo/attack")
async def demo_attack(payload: DemoAttackRequest) -> dict[str, str]:
    api_client = _build_demo_attacker_client()
    apps = client.AppsV1Api(api_client=api_client)
    core = client.CoreV1Api(api_client=api_client)

    try:
        if payload.attack_type == "crashloop":
            body = {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [
                                {"name": "app-a", "env": [{"name": "APP_A_REQUIRED", "value": ""}]}
                            ]
                        }
                    }
                }
            }
            apps.patch_namespaced_deployment(name="app-a", namespace="ns-a", body=body)
            return {"status": "ok", "attack": "crashloop", "target": "ns-a/app-a"}
        if payload.attack_type == "rollout_failure":
            body = {
                "spec": {
                    "template": {
                        "spec": {"containers": [{"name": "app-b", "image": "demo-app-b:doesnotexist"}]}
                    }
                }
            }
            apps.patch_namespaced_deployment(name="app-b", namespace="ns-b", body=body)
            return {"status": "ok", "attack": "rollout_failure", "target": "ns-b/app-b"}
        if payload.attack_type == "high_latency":
            config_map = core.read_namespaced_config_map(name="app-a-config", namespace="ns-a")
            current = (config_map.data or {}).get("LATENCY_MODE", "off")
            if payload.enabled is None:
                next_value = "off" if current == "on" else "on"
            else:
                next_value = "on" if payload.enabled else "off"
            core.patch_namespaced_config_map(
                name="app-a-config",
                namespace="ns-a",
                body={"data": {"LATENCY_MODE": next_value}},
            )
            return {"status": "ok", "attack": "high_latency", "target": "ns-a/app-a"}
    except ApiException as exc:
        logger.exception("demo_attack_failed", extra={"error": str(exc)})
        raise HTTPException(status_code=exc.status or 500, detail="demo_attack_failed") from exc
    raise HTTPException(status_code=400, detail="unsupported_attack_type")


@app.get("/demo/workloads", response_model=list[DemoWorkloadStatus])
async def demo_workloads() -> list[DemoWorkloadStatus]:
    _load_cluster_config()
    core = client.CoreV1Api()
    apps = client.AppsV1Api()
    statuses: list[DemoWorkloadStatus] = []

    for workload in DEMO_WORKLOADS:
        namespace = workload["namespace"]
        name = workload["name"]
        label_selector = workload["label_selector"]
        try:
            deployment = apps.read_namespaced_deployment(name=name, namespace=namespace)
        except ApiException as exc:
            status = "missing" if exc.status == 404 else "error"
            statuses.append(
                DemoWorkloadStatus(
                    namespace=namespace,
                    workload=name,
                    desired_replicas=0,
                    ready_replicas=0,
                    available_replicas=0,
                    restarts=0,
                    status=status,
                    message="deployment_not_found" if exc.status == 404 else "deployment_lookup_failed",
                )
            )
            continue

        desired = deployment.spec.replicas or 0
        ready = deployment.status.ready_replicas or 0
        available = deployment.status.available_replicas or 0
        restarts = 0
        message = None
        try:
            pods = core.list_namespaced_pod(namespace=namespace, label_selector=label_selector)
            for pod in pods.items:
                if pod.status.container_statuses:
                    for container in pod.status.container_statuses:
                        restarts += container.restart_count or 0
                        if container.state and container.state.waiting and container.state.waiting.reason:
                            message = container.state.waiting.reason
        except ApiException:
            message = "pod_lookup_failed"

        status = "healthy" if desired > 0 and ready == desired else "degraded"
        statuses.append(
            DemoWorkloadStatus(
                namespace=namespace,
                workload=name,
                desired_replicas=desired,
                ready_replicas=ready,
                available_replicas=available,
                restarts=restarts,
                status=status,
                message=message,
            )
        )

    return statuses


@app.get("/incidents", response_model=list[IncidentSummary])
async def list_incidents(store: Store = Depends(get_store)) -> list[IncidentSummary]:
    return await store.list_incidents()


@app.get("/incidents/{incident_id}", response_model=IncidentReport)
async def get_incident(incident_id: str, store: Store = Depends(get_store)) -> IncidentReport:
    report = await store.get_incident_report(incident_id)
    if report is None:
        raise HTTPException(status_code=404, detail="not_found")
    return report


@app.post("/slack/ack")
async def slack_ack(request: Request) -> JSONResponse:
    payload = await request.json()
    logger.info("slack_ack_received", extra={"payload": payload})
    return JSONResponse({"status": "acknowledged"})
