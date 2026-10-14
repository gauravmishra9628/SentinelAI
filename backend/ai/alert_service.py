"""
SentinelAI alert and detection analytics service.

Provides:
- Detection statistics
- Risk trend analytics
- Alert generation
- Alert CRUD
- Alert acknowledgement/resolution
- Alert summaries/counts
- Alert cooldown handling

The service uses the shared SQLite storage layer.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from .storage import get_connection


# ============================================================
# Constants
# ============================================================

ACTIVE = "ACTIVE"
ACKNOWLEDGED = "ACKNOWLEDGED"
RESOLVED = "RESOLVED"

SEVERITY_ORDER = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


# ============================================================
# Alert result contract
# ============================================================

@dataclass
class AlertResult:
    should_alert: bool
    alert: dict[str, Any] | None = None


# ============================================================
# Database initialization
# ============================================================

def _init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                severity TEXT NOT NULL,
                risk_score INTEGER NOT NULL DEFAULT 0,
                risk_level TEXT NOT NULL DEFAULT 'LOW',
                type TEXT NOT NULL DEFAULT 'ROAD_SAFETY',
                message TEXT NOT NULL,
                camera_id TEXT,
                location TEXT,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                detections TEXT NOT NULL DEFAULT '[]',
                acknowledged_at TEXT,
                resolved_at TEXT
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_alerts_timestamp
            ON alerts(timestamp DESC)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_alerts_status
            ON alerts(status)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_alerts_severity
            ON alerts(severity)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_alerts_camera
            ON alerts(camera_id)
            """
        )

        conn.commit()


# ============================================================
# Utility helpers
# ============================================================

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str = "alert") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _json_loads(value: Any, default: Any) -> Any:
    if value is None:
        return default

    if isinstance(value, (dict, list)):
        return value

    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _normalise_severity(risk_level: str, risk_score: int) -> str:
    level = str(risk_level or "").upper()

    if level in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
        return level

    score = int(risk_score or 0)

    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"

    return "LOW"


def _message_for_alert(
    severity: str,
    detections: list[dict[str, Any]],
) -> str:
    objects: list[str] = []

    for detection in detections[:5]:
        name = detection.get("class") or detection.get("label")

        if name:
            name = str(name).replace("_", " ").strip()
            if name and name not in objects:
                objects.append(name)

    if objects:
        object_text = ", ".join(objects)

        if severity == "CRITICAL":
            return f"Critical road-safety risk detected: {object_text}"
        if severity == "HIGH":
            return f"High road-safety risk detected: {object_text}"
        if severity == "MEDIUM":
            return f"Medium road-safety risk detected: {object_text}"

        return f"Road-safety event detected: {object_text}"

    if severity == "CRITICAL":
        return "Critical road-safety risk detected"
    if severity == "HIGH":
        return "High road-safety risk detected"
    if severity == "MEDIUM":
        return "Medium road-safety risk detected"

    return "Road-safety event detected"


# ============================================================
# Cooldown manager
# ============================================================

class AlertCooldownManager:
    """
    Prevents repeated alerts for the same camera/severity
    within a short interval.
    """

    def __init__(self, cooldown_seconds: int = 15):
        self.cooldown_seconds = max(0, int(cooldown_seconds))
        self._last_alert: dict[str, datetime] = {}

    def _key(self, camera_id: str | None, severity: str) -> str:
        return f"{camera_id or 'UNKNOWN'}:{severity}"

    def can_alert(
        self,
        camera_id: str | None,
        severity: str,
    ) -> bool:
        if self.cooldown_seconds <= 0:
            return True

        key = self._key(camera_id, severity)
        previous = self._last_alert.get(key)

        if previous is None:
            return True

        elapsed = (
            datetime.now(timezone.utc) - previous
        ).total_seconds()

        return elapsed >= self.cooldown_seconds

    def mark_alert(
        self,
        camera_id: str | None,
        severity: str,
    ) -> None:
        self._last_alert[self._key(camera_id, severity)] = (
            datetime.now(timezone.utc)
        )

    def clear(self) -> None:
        self._last_alert.clear()


_ALERT_COOLDOWN_MANAGER = AlertCooldownManager()


def get_alert_cooldown_manager() -> AlertCooldownManager:
    return _ALERT_COOLDOWN_MANAGER


# ============================================================
# Alert generation
# ============================================================

