from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import BackgroundTasks

from app.agents.deploy_investigator import deploy_investigation
from app.agents.k8s_investigator import k8s_investigation
from app.agents.remediation_advisor import recommend_actions
from app.agents.triage import triage_alert
from app.integrations.slack import SlackClient
from app.logging_config import get_logger
from app.models import (
    IncidentReport,
    RecommendedAction,
    RootCauseHypothesis,
    StageTiming,
    TimelineEvent,
)
from app.store import Store, now_utc, summarize_alert

logger = get_logger(__name__)


class Orchestrator:
    def __init__(self, store: Store, slack: SlackClient) -> None:
        self.store = store
        self.slack = slack

    async def handle_alert(
        self,
        payload: dict[str, Any],
        source: str,
        correlation_id: str,
        background_tasks: BackgroundTasks,
    ) -> IncidentReport:
        incident_type, summary = summarize_alert(payload)
        incident_id = str(uuid.uuid4())
        created_at = now_utc()

        report = IncidentReport(
            incident_id=incident_id,
            correlation_id=correlation_id,
            status="new",
            incident_type=incident_type,
            severity=payload.get("labels", {}).get("severity", "unknown"),
            summary=summary,
            created_at=created_at,
            updated_at=created_at,
            raw_alert=payload,
            timeline=[
                TimelineEvent(
                    stage="ingestion",
                    status="completed",
                    timestamp=created_at,
                )
            ],
        )

        await self.store.save_incident_report(report)
        background_tasks.add_task(self._run_pipeline, report)
        return report

    async def analyze_incident(
        self,
        incident_id: str,
        refresh_evidence: bool = False,
    ) -> IncidentReport:
        report = await self.store.get_incident_report(incident_id)
        if not report:
            raise ValueError("incident_not_found")

        if refresh_evidence:
            report = await self._investigate(report)

        report = await self._analyze(report)
        report = await self._recommend(report)
        report = await self._validate(report)

        logger.info(
            "manual_analysis_complete",
            extra={"incident_id": report.incident_id},
        )

        return report

    async def handle_demo_alert(
        self,
        demo_request: Any,
        correlation_id: str,
        background_tasks: BackgroundTasks,
    ) -> IncidentReport:
        payload = {
            "labels": {
                "alertname": demo_request.incident_type,
                "severity": demo_request.severity,
                "namespace": demo_request.namespace,
            },
            "annotations": {
                "summary": f"Demo incident injected: {demo_request.incident_type}",
                "workload": demo_request.workload or "unspecified",
            },
        }
        return await self.handle_alert(payload, "demo", correlation_id, background_tasks)

    async def _run_pipeline(self, report: IncidentReport) -> None:
        try:
            report = await self._triage(report)
            report = await self._investigate(report)
            report = await self._analyze(report)
            report = await self._recommend(report)
            report = await self._validate(report)

            logger.info(
                "pipeline_complete",
                extra={"incident_id": report.incident_id},
            )
        except Exception as exc:
            logger.exception(
                "pipeline_failed",
                extra={"incident_id": report.incident_id, "error": str(exc)},
            )

    async def _triage(self, report: IncidentReport) -> IncidentReport:
        stage = StageTiming(stage="triage", started_at=now_utc())
        report.stage_timings.append(stage)
        report.timeline.append(
            TimelineEvent(stage="triage", status="started", timestamp=stage.started_at)
        )

        result = await triage_alert(report)
        report.evidence.extend(result.evidence)
        report.status = "investigating"
        report.updated_at = now_utc()

        stage.completed_at = report.updated_at
        report.timeline.append(
            TimelineEvent(stage="triage", status="completed", timestamp=report.updated_at)
        )

        await self.store.save_incident_report(report)
        await self.slack.notify_incident_created(report)
        return report

    async def _investigate(self, report: IncidentReport) -> IncidentReport:
        stage = StageTiming(stage="investigation", started_at=now_utc())
        report.stage_timings.append(stage)
        report.timeline.append(
            TimelineEvent(stage="investigation", status="started", timestamp=stage.started_at)
        )

        k8s_task = asyncio.create_task(k8s_investigation(report))
        deploy_task = asyncio.create_task(deploy_investigation(report))
        results = await asyncio.gather(k8s_task, deploy_task)

        for result in results:
            report.evidence.extend(result.evidence)
            report.links.extend(result.links)

        report.updated_at = now_utc()
        stage.completed_at = report.updated_at
        report.timeline.append(
            TimelineEvent(stage="investigation", status="completed", timestamp=report.updated_at)
        )

        await self.store.save_incident_report(report)
        return report

    async def _analyze(self, report: IncidentReport) -> IncidentReport:
        stage = StageTiming(stage="analysis", started_at=now_utc())
        report.stage_timings.append(stage)
        report.timeline.append(
            TimelineEvent(stage="analysis", status="started", timestamp=stage.started_at)
        )

        report.root_cause_hypotheses = _derive_hypotheses(report.evidence)
        report.updated_at = now_utc()

        stage.completed_at = report.updated_at
        report.timeline.append(
            TimelineEvent(stage="analysis", status="completed", timestamp=report.updated_at)
        )

        await self.store.save_incident_report(report)
        return report

    async def _recommend(self, report: IncidentReport) -> IncidentReport:
        stage = StageTiming(stage="recommendation", started_at=now_utc())
        report.stage_timings.append(stage)
        report.timeline.append(
            TimelineEvent(stage="recommendation", status="started", timestamp=stage.started_at)
        )

        recommendation = await recommend_actions(report)
        report.recommended_actions = recommendation.recommended_actions
        report.root_cause_hypotheses = (
            recommendation.root_cause_hypotheses or report.root_cause_hypotheses
        )
        report.status = "recommended"
        report.updated_at = now_utc()

        stage.completed_at = report.updated_at
        report.timeline.append(
            TimelineEvent(stage="recommendation", status="completed", timestamp=report.updated_at)
        )

        await self.store.save_incident_report(report)
        await self.slack.notify_recommendation_ready(report)
        return report

    async def _validate(self, report: IncidentReport) -> IncidentReport:
        stage = StageTiming(stage="validation", started_at=now_utc())
        report.stage_timings.append(stage)
        report.timeline.append(
            TimelineEvent(stage="validation", status="started", timestamp=stage.started_at)
        )

        if not report.recommended_actions:
            report.recommended_actions.append(
                RecommendedAction(
                    action="Run kubectl get events to confirm status",
                    risk="low",
                    confidence=0.4,
                )
            )

        report.status = "validated"
        report.updated_at = now_utc()

        stage.completed_at = report.updated_at
        report.timeline.append(
            TimelineEvent(stage="validation", status="completed", timestamp=report.updated_at)
        )

        await self.store.save_incident_report(report)
        await self.slack.notify_validation_complete(report)
        return report


def _derive_hypotheses(evidence) -> list[RootCauseHypothesis]:
    hypotheses: list[RootCauseHypothesis] = []
    for item in evidence:
        if "CrashLoopBackOff" in item.detail:
            hypotheses.append(
                RootCauseHypothesis(
                    hypothesis="Pod crash loops detected",
                    confidence=0.6,
                )
            )
        if "ImagePullBackOff" in item.detail:
            hypotheses.append(
                RootCauseHypothesis(
                    hypothesis="Image pull failures",
                    confidence=0.5,
                )
            )
    if not hypotheses:
        hypotheses.append(
            RootCauseHypothesis(
                hypothesis="Investigate recent changes in workload",
                confidence=0.3,
            )
        )
    return hypotheses

