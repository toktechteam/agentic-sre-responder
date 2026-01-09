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


class BedrockProvider(LLMProvider):
    def __init__(self) -> None:
        self.region = os.environ.get("AWS_REGION")
        self.model_id = os.environ.get("BEDROCK_MODEL_ID")
        self.max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "512"))
        self.temperature = float(os.environ.get("LLM_TEMPERATURE", "0.2"))
        self.max_retries = int(os.environ.get("LLM_MAX_RETRIES", "2"))

    async def generate_recommendations(self, report: IncidentReport) -> RecommendationResult | None:
        if not self.region or not self.model_id:
            logger.warning("bedrock_env_missing")
            return None
        prompt = _build_prompt(report)
        payload = {
            "modelId": self.model_id,
            "contentType": "application/json",
            "accept": "application/json",
            "body": json.dumps(
                {
                    "prompt": prompt,
                    "maxTokens": self.max_tokens,
                    "temperature": self.temperature,
                }
            ),
        }
        url = f"https://bedrock-runtime.{self.region}.amazonaws.com/model/{self.model_id}/invoke"
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    content = data.get("completion") or data.get("outputText") or ""
                    return _parse_response(content)
            except Exception as exc:
                logger.warning("bedrock_request_failed", extra={"error": str(exc), "attempt": attempt})
        return None


def _build_prompt(report: IncidentReport) -> str:
    evidence = "\n".join([f"- {item.detail}" for item in report.evidence[:15]])
    prompt = (
        "Summarize the incident and propose safe, read-only remediation steps. "
        "Do not suggest destructive commands. Provide JSON with keys: "
        "root_cause_hypotheses (list of {hypothesis, confidence}), "
        "recommended_actions (list of {action, risk, confidence})."
        f"\nIncident summary: {report.summary}\nEvidence:\n{evidence}"
    )
    return prompt


def _parse_response(content: str) -> RecommendationResult | None:
    try:
        data = json.loads(_extract_json(content))
        hypotheses = [
            RootCauseHypothesis(
                hypothesis=item["hypothesis"],
                confidence=float(item.get("confidence", 0.4)),
            )
            for item in data.get("root_cause_hypotheses", [])
        ]
        actions = [
            RecommendedAction(
                action=item["action"],
                risk=item.get("risk", "low"),
                confidence=float(item.get("confidence", 0.4)),
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
