"""
SentinelAI shared SQLite storage layer.

Responsibilities:
- Provide a shared SQLite connection for backend services.
- Initialize the detection_history table used by analytics/dashboard APIs.
- Provide detection event persistence and retrieval helpers.

This module intentionally does NOT own the schemas of:
- users
- audit_events
- security_alerts
- emergency_* tables
- incidents/evidence

Those schemas are owned by their respective services.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Database location
# ---------------------------------------------------------------------------

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "sentinelai.db"


def _get_db_path() -> Path:
    configured = os.getenv("SENTINELAI_DB", "").strip()

    if configured:
        path = Path(configured).expanduser()

        if not path.is_absolute():
            path = Path(__file__).resolve().parent.parent / path

        return path

    return _DEFAULT_DB_PATH


DB_PATH = _get_db_path()


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """
    Return a configured SQLite connection.

    Existing services expect:
        with get_connection() as conn:
            cursor = conn.cursor()
            ...
            row["column_name"]

    Therefore sqlite3.Row is required.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(DB_PATH),
        timeout=30,
        check_same_thread=False,
    )

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")

    return conn


# ---------------------------------------------------------------------------
# Schema initialization
# ---------------------------------------------------------------------------

def init_db() -> None:
    """
    Initialize only the shared storage schema owned by this module.
    """
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS detection_history (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                camera_id TEXT,
                risk_score INTEGER NOT NULL DEFAULT 0,
                risk_level TEXT NOT NULL DEFAULT 'LOW',
                detections TEXT NOT NULL DEFAULT '[]',
                alert_id TEXT,
                event_type TEXT NOT NULL DEFAULT 'NONE'
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_detection_history_timestamp
            ON detection_history(timestamp DESC)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_detection_history_camera
            ON detection_history(camera_id)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_detection_history_risk_level
            ON detection_history(risk_level)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_detection_history_event_type
            ON detection_history(event_type)
            """
        )

        conn.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json_loads(value: Any, default: Any) -> Any:
    if value is None:
        return default

    if isinstance(value, (list, dict)):
        return value

    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


# ---------------------------------------------------------------------------
# Detection history
# ---------------------------------------------------------------------------

def store_event(
    risk_score: int,
    risk_level: str,
    detections: list[dict[str, Any]] | None = None,
    alert_id: str | None = None,
    camera_id: str | None = None,
    event_type: str = "NONE",
) -> dict[str, Any]:
    """
    Persist one detection event.

    Contract matches main.py:

        store_event(
            risk_score=int(...),
            risk_level=...,
            detections=...,
            alert_id=...,
            camera_id=...,
            event_type=...,
        )
    """
    event_id = uuid.uuid4().hex[:12]
    timestamp = _now()

    detections = detections if isinstance(detections, list) else []

    event = {
        "id": event_id,
        "timestamp": timestamp,
        "camera_id": camera_id,
        "risk_score": int(risk_score or 0),
        "risk_level": str(risk_level or "LOW"),
        "detections": detections,
        "alert_id": alert_id,
        "event_type": str(event_type or "NONE"),
    }

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO detection_history (
                id,
                timestamp,
                camera_id,
                risk_score,
                risk_level,
                detections,
                alert_id,
                event_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                timestamp,
                camera_id,
                int(risk_score or 0),
                str(risk_level or "LOW"),
                json.dumps(detections, ensure_ascii=False),
                alert_id,
                str(event_type or "NONE"),
            ),
        )
        conn.commit()

    return event


def get_detection_history(
    limit: int = 100,
    offset: int = 0,
    risk_level: str | None = None,
    min_risk_score: int | None = None,
    camera_id: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> list[dict[str, Any]]:
    """
    Return detection history with optional filtering.

    Results are newest first.
    """
    try:
        limit = max(1, min(int(limit), 5000))
    except (TypeError, ValueError):
        limit = 100

    try:
        offset = max(0, int(offset))
    except (TypeError, ValueError):
        offset = 0

    conditions: list[str] = []
    params: list[Any] = []

    if risk_level:
        conditions.append("risk_level = ?")
        params.append(risk_level)

    if min_risk_score is not None:
        conditions.append("risk_score >= ?")
        params.append(int(min_risk_score))

    if camera_id:
        conditions.append("camera_id = ?")
        params.append(camera_id)

    if start_time:
        conditions.append("timestamp >= ?")
        params.append(start_time)

    if end_time:
        conditions.append("timestamp <= ?")
        params.append(end_time)

    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            f"""
            SELECT
                id,
                timestamp,
                camera_id,
                risk_score,
                risk_level,
                detections,
                alert_id,
                event_type
            FROM detection_history
            {where}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        )

        rows = cursor.fetchall()

    result: list[dict[str, Any]] = []

    for row in rows:
        item = dict(row)
        item["detections"] = _safe_json_loads(item.get("detections"), [])
        result.append(item)

    return result


# ---------------------------------------------------------------------------
# Startup initialization
# ---------------------------------------------------------------------------

init_db()
