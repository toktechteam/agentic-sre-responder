from __future__ import annotations

from abc import ABC, abstractmethod

from app.models import IncidentReport
from app.results import RecommendationResult

class LLMProvider(ABC):
    @abstractmethod
    async def generate_recommendations(self, report: IncidentReport) -> RecommendationResult | None:
        raise NotImplementedError