def generate_alert(
    detections: list[dict[str, Any]] | None,
    risk_score: int,
    risk_level: str,
    camera_id: str | None = None,
    location: str | None = None,
) -> AlertResult:
    """
    Generate a persistent alert when the calculated risk is
    meaningful enough to notify the monitoring system.

    Main.py expects:
        result.should_alert
        result.alert
    """
    detections = detections if isinstance(detections, list) else []

    score = int(risk_score or 0)
    level = str(risk_level or "LOW").upper()
    severity = _normalise_severity(level, score)

    # LOW events are stored in detection_history but do not
    # generate noisy dashboard alerts.
    if severity == "LOW":
        return AlertResult(should_alert=False, alert=None)

    manager = get_alert_cooldown_manager()

    if not manager.can_alert(camera_id, severity):
        return AlertResult(should_alert=False, alert=None)

    timestamp = _now()
    alert_id = _id()

    alert = {
        "id": alert_id,
        "timestamp": timestamp,
        "severity": severity,
        "risk_score": score,
        "risk_level": level,
        "message": _message_for_alert(severity, detections),
        "type": "ROAD_SAFETY",
        "camera_id": camera_id,
        "location": location or "Unknown",
        "status": ACTIVE,
        "detections": detections,
    }

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO alerts (
                id,
                timestamp,
                severity,
                risk_score,
                risk_level,
                type,
                message,
                camera_id,
                location,
                status,
                detections
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert_id,
                timestamp,
                severity,
                score,
                level,
                alert["type"],
                alert["message"],
                camera_id,
                location or "Unknown",
                ACTIVE,
                json.dumps(detections, ensure_ascii=False),
            ),
        )
        conn.commit()

    manager.mark_alert(camera_id, severity)

    return AlertResult(
        should_alert=True,
        alert=alert,
    )


# ============================================================
# Alert retrieval
# ============================================================

def _row_to_alert(row: Any) -> dict[str, Any]:
    alert = dict(row)

    alert["detections"] = _json_loads(
        alert.get("detections"),
        [],
    )

    return alert


def get_alert(alert_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM alerts
            WHERE id = ?
            """,
            (alert_id,),
        ).fetchone()

    return _row_to_alert(row) if row else None


def list_alerts(
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    severity: str | None = None,
) -> list[dict[str, Any]]:
    try:
        limit = max(1, min(int(limit), 5000))
    except (TypeError, ValueError):
        limit = 50

    try:
        offset = max(0, int(offset))
    except (TypeError, ValueError):
        offset = 0

    conditions: list[str] = []
    params: list[Any] = []

    if status:
        conditions.append("status = ?")
        params.append(str(status).upper())

    if severity:
        conditions.append("severity = ?")
        params.append(str(severity).upper())

    where = ""

    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT *
            FROM alerts
            {where}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        ).fetchall()

    return [_row_to_alert(row) for row in rows]


# ============================================================
# Alert lifecycle
# ============================================================

def acknowledge(alert_id: str) -> dict[str, Any] | None:
    now = _now()

    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE alerts
            SET status = ?,
                acknowledged_at = ?
            WHERE id = ?
              AND status = ?
            """,
            (
                ACKNOWLEDGED,
                now,
                alert_id,
                ACTIVE,
            ),
        )

        if cursor.rowcount == 0:
            return None

        conn.commit()

        row = conn.execute(
            "SELECT * FROM alerts WHERE id = ?",
            (alert_id,),
        ).fetchone()

    return _row_to_alert(row) if row else None


def resolve(alert_id: str) -> dict[str, Any] | None:
    now = _now()

    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE alerts
            SET status = ?,
                resolved_at = ?
            WHERE id = ?
              AND status != ?
            """,
            (
                RESOLVED,
                now,
                alert_id,
                RESOLVED,
            ),
        )

        if cursor.rowcount == 0:
            return None

        conn.commit()

        row = conn.execute(
            "SELECT * FROM alerts WHERE id = ?",
            (alert_id,),
        ).fetchone()

    return _row_to_alert(row) if row else None


def delete(alert_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            DELETE FROM alerts
            WHERE id = ?
            """,
            (alert_id,),
        )

        conn.commit()

        return cursor.rowcount > 0


def clear_all() -> int:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM alerts")
        conn.commit()

        return cursor.rowcount


# ============================================================
# Alert summaries
# ============================================================

