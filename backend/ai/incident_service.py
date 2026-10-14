"""
SentinelAI Incident Service

Reconstructed service contract for main.py.
Provides incident lifecycle, alert-to-incident creation,
evidence metadata, assignment, counts, and status transitions.

This implementation is intentionally deterministic and SQLite-backed.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .storage import get_connection


# ============================================================
# STATUS CONSTANTS
# ============================================================

STATUS_NEW = "NEW"
STATUS_ACKNOWLEDGED = "ACKNOWLEDGED"
STATUS_INVESTIGATING = "INVESTIGATING"
STATUS_RESOLVED = "RESOLVED"

VALID_STATUSES = {
    STATUS_NEW,
    STATUS_ACKNOWLEDGED,
    STATUS_INVESTIGATING,
    STATUS_RESOLVED,
}

ALLOWED_TRANSITIONS = {
    STATUS_NEW: {
        STATUS_ACKNOWLEDGED,
        STATUS_INVESTIGATING,
        STATUS_RESOLVED,
    },
    STATUS_ACKNOWLEDGED: {
        STATUS_INVESTIGATING,
        STATUS_RESOLVED,
    },
    STATUS_INVESTIGATING: {
        STATUS_RESOLVED,
    },
    STATUS_RESOLVED: set(),
}


# Evidence directory used by main.py.
EVIDENCE_DIR = Path(__file__).resolve().parent.parent / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# HELPERS
# ============================================================

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _json_load(value: Any, default: Any) -> Any:
    if value is None:
        return default

    if isinstance(value, (dict, list)):
        return value

    try:
        return json.loads(value)
    except Exception:
        return default


def _row_to_dict(row: sqlite3.Row | None) -> Optional[dict]:
    if row is None:
        return None

    result = dict(row)

    for key in (
        "detections",
        "metadata",
        "evidence",
    ):
        if key in result and isinstance(result[key], str):
            result[key] = _json_load(result[key], [])

    return result


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def _init_db() -> None:
    conn = get_connection()

    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                alert_id TEXT,
                timestamp TEXT NOT NULL,
                camera_id TEXT,
                location TEXT,
                title TEXT NOT NULL,
                description TEXT,
                severity TEXT NOT NULL DEFAULT 'MEDIUM',
                risk_score INTEGER NOT NULL DEFAULT 0,
                risk_level TEXT NOT NULL DEFAULT 'MEDIUM',
                event_type TEXT NOT NULL DEFAULT 'NONE',
                status TEXT NOT NULL DEFAULT 'NEW',
                assigned_to TEXT,
                evidence_path TEXT,
                detections TEXT NOT NULL DEFAULT '[]',
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                acknowledged_at TEXT,
                resolved_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_incidents_timestamp
                ON incidents(timestamp);

            CREATE INDEX IF NOT EXISTS idx_incidents_status
                ON incidents(status);

            CREATE INDEX IF NOT EXISTS idx_incidents_camera
                ON incidents(camera_id);

            CREATE INDEX IF NOT EXISTS idx_incidents_alert
                ON incidents(alert_id);

            CREATE TABLE IF NOT EXISTS incident_events (
                id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor TEXT,
                old_status TEXT,
                new_status TEXT,
                message TEXT,
                metadata TEXT,
                FOREIGN KEY (incident_id)
                    REFERENCES incidents(id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_incident_events_incident
                ON incident_events(incident_id);

            CREATE INDEX IF NOT EXISTS idx_incident_events_timestamp
                ON incident_events(timestamp);

            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                content_type TEXT,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (incident_id)
                    REFERENCES incidents(id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_evidence_incident
                ON evidence(incident_id);

            CREATE TABLE IF NOT EXISTS incident_notes (
                id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                content TEXT NOT NULL,
                author_id TEXT NOT NULL,
                author_username TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (incident_id)
                    REFERENCES incidents(id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_incident_notes_incident
                ON incident_notes(incident_id, created_at DESC);
            """
        )

        conn.commit()

    finally:
        conn.close()


