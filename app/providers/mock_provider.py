from __future__ import annotations

from app.models import IncidentReport, RecommendedAction, RootCauseHypothesis
from app.results import RecommendationResult
from app.providers.base import LLMProvider


class MockProvider(LLMProvider):
    async def generate_recommendations(self, report: IncidentReport) -> RecommendationResult | None:
        hypotheses = [
            RootCauseHypothesis(
                hypothesis="Mock: recent rollout or resource pressure", confidence=0.45
            )
        ]
        actions = [
            RecommendedAction(
                action="Check pod events and rollout status for the affected namespace",
                risk="low",
                confidence=0.5,
            ),
            RecommendedAction(
                action="Verify image pull secrets and recent deployment changes",
                risk="low",
                confidence=0.4,
            ),
        ]
        return RecommendationResult(recommended_actions=actions, root_cause_hypotheses=hypotheses)
