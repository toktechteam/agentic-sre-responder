import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

from pydantic import BaseModel
import aiosqlite
import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnectionError


# -------------------------------------------------------------------
# Fallback in-memory Redis (for local / demo safety)
# -------------------------------------------------------------------
class _MemoryRedis:
    def __init__(self) -> None:
        self._data: Dict[str, str] = {}
        self._expiry: Dict[str, float] = {}

    async def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self._data[key] = value
        self._expiry[key] = time.time() + ttl_seconds

    async def get(self, key: str) -> Optional[str]:
        exp = self._expiry.get(key)
        if exp is not None and time.time() > exp:
            self._data.pop(key, None)
            self._expiry.pop(key, None)
            return None
        return self._data.get(key)

    async def close(self) -> None:
        return


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def summarize_alert(payload: Dict[str, Any]) -> tuple[str, str]:
    labels = payload.get("labels", {}) or {}
    annotations = payload.get("annotations", {}) or {}

    incident_type = (
        labels.get("alertname")
        or labels.get("incident_type")
        or annotations.get("incident_type")
        or "unknown"
    )

    summary = (
        annotations.get("summary")
        or annotations.get("description")
        or annotations.get("message")
        or f"Incident triggered: {incident_type}"
    )

    return str(incident_type), str(summary)


# -------------------------------------------------------------------
# Store
# -------------------------------------------------------------------
class Store:
    def __init__(self, redis_url: str, sqlite_path: str, ttl_seconds: int = 3600):
        self.redis_url = redis_url
        self.sqlite_path = sqlite_path
        self.ttl_seconds = ttl_seconds
        self._redis: Any = None
        self._db: Optional[aiosqlite.Connection] = None

    # ---------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------
    async def connect(self) -> None:
        # Redis (best effort)
        self._redis = redis.from_url(self.redis_url, decode_responses=True)
        try:
            await self._redis.ping()
        except (OSError, RedisConnectionError):
            self._redis = _MemoryRedis()

        # SQLite
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

    # ---------------------------------------------------------------
    # Writes
    # ---------------------------------------------------------------
    async def save_incident_report(self, report: Any) -> str:
        if self._db is None:
            raise RuntimeError("Store not connected (db).")

        # Normalize Pydantic → dict
        if isinstance(report, BaseModel):
            report = report.model_dump()

        if not isinstance(report, dict):
            raise TypeError(f"Invalid report type: {type(report)}")

        incident_id = report.get("incident_id") or str(uuid.uuid4())
        correlation_id = report.get("correlation_id")
        status = report.get("status", "open")
        incident_type = report.get("incident_type", "unknown")
        severity = report.get("severity", "unknown")
        summary = report.get("summary", "")

        now = now_utc().isoformat()

        # Safe JSON serialization (datetime handled)
        report_json = json.dumps(report, ensure_ascii=False, default=str)

        await self._db.execute(
            """
            INSERT INTO incidents (
                incident_id,
                correlation_id,
                status,
                incident_type,
                severity,
                summary,
                created_at,
                updated_at,
                report_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(incident_id) DO UPDATE SET
                status=excluded.status,
                severity=excluded.severity,
                summary=excluded.summary,
                updated_at=excluded.updated_at,
                report_json=excluded.report_json
            """,
            (
                incident_id,
                correlation_id,
                status,
                incident_type,
                severity,
                summary,
                now,
                now,
                report_json,
            ),
        )
        await self._db.commit()

        return incident_id

    # ---------------------------------------------------------------
    # Reads
    # ---------------------------------------------------------------
    async def get_incident_report(self, incident_id: str) -> Optional[Dict[str, Any]]:
        if self._db is None:
            raise RuntimeError("Store not connected (db).")

        async with self._db.execute(
            "SELECT report_json FROM incidents WHERE incident_id = ?",
            (incident_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return None

        try:
            return json.loads(row[0]) if row[0] else None
        except json.JSONDecodeError:
            return None

    async def list_incidents(self, limit: int = 50) -> List[Dict[str, Any]]:
        if self._db is None:
            raise RuntimeError("Store not connected (db).")

        async with self._db.execute(
            """
            SELECT
                incident_id,
                correlation_id,
                status,
                incident_type,
                severity,
                summary,
                created_at,
                updated_at
            FROM incidents
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()

        return [
            {
                "incident_id": r[0],
                "correlation_id": r[1],
                "status": r[2],
                "incident_type": r[3],
                "severity": r[4],
                "summary": r[5],
                "created_at": r[6],   # ✅ REQUIRED BY RESPONSE MODEL
                "updated_at": r[7],
            }
            for r in rows
        ]

