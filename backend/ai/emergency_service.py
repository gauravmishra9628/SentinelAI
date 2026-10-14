"""Emergency response workflow built on top of existing incidents.

This module intentionally keeps emergency cases separate from incidents while
using the incident id as the unique source reference. All locations and units
created here are explicitly marked as simulated because the current project
has no dispatch or GPS integration.
"""

from __future__ import annotations

import json
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from ai.storage import get_connection
from ai.incident_service import get_incident, list_incidents
from ai.dispatch_service import dispatch_status, get_dispatch_provider
from ai.location_service import get_location_provider


STATUSES = {
    "PENDING", "ACKNOWLEDGED", "DISPATCH_RECOMMENDED", "DISPATCHED",
    "RESPONDING", "ON_SCENE", "RESOLVED", "CANCELLED",
}
ACTIVE_STATUSES = STATUSES - {"RESOLVED", "CANCELLED"}
STATUS_TRANSITIONS = {
    "PENDING": {"ACKNOWLEDGED", "DISPATCH_RECOMMENDED", "CANCELLED"},
    "ACKNOWLEDGED": {"DISPATCH_RECOMMENDED", "CANCELLED"},
    "DISPATCH_RECOMMENDED": {"DISPATCHED", "CANCELLED"},
    "DISPATCHED": {"RESPONDING", "CANCELLED"},
    "RESPONDING": {"ON_SCENE", "CANCELLED"},
    "ON_SCENE": {"RESOLVED", "CANCELLED"},
    "RESOLVED": set(),
    "CANCELLED": set(),
}
SEVERITY_TO_PRIORITY = {"CRITICAL": "P1", "HIGH": "P2", "MEDIUM": "P3", "LOW": "P4"}
UNIT_TYPES = {"MEDICAL", "POLICE", "TRAFFIC_CONTROL", "FIRE", "ROAD_ASSISTANCE", "SECURITY"}
UNIT_STATUSES = {"AVAILABLE", "DISPATCHED", "RESPONDING", "ON_SCENE", "BUSY", "OFFLINE"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _json(value: Any, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _score_incident(incident: dict[str, Any]) -> dict[str, Any]:
    incident_type = str(incident.get("incident_type") or "").upper()
    severity = str(incident.get("severity") or "LOW").upper()
    risk_score = max(0, min(100, int(incident.get("risk_score") or 0)))
    objects = incident.get("detected_objects") or []
    object_names = " ".join(str(item.get("class", "")) if isinstance(item, dict) else str(item) for item in objects).lower()

    score = risk_score * 0.62
    factors: list[dict[str, Any]] = [{"label": "Risk engine score", "weight": round(risk_score * 0.62)}]
    if severity == "CRITICAL":
        score += 18
        factors.append({"label": "Critical incident severity", "weight": 18})
    elif severity == "HIGH":
        score += 10
        factors.append({"label": "High incident severity", "weight": 10})
    if any(term in incident_type for term in ("ACCIDENT", "COLLISION")):
        score += 18
        factors.append({"label": "Accident or collision indicator", "weight": 18})
    if any(term in incident_type for term in ("PEDESTRIAN", "MOTORCYCLE", "VULNERABLE")):
        score += 8
        factors.append({"label": "Vulnerable road user indicator", "weight": 8})
    if len(objects) >= 5:
        score += 6
        factors.append({"label": "High detected object count", "weight": 6})
    if "traffic" in object_names or "density" in incident_type:
        score += 6
        factors.append({"label": "Traffic density indicator", "weight": 6})

    score = max(0, min(100, round(score)))
    calculated_severity = "CRITICAL" if score >= 75 else "HIGH" if score >= 50 else "MEDIUM" if score >= 25 else "LOW"
    confidence = round(max(0.5, min(0.99, float(incident.get("confidence") or 0.75))) * 100)
    return {
        "score": score,
        "severity": calculated_severity,
        "priority": SEVERITY_TO_PRIORITY[calculated_severity],
        "confidence": confidence,
        "factors": factors,
    }


def _init_db() -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emergency_responses (
                id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL UNIQUE,
                severity TEXT NOT NULL,
                priority TEXT NOT NULL,
                score INTEGER NOT NULL,
                confidence INTEGER NOT NULL,
                factors TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL,
                acknowledged_at TEXT,
                dispatch_recommended_at TEXT,
                dispatched_at TEXT,
                responding_at TEXT,
                on_scene_at TEXT,
                resolved_at TEXT,
                updated_at TEXT NOT NULL,
                cancelled_at TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_emergency_status ON emergency_responses(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_emergency_created ON emergency_responses(created_at DESC)")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emergency_response_events (
                id TEXT PRIMARY KEY,
                response_id TEXT NOT NULL,
                incident_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                status TEXT,
                actor TEXT NOT NULL,
                description TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(response_id) REFERENCES emergency_responses(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_emergency_events_response ON emergency_response_events(response_id, timestamp)")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emergency_units (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                unit_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'AVAILABLE',
                location TEXT,
                eta_minutes INTEGER,
                assigned_incident_id TEXT,
                last_updated TEXT NOT NULL,
                simulated INTEGER NOT NULL DEFAULT 1
            )
        """)
        for column, definition in (
            ("latitude", "REAL"),
            ("longitude", "REAL"),
            ("location_source", "TEXT NOT NULL DEFAULT 'UNAVAILABLE'"),
            ("last_location_update", "TEXT"),
        ):
            try:
                cursor.execute(f"ALTER TABLE emergency_units ADD COLUMN {column} {definition}")
            except Exception:
                pass
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_emergency_units_status ON emergency_units(status)")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emergency_assignments (
                id TEXT PRIMARY KEY,
                response_id TEXT NOT NULL,
                incident_id TEXT NOT NULL,
                unit_id TEXT NOT NULL,
                assigned_by TEXT NOT NULL,
                assigned_at TEXT NOT NULL,
                released_at TEXT,
                FOREIGN KEY(response_id) REFERENCES emergency_responses(id) ON DELETE CASCADE,
                FOREIGN KEY(unit_id) REFERENCES emergency_units(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_emergency_assignment_response ON emergency_assignments(response_id)")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emergency_notes (
                id TEXT PRIMARY KEY,
                response_id TEXT NOT NULL,
                incident_id TEXT NOT NULL,
                actor TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(response_id) REFERENCES emergency_responses(id) ON DELETE CASCADE
            )
        """)
        # Demo units are clearly marked and do not represent real dispatch assets.
        cursor.execute("SELECT COUNT(*) FROM emergency_units")
        if cursor.fetchone()[0] == 0:
            now = _now()
            demo_units = [
                ("SIM-MED-01", "Simulated Medical 01", "MEDICAL"),
                ("SIM-POL-01", "Simulated Police 01", "POLICE"),
                ("SIM-TRF-01", "Simulated Traffic Control 01", "TRAFFIC_CONTROL"),
                ("SIM-FIR-01", "Simulated Fire 01", "FIRE"),
                ("SIM-SEC-01", "Simulated Security 01", "SECURITY"),
            ]
            cursor.executemany("""
                INSERT INTO emergency_units (id, name, unit_type, status, location, eta_minutes, last_updated, simulated, location_source)
                VALUES (?, ?, ?, 'AVAILABLE', 'Location metadata unavailable', NULL, ?, 1, 'SIMULATED')
            """, [(uid, name, typ, now) for uid, name, typ in demo_units])
        conn.commit()


try:
    _init_db()
except Exception as exc:
    print(f"[SentinelAI] WARNING: Emergency DB initialization failed: {exc}")


def _response(row) -> dict[str, Any]:
    result = dict(row)
    result["factors"] = _json(result.get("factors"), [])
    result["incident"] = get_incident(result["incident_id"])
    result["assignments"] = list_assignments(result["id"])
    result["dispatch"] = dispatch_status()
    result["location"] = get_location_provider().get_location(result["incident_id"])
    return result


def create_or_get_response(incident_id: str) -> dict[str, Any] | None:
    incident = get_incident(incident_id)
    if not incident or incident.get("severity") not in {"HIGH", "CRITICAL"}:
        return None
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM emergency_responses WHERE incident_id = ?", (incident_id,))
        existing = cursor.fetchone()
        if existing:
            return _response(existing)
        calc = _score_incident(incident)
        now = _now()
        response_id = _id("er")
        cursor.execute("""
            INSERT INTO emergency_responses
            (id, incident_id, severity, priority, score, confidence, factors, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)
        """, (response_id, incident_id, calc["severity"], calc["priority"], calc["score"], calc["confidence"], json.dumps(calc["factors"]), now, now))
        cursor.execute("""
            INSERT INTO emergency_response_events
            (id, response_id, incident_id, event_type, status, actor, description, timestamp)
            VALUES (?, ?, ?, 'EMERGENCY_CREATED', 'PENDING', 'system', 'Emergency response case created from existing incident', ?)
        """, (_id("ere"), response_id, incident_id, now))
        conn.commit()
    return get_response(response_id)


def sync_responses() -> None:
    for incident in list_incidents(limit=500):
        if incident.get("severity") in {"HIGH", "CRITICAL"} and incident.get("status") != "RESOLVED":
            create_or_get_response(incident["id"])


def list_responses(status: str | None = None, severity: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    sync_responses()
    with get_connection() as conn:
        query = "SELECT * FROM emergency_responses WHERE 1=1"
        params: list[Any] = []
        if status and status != "ALL":
            query += " AND status = ?"
            params.append(status)
        if severity and severity != "ALL":
            query += " AND severity = ?"
            params.append(severity)
        query += " ORDER BY CASE priority WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 WHEN 'P3' THEN 3 ELSE 4 END, score DESC, created_at DESC LIMIT ?"
        params.append(limit)
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [_response(row) for row in cursor.fetchall()]


def get_response(response_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM emergency_responses WHERE id = ?", (response_id,))
        row = cursor.fetchone()
        return _response(row) if row else None


def get_response_for_incident(incident_id: str) -> dict[str, Any] | None:
    create_or_get_response(incident_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM emergency_responses WHERE incident_id = ?", (incident_id,))
        row = cursor.fetchone()
    return get_response(row["id"]) if row else None


def transition_response(response_id: str, status: str, actor: str = "operator", description: str | None = None) -> dict[str, Any] | None:
    status = status.upper()
    if status not in STATUSES:
        return None
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM emergency_responses WHERE id = ?", (response_id,))
        row = cursor.fetchone()
        if not row or status == row["status"] or status not in STATUS_TRANSITIONS.get(row["status"], set()):
            return None
        now = _now()
        column = {"ACKNOWLEDGED": "acknowledged_at", "DISPATCH_RECOMMENDED": "dispatch_recommended_at", "DISPATCHED": "dispatched_at", "RESPONDING": "responding_at", "ON_SCENE": "on_scene_at", "RESOLVED": "resolved_at", "CANCELLED": "cancelled_at"}.get(status)
        if column:
            cursor.execute(f"UPDATE emergency_responses SET status = ?, updated_at = ?, {column} = ? WHERE id = ?", (status, now, now, response_id))
        else:
            cursor.execute("UPDATE emergency_responses SET status = ?, updated_at = ? WHERE id = ?", (status, now, response_id))
        if status in {"RESOLVED", "CANCELLED"}:
            cursor.execute("""
                UPDATE emergency_units SET status = 'AVAILABLE', assigned_incident_id = NULL,
                eta_minutes = NULL, last_updated = ?
                WHERE assigned_incident_id = ?
            """, (now, row["incident_id"]))
            cursor.execute("UPDATE emergency_assignments SET released_at = ? WHERE response_id = ? AND released_at IS NULL", (now, response_id))
        cursor.execute("""
            INSERT INTO emergency_response_events
            (id, response_id, incident_id, event_type, status, actor, description, timestamp)
            VALUES (?, ?, ?, 'STATUS_CHANGED', ?, ?, ?, ?)
        """, (_id("ere"), row["incident_id"], row["incident_id"], status, actor, description or f"Response status changed to {status}", now))
        conn.commit()
    return get_response(response_id)


def list_units(status: str | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        if status and status != "ALL":
            cursor.execute("SELECT * FROM emergency_units WHERE status = ? ORDER BY name", (status,))
        else:
            cursor.execute("SELECT * FROM emergency_units ORDER BY status, name")
        units = [dict(row) for row in cursor.fetchall()]
        for unit in units:
            source = unit.get("location_source") or ("SIMULATED" if unit.get("simulated") else "UNAVAILABLE")
            unit["location"] = {
                "label": unit.get("location") or "Location metadata unavailable",
                "latitude": unit.get("latitude"),
                "longitude": unit.get("longitude"),
                "accuracy": None,
                "source": source,
                "timestamp": unit.get("last_location_update"),
            }
            unit["location_source"] = source
            unit["dispatch_source"] = "SIMULATED" if unit.get("simulated") else "UNAVAILABLE"
        return units


def create_unit(payload: dict[str, Any]) -> dict[str, Any] | None:
    unit_type = str(payload.get("unit_type") or "").upper()
    status = str(payload.get("status") or "AVAILABLE").upper()
    if unit_type not in UNIT_TYPES or status not in UNIT_STATUSES or not payload.get("unit_id") or not payload.get("name"):
        return None
    now = _now()
    try:
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO emergency_units
                (id, name, unit_type, status, location, eta_minutes, last_updated, simulated, latitude, longitude, location_source, last_location_update)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
            """, (payload["unit_id"], payload["name"], unit_type, status, payload.get("location") or "Location metadata unavailable", payload.get("eta_minutes"), now, payload.get("latitude"), payload.get("longitude"), payload.get("location_source") or "UNAVAILABLE", now))
            conn.commit()
    except Exception:
        return None
    return next((unit for unit in list_units() if unit["id"] == payload["unit_id"]), None)


def update_unit(unit_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {"name", "unit_type", "status", "location", "eta_minutes", "latitude", "longitude", "location_source"}
    values = {key: value for key, value in payload.items() if key in allowed and value is not None}
    if "unit_type" in values:
        values["unit_type"] = str(values["unit_type"]).upper()
        if values["unit_type"] not in UNIT_TYPES:
            return None
    if "status" in values:
        values["status"] = str(values["status"]).upper()
        if values["status"] not in UNIT_STATUSES:
            return None
    if not values:
        return next((unit for unit in list_units() if unit["id"] == unit_id), None)
    values["last_updated"] = _now()
    assignments = ", ".join(f"{key} = ?" for key in values)
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE emergency_units SET {assignments} WHERE id = ?", (*values.values(), unit_id))
            if cursor.rowcount == 0:
                return None
            conn.commit()
    except Exception:
        return None
    return next((unit for unit in list_units() if unit["id"] == unit_id), None)


def list_assignments(response_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.*, u.name, u.unit_type, u.status AS unit_status
            FROM emergency_assignments a JOIN emergency_units u ON u.id = a.unit_id
            WHERE a.response_id = ? ORDER BY a.assigned_at DESC
        """, (response_id,))
        return [dict(row) for row in cursor.fetchall()]


def assign_unit(response_id: str, unit_id: str, actor: str = "operator") -> dict[str, Any] | None:
    response = get_response(response_id)
    if not response:
        return None
    try:
        dispatch_result = get_dispatch_provider().dispatch(response_id, unit_id, 10)
    except RuntimeError:
        return None
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM emergency_units WHERE id = ?", (unit_id,))
        unit = cursor.fetchone()
        if not unit or unit["status"] != "AVAILABLE":
            return None
        cursor.execute("SELECT id FROM emergency_assignments WHERE response_id = ? AND released_at IS NULL", (response_id,))
        if cursor.fetchone():
            return None
        now = _now()
        cursor.execute("UPDATE emergency_units SET status = 'DISPATCHED', assigned_incident_id = ?, eta_minutes = ?, last_updated = ? WHERE id = ?", (response["incident_id"], 10, now, unit_id))
        cursor.execute("INSERT INTO emergency_assignments (id, response_id, incident_id, unit_id, assigned_by, assigned_at) VALUES (?, ?, ?, ?, ?, ?)", (_id("ass"), response_id, response["incident_id"], unit_id, actor, now))
        cursor.execute("INSERT INTO emergency_response_events (id, response_id, incident_id, event_type, status, actor, description, timestamp) VALUES (?, ?, ?, 'UNIT_ASSIGNED', ?, ?, ?, ?)", (_id("ere"), response_id, response["incident_id"], response["status"], actor, f"{dispatch_result['mode']} dispatch requested for unit {unit_id}", now))
        conn.commit()
    if response["status"] == "DISPATCH_RECOMMENDED":
        transition_response(response_id, "DISPATCHED", actor, "Unit assignment dispatched")
    return get_response(response_id)


def add_note(response_id: str, note: str, actor: str = "operator") -> dict[str, Any] | None:
    response = get_response(response_id)
    if not response or not note.strip():
        return None
    with get_connection() as conn:
        now = _now()
        conn.execute("INSERT INTO emergency_notes (id, response_id, incident_id, actor, note, created_at) VALUES (?, ?, ?, ?, ?, ?)", (_id("note"), response["id"], response["incident_id"], actor, note.strip()[:1000], now))
        conn.execute("INSERT INTO emergency_response_events (id, response_id, incident_id, event_type, status, actor, description, timestamp) VALUES (?, ?, ?, 'NOTE_ADDED', ?, ?, ?, ?)", (_id("ere"), response["id"], response["incident_id"], response["status"], actor, note.strip()[:1000], now))
        conn.commit()
    return get_response(response_id)


def get_timeline(response_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM emergency_response_events WHERE response_id = ? ORDER BY timestamp ASC", (response_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_notes(response_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM emergency_notes WHERE response_id = ? ORDER BY created_at DESC", (response_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_recommendations(response_id: str) -> list[dict[str, Any]]:
    response = get_response(response_id)
    if not response:
        return []
    incident = response.get("incident") or {}
    actions = [
        ("Preserve evidence", "Maintain the existing incident evidence chain", "P1" if response["priority"] == "P1" else "P2"),
        ("Monitor adjacent cameras", "Increase situational awareness around the incident camera", "P2"),
        ("Open investigation workflow", "Review the incident timeline and evidence", "P2"),
    ]
    if response["severity"] in {"HIGH", "CRITICAL"}:
        actions.insert(0, ("Dispatch recommended unit", "Severity and risk score warrant operator dispatch review", response["priority"]))
    if "PEDESTRIAN" in str(incident.get("incident_type", "")):
        actions.insert(0, ("Dispatch medical response", "Vulnerable road user indicator is present", "P1"))
    return [{"action": a, "reason": r, "priority": p, "status": "RECOMMENDED", "timestamp": response["created_at"]} for a, r, p in actions]


def analytics() -> dict[str, Any]:
    sync_responses()
    responses = list_responses(limit=1000)
    if not responses:
        return {"total": 0, "message": "Insufficient historical data", "severity_distribution": {}, "status_distribution": {}}
    durations = []
    ack_times = []
    for item in responses:
        created = datetime.fromisoformat(item["created_at"])
        if item.get("acknowledged_at"):
            ack_times.append(max(0, (datetime.fromisoformat(item["acknowledged_at"]) - created).total_seconds()))
        if item.get("resolved_at"):
            durations.append(max(0, (datetime.fromisoformat(item["resolved_at"]) - created).total_seconds()))
    return {
        "total": len(responses),
        "critical": sum(1 for r in responses if r["severity"] == "CRITICAL"),
        "average_acknowledgement_seconds": round(sum(ack_times) / len(ack_times)) if ack_times else None,
        "average_resolution_seconds": round(sum(durations) / len(durations)) if durations else None,
        "severity_distribution": dict(Counter(r["severity"] for r in responses)),
        "status_distribution": dict(Counter(r["status"] for r in responses)),
        "message": None if ack_times or durations else "Insufficient historical data",
    }
