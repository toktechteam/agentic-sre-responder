from __future__ import annotations

from typing import Any

import httpx

from app.logging_config import get_logger
from app.models import IncidentReport

logger = get_logger(__name__)


class SlackClient:
    def __init__(self, webhook_url: str | None) -> None:
        self.webhook_url = webhook_url

    async def notify_incident_created(self, report: IncidentReport) -> None:
        await self._send_message(report, "Incident created")

    async def notify_recommendation_ready(self, report: IncidentReport) -> None:
        await self._send_message(report, "Recommendation ready")

    async def notify_validation_complete(self, report: IncidentReport) -> None:
        await self._send_message(report, "Validation complete")

    async def _send_message(self, report: IncidentReport, title: str) -> None:
        if not self.webhook_url:
            logger.info("slack_webhook_missing", extra={"incident_id": report.incident_id})
            return
        summary = report.summary
        top_evidence = report.evidence[:2]
        recommendation = report.recommended_actions[0].action if report.recommended_actions else "Pending"
        payload: dict[str, Any] = {
            "text": f"{title}: {summary}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{title}*\n*Severity:* {report.severity}\n*Type:* {report.incident_type}",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Summary:* {summary}",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Top evidence:*\n" + "\n".join(
                            [f"- {item.detail}" for item in top_evidence]
                        ),
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Recommended action:* {recommendation}",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Dashboard:* http://localhost:30081/incidents/{report.incident_id}",
                    },
                },
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self.webhook_url, json=payload)
                resp.raise_for_status()
        except Exception as exc:
            logger.warning("slack_notify_failed", extra={"error": str(exc)})