_init_db()


# ============================================================
# ALERT → INCIDENT RULE
# ============================================================

def should_create_incident_for_alert(alert: Any) -> bool:
    """
    Determine whether an alert should create an incident.

    Critical and high-risk alerts create incidents.
    Lower severity alerts remain normal alerts.
    """

    if not alert:
        return False

    if isinstance(alert, dict):
        risk_level = str(
            alert.get("risk_level")
            or alert.get("severity")
            or ""
        ).upper()

        risk_score = int(alert.get("risk_score") or 0)

        return (
            risk_level in {"HIGH", "CRITICAL"}
            or risk_score >= 60
        )

    return False


# ============================================================
# INCIDENT CREATION
# ============================================================

def create_incident_from_alert(alert: dict) -> dict:
    """Create an incident from a qualifying alert."""

    if not should_create_incident_for_alert(alert):
        raise ValueError("Alert does not qualify for incident creation")

    now = _utc_now()

    incident_id = _new_id("incident")

    risk_score = int(alert.get("risk_score") or 0)

    risk_level = str(
        alert.get("risk_level")
        or alert.get("severity")
        or "MEDIUM"
    ).upper()

    severity = str(
        alert.get("severity")
        or risk_level
        or "MEDIUM"
    ).upper()

    event_type = str(
        alert.get("event_type")
        or alert.get("type")
        or "NONE"
    )

    detections = alert.get("detections") or []

    title = (
        f"{severity.title()} road-safety incident"
    )

    message = str(
        alert.get("message")
        or "Road-safety risk detected."
    )

    conn = get_connection()

    try:
        # Avoid duplicate incident for the same alert.
        existing = conn.execute(
            """
            SELECT *
            FROM incidents
            WHERE alert_id = ?
            LIMIT 1
            """,
            (str(alert.get("id")),),
        ).fetchone()

        if existing:
            return _row_to_dict(existing) or {}

        conn.execute(
            """
            INSERT INTO incidents (
                id,
                alert_id,
                timestamp,
                camera_id,
                location,
                title,
                description,
                severity,
                risk_score,
                risk_level,
                event_type,
                status,
                assigned_to,
                evidence_path,
                detections,
                metadata,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incident_id,
                alert.get("id"),
                str(alert.get("timestamp") or now),
                alert.get("camera_id"),
                alert.get("location"),
                title,
                message,
                severity,
                risk_score,
                risk_level,
                event_type,
                STATUS_NEW,
                None,
                None,
                json.dumps(detections),
                json.dumps({
                    "source": "alert_service",
                    "alert_type": alert.get("type"),
                }),
                now,
                now,
            ),
        )

        conn.execute(
            """
            INSERT INTO incident_events (
                id,
                incident_id,
                timestamp,
                event_type,
                actor,
                old_status,
                new_status,
                message,
                metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _new_id("inc_event"),
                incident_id,
                now,
                "CREATED",
                "system",
                None,
                STATUS_NEW,
                "Incident created from alert.",
                json.dumps({
                    "alert_id": alert.get("id"),
                }),
            ),
        )

        conn.commit()

        row = conn.execute(
            """
            SELECT *
            FROM incidents
            WHERE id = ?
            """,
            (incident_id,),
        ).fetchone()

        return _row_to_dict(row) or {}

    finally:
        conn.close()


# ============================================================
# INCIDENT READ OPERATIONS
# ============================================================

