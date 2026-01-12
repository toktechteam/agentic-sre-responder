from __future__ import annotations

import json
import os
from typing import Any

import httpx

from app.logging_config import get_logger
from app.models import IncidentReport, RecommendedAction, RootCauseHypothesis
from app.results import RecommendationResult
from app.providers.base import LLMProvider

logger = get_logger(__name__)


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "600"))
        self.temperature = float(os.environ.get("LLM_TEMPERATURE", "0.1"))
        self.max_retries = int(os.environ.get("LLM_MAX_RETRIES", "2"))
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    async def generate_recommendations(
        self, report: IncidentReport
    ) -> RecommendationResult | None:
        if not self.api_key:
            logger.warning("openai_api_key_missing")
            return None

        prompt = _build_prompt(report)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a senior Site Reliability Engineer.\n"
                        "You analyze production incidents.\n\n"
                        "Rules:\n"
                        "- Be incident-type aware (latency vs rollout vs crashloop).\n"
                        "- Never suggest destructive commands.\n"
                        "- Prefer read-only kubectl commands.\n"
                        "- Do NOT guess RBAC or security issues unless evidence mentions permissions.\n"
                        "- Output ONLY valid JSON.\n"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
        }

        url = "https://api.openai.com/v1/chat/completions"

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=20) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return _parse_response(content)
            except Exception as exc:
                logger.warning(
                    "openai_request_failed",
                    extra={"error": str(exc), "attempt": attempt},
                )

        logger.warning("llm_fallback_used", extra={"incident_id": report.incident_id})
        return None


def _build_prompt(report: IncidentReport) -> str:
    evidence = "\n".join([f"- {item.detail}" for item in report.evidence[:15]])

    incident_guidance = {
        "high_latency": (
            "This is a PERFORMANCE incident.\n"
            "Focus on latency, load, config changes, saturation, throttling.\n"
            "Do NOT suggest rollout or RBAC checks unless evidence shows it."
        ),
        "rollout_failure": (
            "This is a DEPLOYMENT incident.\n"
            "Focus on rollout status, image pulls, pod readiness, events."
        ),
        "crashloop": (
            "This is an AVAILABILITY incident.\n"
            "Focus on pod crashes, logs, env vars, config errors."
        ),
    }

    guidance = incident_guidance.get(
        report.incident_type,
        "General SRE investigation. Use evidence to guide reasoning.",
    )

    return f"""
Incident Type: {report.incident_type}
Severity: {report.severity}

Guidance:
{guidance}

Incident Summary:
{report.summary}

Evidence:
{evidence}

Respond in JSON only with:
- root_cause_hypotheses: [{{
    "hypothesis": string,
    "confidence": number (0-1)
}}]
- recommended_actions: [{{
    "action": string,
    "risk": "low" | "medium" | "high",
    "confidence": number (0-1)
}}]
"""


def _parse_response(content: str) -> RecommendationResult | None:
    try:
        data = json.loads(_extract_json(content))

        hypotheses = [
            RootCauseHypothesis(
                hypothesis=item["hypothesis"],
                confidence=_clamp_confidence(item.get("confidence", 0.4)),
            )
            for item in data.get("root_cause_hypotheses", [])
        ]

        actions = [
            RecommendedAction(
                action=item["action"],
                risk=_normalize_risk(item.get("risk", "low")),
                confidence=_clamp_confidence(item.get("confidence", 0.4)),
            )
            for item in data.get("recommended_actions", [])
        ]

        if not actions:
            return None

        return RecommendationResult(
            recommended_actions=actions,
            root_cause_hypotheses=hypotheses,
        )
    except Exception:
        return None


def _extract_json(content: str) -> str:
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1:
        return content
    return content[start : end + 1]


def _normalize_risk(value: str) -> str:
    risk = str(value).lower()
    return risk if risk in {"low", "medium", "high"} else "low"


def _clamp_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.4
    return max(0.0, min(1.0, confidence))

