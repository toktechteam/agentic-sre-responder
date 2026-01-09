import pytest

from app.models import IncidentReport
from app.store import Store, now_utc


@pytest.mark.asyncio
async def test_store_roundtrip(tmp_path):
    store = Store(redis_url="redis://localhost:6379/0", sqlite_path=str(tmp_path / "incidents.db"))
    await store.connect()
    report = IncidentReport(
        incident_id="inc-1",
        correlation_id="corr-1",
        status="new",
        incident_type="crashloop",
        severity="high",
        summary="CrashLoop detected",
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    await store.save_incident_report(report)
    fetched = await store.get_incident_report("inc-1")
    assert fetched is not None
    assert fetched.incident_id == "inc-1"
    await store.close()