def get_incident(incident_id: str) -> Optional[dict]:
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT *
            FROM incidents
            WHERE id = ?
            """,
            (incident_id,),
        ).fetchone()

        return _row_to_dict(row)

    finally:
        conn.close()


def list_incidents(
    status: Optional[str] = None,
    camera_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    **kwargs,
) -> list[dict]:
    limit = max(1, min(int(limit), 1000))
    offset = max(0, int(offset))

    conn = get_connection()

    try:
        where = []
        params: list[Any] = []

        if status:
            where.append("status = ?")
            params.append(str(status).upper())

        if camera_id:
            where.append("camera_id = ?")
            params.append(camera_id)

        sql = """
            SELECT *
            FROM incidents
        """

        if where:
            sql += " WHERE " + " AND ".join(where)

        sql += """
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """

        params.extend([limit, offset])

        rows = conn.execute(sql, params).fetchall()

        return [_row_to_dict(row) or {} for row in rows]

    finally:
        conn.close()


def get_incident_events(incident_id: str) -> list[dict]:
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT *
            FROM incident_events
            WHERE incident_id = ?
            ORDER BY timestamp ASC
            """,
            (incident_id,),
        ).fetchall()

        return [_row_to_dict(row) or {} for row in rows]

    finally:
        conn.close()


def get_evidence(incident_id: str) -> list[dict]:
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT *
            FROM evidence
            WHERE incident_id = ?
            ORDER BY created_at DESC
            """,
            (incident_id,),
        ).fetchall()

        return [_row_to_dict(row) or {} for row in rows]

    finally:
        conn.close()


def list_incident_notes(incident_id: str) -> list[dict]:
    """Return notes for an incident, newest first."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, incident_id, content, author_id, author_username, created_at
            FROM incident_notes
            WHERE incident_id = ?
            ORDER BY created_at DESC
            """,
            (incident_id,),
        ).fetchall()
    return [_row_to_dict(row) or {} for row in rows]


def create_incident_note(
    incident_id: str,
    content: str,
    author_id: str,
    author_username: str,
) -> dict | None:
    """Persist a validated incident note."""
    note_id = _new_id("note")
    created_at = _utc_now()
    with get_connection() as conn:
        incident = conn.execute("SELECT id FROM incidents WHERE id = ?", (incident_id,)).fetchone()
        if not incident:
            return None
        conn.execute(
            """
            INSERT INTO incident_notes (id, incident_id, content, author_id, author_username, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (note_id, incident_id, content, author_id, author_username, created_at),
        )
        conn.commit()
    return {
        "id": note_id,
        "incident_id": incident_id,
        "content": content,
        "author_id": author_id,
        "author_username": author_username,
        "created_at": created_at,
    }


def delete_incident_note(note_id: str, user_id: str, is_admin: bool = False) -> bool | None:
    """Delete a note when the caller is its author or an administrator.

    Returns None when the note does not exist and False when permission is denied.
    """
    with get_connection() as conn:
        row = conn.execute("SELECT author_id FROM incident_notes WHERE id = ?", (note_id,)).fetchone()
        if not row:
            return None
        if not is_admin and row["author_id"] != user_id:
            return False
        conn.execute("DELETE FROM incident_notes WHERE id = ?", (note_id,))
        conn.commit()
    return True


# ============================================================
# INCIDENT STATUS TRANSITIONS
# ============================================================

def transition_incident(
    incident_id: str,
    new_status: str,
    actor: str = "system",
    message: Optional[str] = None,
    **kwargs,
) -> dict:
    new_status = str(new_status).upper()

    if new_status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid incident status: {new_status}"
        )

    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT *
            FROM incidents
            WHERE id = ?
            """,
            (incident_id,),
        ).fetchone()

        if row is None:
            raise ValueError(
                f"Incident not found: {incident_id}"
            )

        old_status = str(row["status"]).upper()

        if old_status != new_status:
            allowed = ALLOWED_TRANSITIONS.get(
                old_status,
                set(),
            )

            if new_status not in allowed:
                raise ValueError(
                    f"Invalid incident transition: "
                    f"{old_status} -> {new_status}"
                )

        now = _utc_now()

        acknowledged_at = row["acknowledged_at"]
        resolved_at = row["resolved_at"]

        if new_status == STATUS_ACKNOWLEDGED:
            acknowledged_at = now

        if new_status == STATUS_RESOLVED:
            resolved_at = now

        conn.execute(
            """
            UPDATE incidents
            SET
                status = ?,
                updated_at = ?,
                acknowledged_at = ?,
                resolved_at = ?
            WHERE id = ?
            """,
            (
                new_status,
                now,
                acknowledged_at,
                resolved_at,
                incident_id,
            ),
        )

        conn.execute(
            """
            INSERT INTO incident_events (
                id,
                incident_id,
                timestamp,
                event_type,
                actor,
                old_status,
                new_status,
                message,
                metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _new_id("inc_event"),
                incident_id,
                now,
                "STATUS_CHANGE",
                actor,
                old_status,
                new_status,
                message
                or f"Incident status changed to {new_status}.",
                json.dumps({}),
            ),
        )

        conn.commit()

        updated = conn.execute(
            """
            SELECT *
            FROM incidents
            WHERE id = ?
            """,
            (incident_id,),
        ).fetchone()

        return _row_to_dict(updated) or {}

    finally:
        conn.close()


