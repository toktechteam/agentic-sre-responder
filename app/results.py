# app/results.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from app.models import Evidence, RecommendedAction, RootCauseHypothesis


@dataclass
class InvestigationResult:
    evidence: List[Evidence]
    links: List[str]


@dataclass
class RecommendationResult:
    recommended_actions: List[RecommendedAction]
    root_cause_hypotheses: Optional[List[RootCauseHypothesis]] = None


@dataclass
class TriageResult:
    evidence: List[Evidence]

