from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import aiosqlite
import redis.asyncio as redis

from app.models import IncidentReport, IncidentSummary, StageTiming


class Store:
    def __init__(self, redis_url: str, sqlite_path: str, ttl_seconds: int = 3600) -> None:
        self.redis_url = redis_url
        self.sqlite_path = sqlite_path
        self.ttl_seconds = ttl_seconds
        self._redis: redis.Redis | None = None
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._redis = redis.from_url(self.redis_url, decode_responses=True)
        self._db = await aiosqlite.connect(self.sqlite_path)
        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                correlation_id TEXT,
                status TEXT,
                incident_type TEXT,
                severity TEXT,
                summary TEXT,
                created_at TEXT,
                updated_at TEXT,
                report_json TEXT
            )
            """
        )
        await self._db.commit()

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.close()
        if self._db is not None:
            await self._db.close()

    async def save_incident_report(self, report: IncidentReport) -> None:
        if self._redis is None or self._db is None:
            raise RuntimeError("store_not_initialized")
        report_json = report.model_dump(mode="json")
        await self._redis.setex(
            name=f"incident:{report.incident_id}",
            time=self.ttl_seconds,
            value=json.dumps(report_json),
        )
        await self._db.execute(
            """
            INSERT INTO incidents (
                incident_id, correlation_id, status, incident_type, severity,
                summary, created_at, updated_at, report_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(incident_id) DO UPDATE SET
                status=excluded.status,
                incident_type=excluded.incident_type,
                severity=excluded.severity,
                summary=excluded.summary,
                updated_at=excluded.updated_at,
                report_json=excluded.report_json
            """,
            (
                report.incident_id,
                report.correlation_id,
                report.status,
                report.incident_type,
                report.severity,
                report.summary,
                report.created_at.isoformat(),
                report.updated_at.isoformat(),
                json.dumps(report_json),
            ),
        )
        await self._db.commit()

    async def get_incident_report(self, incident_id: str) -> IncidentReport | None:
        if self._redis is None or self._db is None:
            raise RuntimeError("store_not_initialized")
        cached = await self._redis.get(f"incident:{incident_id}")
        if cached:
            data = json.loads(cached)
            return IncidentReport.model_validate(data)
        async with self._db.execute(
            "SELECT report_json FROM incidents WHERE incident_id = ?", (incident_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return None
        data = json.loads(row[0])
        return IncidentReport.model_validate(data)

    async def list_incidents(self) -> list[IncidentSummary]:
        if self._db is None:
            raise RuntimeError("store_not_initialized")
        items: list[IncidentSummary] = []
        async with self._db.execute(
            """
            SELECT incident_id, correlation_id, status, incident_type, severity, summary,
                   created_at, updated_at, report_json
            FROM incidents
            ORDER BY updated_at DESC
            """
        ) as cursor:
            async for row in cursor:
                report_json = json.loads(row[8])
                report = IncidentReport.model_validate(report_json)
                timings = _timing_summary(report.stage_timings)
                items.append(
                    IncidentSummary(
                        incident_id=row[0],
                        correlation_id=row[1],
                        status=row[2],
                        incident_type=row[3],
                        severity=row[4],
                        summary=row[5],
                        created_at=datetime.fromisoformat(row[6]),
                        updated_at=datetime.fromisoformat(row[7]),
                        time_to_triage_ms=timings.get("triage"),
                        time_to_investigate_ms=timings.get("investigation"),
                        time_to_recommend_ms=timings.get("recommendation"),
                    )
                )
        return items


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _timing_summary(stage_timings: list[StageTiming]) -> dict[str, int | None]:
    result: dict[str, int | None] = {}
    for timing in stage_timings:
        if timing.duration_ms is not None:
            result[timing.stage] = timing.duration_ms
    return result


def summarize_alert(payload: dict[str, Any]) -> tuple[str, str]:
    labels = payload.get("labels", {}) if isinstance(payload, dict) else {}
    annotations = payload.get("annotations", {}) if isinstance(payload, dict) else {}
    incident_type = labels.get("alertname", "alert")
    summary = annotations.get("summary") or annotations.get("description") or "Alert received"
    return incident_type, summary
