import pytest

from app.models import IncidentReport
from app.providers.mock_provider import MockProvider
from app.store import now_utc


@pytest.mark.asyncio
async def test_mock_provider():
    provider = MockProvider()
    report = IncidentReport(
        incident_id="inc-3",
        correlation_id="corr-3",
        status="new",
        incident_type="high_latency",
        severity="medium",
        summary="Latency spike",
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    result = await provider.generate_recommendations(report)
    assert result is not None
    assert result.recommended_actions
