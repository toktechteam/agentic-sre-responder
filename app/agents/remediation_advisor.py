from __future__ import annotations

import os

from app.logging_config import get_logger
from app.models import IncidentReport, RecommendedAction
from app.results import RecommendationResult
from app.providers.base import LLMProvider
from app.providers.bedrock_provider import BedrockProvider
from app.providers.mock_provider import MockProvider
from app.providers.openai_provider import OpenAIProvider

logger = get_logger(__name__)


async def recommend_actions(report: IncidentReport) -> RecommendationResult:
    provider = _get_provider()

    # 🔹 CRITICAL: log which LLM is actually being used
    logger.info(
        "llm_provider_selected",
        extra={
            "provider": provider.__class__.__name__,
            "incident_id": report.incident_id,
        },
    )

    try:
        response = await provider.generate_recommendations(report)
    except Exception as exc:
        logger.exception(
            "llm_provider_failed",
            extra={
                "provider": provider.__class__.__name__,
                "incident_id": report.incident_id,
                "error": str(exc),
            },
        )
        response = None

    # 🔹 SAFE fallback (never breaks demo)
    if response is None:
        logger.warning(
            "llm_fallback_used",
            extra={"incident_id": report.incident_id},
        )
        fallback_actions = [
            RecommendedAction(
                action="Review recent deployment changes and check pod events for failures",
                risk="low",
                confidence=0.4,
            )
        ]
        return RecommendationResult(recommended_actions=fallback_actions)

    return response


def _get_provider() -> LLMProvider:
    provider = os.environ.get("LLM_PROVIDER", "mock").lower()

    if provider == "openai":
        return OpenAIProvider()

    if provider == "bedrock":
        return BedrockProvider()

    # default + safety net
    return MockProvider()

