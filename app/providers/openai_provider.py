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
        self.max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "512"))
        self.temperature = float(os.environ.get("LLM_TEMPERATURE", "0.2"))
        self.max_retries = int(os.environ.get("LLM_MAX_RETRIES", "2"))
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    async def generate_recommendations(self, report: IncidentReport) -> RecommendationResult | None:
        if not self.api_key:
            logger.warning("openai_api_key_missing")
            return None
        prompt = _build_prompt(report)
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a cautious SRE advisor. "
                        "Never output destructive commands (delete, wipe, drop, scale-to-zero). "
                        "Prefer safe, read-only investigation steps first (kubectl get/describe/logs). "
                        "Return only JSON that matches the requested schema."
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
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return _parse_response(content)
            except Exception as exc:
                logger.warning("openai_request_failed", extra={"error": str(exc), "attempt": attempt})
        return None


def _build_prompt(report: IncidentReport) -> str:
    evidence = "\n".join([f"- {item.detail}" for item in report.evidence[:15]])
    prompt = (
        "Summarize the incident and propose safe, read-only remediation steps. "
        "Do not suggest destructive commands. Prefer kubectl get/describe/logs first. "
        "Provide JSON with keys: "
        "root_cause_hypotheses (list of {hypothesis, confidence}), "
        "recommended_actions (list of {action, risk, confidence}). "
        "risk must be one of low, medium, high; confidence must be between 0 and 1."
        f"\nIncident summary: {report.summary}\nEvidence:\n{evidence}"
    )
    return prompt


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
        return RecommendationResult(recommended_actions=actions, root_cause_hypotheses=hypotheses)
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
    if risk in {"low", "medium", "high"}:
        return risk
    return "low"


def _clamp_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.4
    return max(0.0, min(1.0, confidence))
