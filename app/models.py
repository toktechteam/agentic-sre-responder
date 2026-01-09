from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TimelineEvent(BaseModel):
    stage: str
    status: Literal["started", "completed"]
    timestamp: datetime


class Evidence(BaseModel):
    source: str
    detail: str
    severity: Literal["info", "warning", "error"] = "info"


class RootCauseHypothesis(BaseModel):
    hypothesis: str
    confidence: float = Field(ge=0.0, le=1.0)


class RecommendedAction(BaseModel):
    action: str
    risk: Literal["low", "medium", "high"]
    confidence: float = Field(ge=0.0, le=1.0)


class StageTiming(BaseModel):
    stage: str
    started_at: datetime
    completed_at: datetime | None = None

    @property
    def duration_ms(self) -> int | None:
        if self.completed_at is None:
            return None
        delta = self.completed_at - self.started_at
        return int(delta.total_seconds() * 1000)


class IncidentReport(BaseModel):
    incident_id: str
    correlation_id: str
    status: Literal["new", "investigating", "recommended", "validated"]
    incident_type: str
    severity: str
    summary: str
    created_at: datetime
    updated_at: datetime
    timeline: list[TimelineEvent] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    root_cause_hypotheses: list[RootCauseHypothesis] = Field(default_factory=list)
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    stage_timings: list[StageTiming] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    raw_alert: dict[str, Any] = Field(default_factory=dict)


class IncidentSummary(BaseModel):
    incident_id: str
    correlation_id: str
    status: str
    incident_type: str
    severity: str
    summary: str
    created_at: datetime
    updated_at: datetime
    time_to_triage_ms: int | None = None
    time_to_investigate_ms: int | None = None
    time_to_recommend_ms: int | None = None


class DemoInjectRequest(BaseModel):
    incident_type: Literal["crashloop", "rollout_failure", "high_latency"]
    namespace: str = "default"
    workload: str | None = None
    severity: Literal["critical", "high", "medium", "low"] = "high"


class DemoAttackRequest(BaseModel):
    attack_type: Literal["crashloop", "rollout_failure", "high_latency"]
    enabled: bool | None = None


class DemoWorkloadStatus(BaseModel):
    namespace: str
    workload: str
    desired_replicas: int
    ready_replicas: int
    available_replicas: int
    restarts: int
    status: Literal["healthy", "degraded", "missing", "error"]
    message: str | None = None


# 🔹 RESULT CONTRACTS (MOVED FROM orchestrator.py)

class InvestigationResult(BaseModel):
    evidence: list[Evidence]
    links: list[str]


class TriageResult(BaseModel):
    evidence: list[Evidence]


class RecommendationResult(BaseModel):
    recommended_actions: list[RecommendedAction]
    root_cause_hypotheses: list[RootCauseHypothesis] | None = None

class TriageResult(BaseModel):
    evidence: list[Evidence]

class InvestigationResult(BaseModel):
    evidence: list[Evidence]
    links: list[str]

class RecommendationResult(BaseModel):
    recommended_actions: list[RecommendedAction]
    root_cause_hypotheses: list[RootCauseHypothesis] | None = None