def get_alert_counts() -> dict[str, int]:
    result = {
        "total": 0,
        "active": 0,
        "acknowledged": 0,
        "resolved": 0,
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT status, severity, COUNT(*) AS count
            FROM alerts
            GROUP BY status, severity
            """
        ).fetchall()

    for row in rows:
        status = str(row["status"] or "").lower()
        severity = str(row["severity"] or "").lower()
        count = int(row["count"] or 0)

        result["total"] += count

        if status in result:
            result[status] += count

        if severity in result:
            result[severity] += count

    return result


def get_summary() -> dict[str, Any]:
    counts = get_alert_counts()

    return {
        "alerts": counts,
    }


# ============================================================
# Detection statistics
# ============================================================

def get_detection_stats(
    start_time: str | None = None,
    end_time: str | None = None,
    camera_id: str | None = None,
) -> dict[str, Any]:
    conditions: list[str] = []
    params: list[Any] = []

    if start_time:
        conditions.append("timestamp >= ?")
        params.append(start_time)

    if end_time:
        conditions.append("timestamp <= ?")
        params.append(end_time)

    if camera_id:
        conditions.append("camera_id = ?")
        params.append(camera_id)

    where = ""

    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT *
            FROM detection_history
            {where}
            ORDER BY timestamp DESC
            """,
            params,
        ).fetchall()

    total_events = len(rows)

    detection_counts: dict[str, int] = {}
    by_risk_level: dict[str, int] = {}
    event_type_counts: dict[str, int] = {}

    total_risk = 0.0
    max_risk = 0

    vehicle_count = 0
    pedestrian_count = 0
    motorcycle_count = 0

    high_events = 0
    critical_events = 0

    one_hour_ago = (
        datetime.now(timezone.utc) - timedelta(hours=1)
    )

    events_last_hour = 0

    for row in rows:
        risk_score = int(row["risk_score"] or 0)
        risk_level = str(row["risk_level"] or "LOW").upper()
        event_type = str(row["event_type"] or "NONE")

        total_risk += risk_score
        max_risk = max(max_risk, risk_score)

        by_risk_level[risk_level] = (
            by_risk_level.get(risk_level, 0) + 1
        )

        event_type_counts[event_type] = (
            event_type_counts.get(event_type, 0) + 1
        )

        if risk_level == "HIGH":
            high_events += 1

        if risk_level == "CRITICAL":
            critical_events += 1

        timestamp = row["timestamp"]

        try:
            dt = datetime.fromisoformat(
                str(timestamp).replace("Z", "+00:00")
            )

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            if dt >= one_hour_ago:
                events_last_hour += 1

        except (TypeError, ValueError):
            pass

        detections = _json_loads(
            row["detections"],
            [],
        )

        if not isinstance(detections, list):
            continue

        for detection in detections:
            if not isinstance(detection, dict):
                continue

            name = str(
                detection.get("class")
                or detection.get("label")
                or ""
            ).lower()

            if not name:
                continue

            detection_counts[name] = (
                detection_counts.get(name, 0) + 1
            )

            if name == "car":
                vehicle_count += 1
            elif name == "truck":
                vehicle_count += 1
            elif name == "bus":
                vehicle_count += 1
            elif name == "bicycle":
                vehicle_count += 1
            elif name == "motorcycle":
                motorcycle_count += 1
                vehicle_count += 1
            elif name in {"person", "pedestrian"}:
                pedestrian_count += 1

    average_risk_score = (
        round(total_risk / total_events, 1)
        if total_events
        else 0
    )

    detection_counter = sum(detection_counts.values())

    return {
        "total_events": total_events,
        "detection_counter": detection_counter,
        "detection_counts": detection_counts,
        "by_risk_level": by_risk_level,
        "event_type_counts": event_type_counts,
        "average_risk_score": average_risk_score,
        "max_risk_score": max_risk,
        "events_last_hour": events_last_hour,
        "vehicle_count": vehicle_count,
        "pedestrian_count": pedestrian_count,
        "motorcycle_count": motorcycle_count,
        "high_events": high_events,
        "critical_events": critical_events,
    }


# ============================================================
# Risk trend
# ============================================================

def get_risk_trend(limit: int = 24) -> list[dict[str, Any]]:
    try:
        limit = max(1, min(int(limit), 500))
    except (TypeError, ValueError):
        limit = 24

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                strftime('%Y-%m-%d %H:00', timestamp) AS hour,
                AVG(risk_score) AS avg_risk_score,
                MAX(risk_score) AS max_risk_score,
                COUNT(*) AS event_count
            FROM detection_history
            GROUP BY hour
            ORDER BY hour DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    result = []

    for row in reversed(rows):
        result.append(
            {
                "hour": row["hour"],
                "avg_risk_score": round(
                    float(row["avg_risk_score"] or 0),
                    1,
                ),
                "max_risk_score": int(
                    row["max_risk_score"] or 0
                ),
                "event_count": int(
                    row["event_count"] or 0
                ),
            }
        )

    return result


# ============================================================
# Analytics
# ============================================================

def get_analytics_data() -> dict[str, Any]:
    stats = get_detection_stats()
    alerts = get_alert_counts()

    return {
        "metrics": [
            {
                "name": "Total Events",
                "value": stats.get("total_events", 0),
            },
            {
                "name": "Average Risk",
                "value": stats.get("average_risk_score", 0),
            },
            {
                "name": "High Risk Events",
                "value": stats.get("high_events", 0),
            },
            {
                "name": "Critical Events",
                "value": stats.get("critical_events", 0),
            },
        ],
        "detection_stats": stats,
        "alerts": alerts,
        "risk_trend": get_risk_trend(limit=24),
    }


# ============================================================
# Startup
# ============================================================

_init_db()