# ============================================================
# ACKNOWLEDGE / ASSIGN
# ============================================================

def assign_incident(
    incident_id: str,
    assigned_to: Optional[str] = None,
    actor: str = "system",
    **kwargs,
) -> dict:
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT *
            FROM incidents
            WHERE id = ?
            """,
            (incident_id,),
        ).fetchone()

        if row is None:
            raise ValueError(
                f"Incident not found: {incident_id}"
            )

        now = _utc_now()

        conn.execute(
            """
            UPDATE incidents
            SET
                assigned_to = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                assigned_to,
                now,
                incident_id,
            ),
        )

        conn.execute(
            """
            INSERT INTO incident_events (
                id,
                incident_id,
                timestamp,
                event_type,
                actor,
                old_status,
                new_status,
                message,
                metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _new_id("inc_event"),
                incident_id,
                now,
                "ASSIGNMENT",
                actor,
                row["status"],
                row["status"],
                (
                    f"Incident assigned to {assigned_to}"
                    if assigned_to
                    else "Incident assignment cleared."
                ),
                json.dumps({
                    "assigned_to": assigned_to,
                }),
            ),
        )

        conn.commit()

        updated = conn.execute(
            """
            SELECT *
            FROM incidents
            WHERE id = ?
            """,
            (incident_id,),
        ).fetchone()

        return _row_to_dict(updated) or {}

    finally:
        conn.close()


# ============================================================
# INCIDENT COUNTS
# ============================================================

def get_incident_counts() -> dict:
    conn = get_connection()

    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM incidents"
        ).fetchone()[0]

        rows = conn.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM incidents
            GROUP BY status
            """
        ).fetchall()

        by_status = {
            str(row["status"]): int(row["count"])
            for row in rows
        }

        return {
            "total": int(total),
            "new": by_status.get(STATUS_NEW, 0),
            "acknowledged": by_status.get(
                STATUS_ACKNOWLEDGED, 0
            ),
            "investigating": by_status.get(
                STATUS_INVESTIGATING, 0
            ),
            "resolved": by_status.get(
                STATUS_RESOLVED, 0
            ),
            "active": (
                by_status.get(STATUS_NEW, 0)
                + by_status.get(STATUS_ACKNOWLEDGED, 0)
                + by_status.get(STATUS_INVESTIGATING, 0)
            ),
            "by_status": by_status,
        }

    finally:
        conn.close()


__all__ = [
    "STATUS_NEW",
    "STATUS_ACKNOWLEDGED",
    "STATUS_INVESTIGATING",
    "STATUS_RESOLVED",
    "VALID_STATUSES",
    "ALLOWED_TRANSITIONS",
    "EVIDENCE_DIR",
    "should_create_incident_for_alert",
    "create_incident_from_alert",
    "get_incident",
    "list_incidents",
    "get_incident_events",
    "get_evidence",
    "transition_incident",
    "assign_incident",
    "get_incident_counts",
]
