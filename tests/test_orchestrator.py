import pytest

from app.models import IncidentReport
from app.orchestrator import Orchestrator
from app.store import Store, now_utc
from app.integrations.slack import SlackClient


@pytest.mark.asyncio
async def test_orchestrator_pipeline(tmp_path):
    store = Store(redis_url="redis://localhost:6379/0", sqlite_path=str(tmp_path / "incidents.db"))
    await store.connect()
    slack = SlackClient(webhook_url=None)
    orch = Orchestrator(store=store, slack=slack)
    report = IncidentReport(
        incident_id="inc-2",
        correlation_id="corr-2",
        status="new",
        incident_type="rollout_failure",
        severity="high",
        summary="Rollout failed",
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    result = await orch._triage(report)
    assert result.status == "investigating"
    await store.close()
