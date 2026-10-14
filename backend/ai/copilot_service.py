"""
SentinelAI Copilot Service

Deterministic AI-assistant style service for dashboard, incident,
risk explanation, recommendations, priority scoring, predictive
warnings, safety timeline and reporting.

This module does not claim external LLM access or fabricate facts.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from .storage import get_connection
from .alert_service import (
    get_summary,
    get_detection_stats,
    list_alerts,
)
from .incident_service import (
    get_incident,
    get_incident_events,
    list_incidents,
)
from .prediction_service import (
    predict_risk,
)


# ============================================================
# HELPERS
# ============================================================

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _risk_level(score: float) -> str:
    score = max(0.0, min(100.0, score))

    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"


def _json_load(value: Any, default: Any) -> Any:
    if value is None:
        return default

    if isinstance(value, (dict, list)):
        return value

    try:
        return json.loads(value)
    except Exception:
        return default


def _row_to_dict(row) -> Optional[dict]:
    if row is None:
        return None

    result = dict(row)

    for key in (
        "detections",
        "metadata",
        "features",
        "prediction",
    ):
        if key in result and isinstance(result[key], str):
            result[key] = _json_load(result[key], {})

    return result


# ============================================================
# AI CONTEXT
# ============================================================

def get_ai_context(
    camera_id: Optional[str] = None,
    limit: int = 10,
    **kwargs,
) -> dict:
    """
    Return a compact deterministic context snapshot for the
    SentinelAI assistant.
    """

    limit = max(1, min(int(limit), 100))

    stats = get_detection_stats(
        camera_id=camera_id,
    )

    summary = get_summary()

    alerts = list_alerts(limit=limit)

    incidents = list_incidents(
        camera_id=camera_id,
        limit=limit,
    )

    return {
        "timestamp": _utc_now(),
        "camera_id": camera_id,
        "detection_stats": stats,
        "alert_summary": summary,
        "recent_alerts": alerts,
        "recent_incidents": incidents,
        "data_source": "SentinelAI SQLite telemetry",
    }


# ============================================================
# DETERMINISTIC QUERY ENGINE
# ============================================================

def query_ai(
    query: str = "",
    camera_id: Optional[str] = None,
    **kwargs,
) -> dict:
    """
    Answer common SentinelAI operational questions using
    available system data.

    No external LLM is required.
    """

    query_text = str(query or "").strip()
    query_lower = query_text.lower()

    context = get_ai_context(
        camera_id=camera_id,
    )

    stats = context["detection_stats"]
    summary = context["alert_summary"]
    incidents = context["recent_incidents"]

    if any(
        word in query_lower
        for word in (
            "risk",
            "danger",
            "safe",
            "safety",
        )
    ):
        avg_risk = _safe_float(
            stats.get("average_risk_score")
        )
        max_risk = _safe_float(
            stats.get("max_risk_score")
        )

        response = (
            f"Current recorded average risk is "
            f"{avg_risk:.1f}/100 and maximum recorded risk "
            f"is {max_risk:.1f}/100."
        )

    elif any(
        word in query_lower
        for word in (
            "alert",
            "alerts",
        )
    ):
        response = (
            f"The system has recorded "
            f"{summary.get('alerts', {}).get('total', 0)} "
            f"alerts. Active alerts: "
            f"{summary.get('alerts', {}).get('active', 0)}."
        )

    elif any(
        word in query_lower
        for word in (
            "incident",
            "incidents",
        )
    ):
        response = (
            f"There are currently "
            f"{len(incidents)} recent incidents in the "
            f"retrieved operational context."
        )

    elif any(
        word in query_lower
        for word in (
            "vehicle",
            "vehicles",
            "car",
            "cars",
        )
    ):
        response = (
            f"Recorded vehicle detections: "
            f"{stats.get('vehicle_count', 0)}."
        )

    elif any(
        word in query_lower
        for word in (
            "pedestrian",
            "pedestrians",
            "person",
            "people",
        )
    ):
        response = (
            f"Recorded pedestrian detections: "
            f"{stats.get('pedestrian_count', 0)}."
        )

    else:
        response = (
            "SentinelAI can summarize recorded risk, alerts, "
            "incidents, vehicles and pedestrian detections. "
            "The current response is based only on available "
            "SQLite telemetry."
        )

    return {
        "query": query_text,
        "response": response,
        "answer": response,
        "camera_id": camera_id,
        "timestamp": _utc_now(),
        "source": "DETERMINISTIC_SYSTEM_CONTEXT",
        "context": context,
    }


# ============================================================
# RISK EXPLANATION
# ============================================================

def explain_risk(
    risk_score: Any = 0,
    risk_level: Optional[str] = None,
    detections: Optional[list] = None,
    factors: Optional[list] = None,
    event_type: Optional[str] = None,
    **kwargs,
) -> dict:
    """
    Explain a risk score from supplied evidence.
    """

    score = max(
        0.0,
        min(100.0, _safe_float(risk_score)),
    )

    level = str(
        risk_level
        or _risk_level(score)
    ).upper()

    detections = detections or []
    factors = factors or []

    reasons = []

    if detections:
        reasons.append(
            f"{len(detections)} detection(s) contributed "
            "to the assessment."
        )

    if event_type and str(event_type).upper() != "NONE":
        reasons.append(
            f"Detected event type: {event_type}."
        )

    if factors:
        reasons.extend(
            [str(item) for item in factors[:10]]
        )

    if not reasons:
        reasons.append(
            "No additional contributing factors were supplied."
        )

    return {
        "risk_score": round(score, 2),
        "risk_level": level,
        "explanation": (
            f"Risk is classified as {level} at "
            f"{score:.1f}/100."
        ),
        "reasons": reasons,
        "factors": factors,
        "event_type": event_type or "NONE",
        "detection_count": len(detections),
        "timestamp": _utc_now(),
    }


# ============================================================
# INCIDENT SUMMARY
# ============================================================

def build_incident_summary(
    incident_id: str,
    **kwargs,
) -> dict:
    incident = get_incident(incident_id)

    if incident is None:
        return {
            "success": False,
            "incident_id": incident_id,
            "error": "Incident not found.",
        }

    events = get_incident_events(incident_id)

    return {
        "success": True,
        "incident_id": incident_id,
        "summary": {
            "title": incident.get("title"),
            "description": incident.get("description"),
            "severity": incident.get("severity"),
            "risk_score": incident.get("risk_score"),
            "risk_level": incident.get("risk_level"),
            "status": incident.get("status"),
            "camera_id": incident.get("camera_id"),
            "location": incident.get("location"),
            "event_type": incident.get("event_type"),
            "assigned_to": incident.get("assigned_to"),
            "created_at": incident.get("created_at"),
            "updated_at": incident.get("updated_at"),
        },
        "events": events,
        "event_count": len(events),
        "timestamp": _utc_now(),
    }


# ============================================================
# DAILY REPORT
# ============================================================

def build_daily_report(
    camera_id: Optional[str] = None,
    **kwargs,
) -> dict:
    stats = get_detection_stats(
        camera_id=camera_id,
    )

    summary = get_summary()

    incidents = list_incidents(
        camera_id=camera_id,
        limit=1000,
    )

    return {
        "success": True,
        "report_type": "DAILY_OPERATIONAL_REPORT",
        "generated_at": _utc_now(),
        "camera_id": camera_id,
        "detection_statistics": stats,
        "alert_summary": summary,
        "incident_count": len(incidents),
        "incidents": incidents,
        "data_note": (
            "Report contains recorded SentinelAI telemetry "
            "available in the local database."
        ),
    }


# ============================================================
# PRIORITY SCORE
# ============================================================

def compute_priority_score(
    item: Optional[dict] = None,
    risk_score: Any = 0,
    severity: Optional[str] = None,
    **kwargs,
) -> dict:
    """
    Compute a transparent operational priority score.
    """

    item = item or {}

    if not risk_score:
        risk_score = item.get("risk_score", 0)

    if not severity:
        severity = (
            item.get("severity")
            or item.get("risk_level")
            or "LOW"
        )

    score = max(
        0.0,
        min(100.0, _safe_float(risk_score)),
    )

    severity_upper = str(severity).upper()

    severity_bonus = {
        "CRITICAL": 20,
        "HIGH": 12,
        "MEDIUM": 5,
        "LOW": 0,
    }.get(severity_upper, 0)

    priority = min(
        100.0,
        score * 0.8 + severity_bonus,
    )

    if priority >= 80:
        priority_level = "URGENT"
    elif priority >= 60:
        priority_level = "HIGH"
    elif priority >= 30:
        priority_level = "MEDIUM"
    else:
        priority_level = "LOW"

    return {
        "priority_score": round(priority, 2),
        "priority_level": priority_level,
        "risk_score": round(score, 2),
        "severity": severity_upper,
        "method": "DETERMINISTIC_RISK_SEVERITY_SCORE",
    }


# ============================================================
# PREDICTIVE WARNINGS
# ============================================================

def build_predictive_warnings(
    camera_id: Optional[str] = None,
    window: str = "1h",
    **kwargs,
) -> dict:
    prediction = predict_risk(
        camera_id=camera_id,
        window=window,
    )

    aggregate = prediction.get(
        "aggregate",
        {},
    )

    score = _safe_float(
        aggregate.get("risk_score")
    )

    level = str(
        aggregate.get("risk_level")
        or _risk_level(score)
    )

    warnings = []

    if level in {"HIGH", "CRITICAL"}:
        warnings.append(
            {
                "level": level,
                "message": (
                    f"Predicted risk is {level.lower()} "
                    f"for the selected prediction window."
                ),
            }
        )

    if not prediction.get("has_sufficient_data", False):
        warnings.append(
            {
                "level": "INFO",
                "message": (
                    "Prediction confidence is limited because "
                    "historical data is insufficient."
                ),
            }
        )

    return {
        "camera_id": camera_id,
        "window": window,
        "prediction": prediction,
        "warnings": warnings,
        "timestamp": _utc_now(),
    }


# ============================================================
# SAFETY TIMELINE
# ============================================================

def build_safety_timeline(
    camera_id: Optional[str] = None,
    limit: int = 50,
    **kwargs,
) -> dict:
    limit = max(1, min(int(limit), 500))

    alerts = list_alerts(limit=limit)

    incidents = list_incidents(
        camera_id=camera_id,
        limit=limit,
    )

    timeline = []

    for alert in alerts:
        timeline.append(
            {
                "timestamp": alert.get("timestamp"),
                "type": "ALERT",
                "id": alert.get("id"),
                "severity": alert.get("severity"),
                "risk_score": alert.get("risk_score"),
                "message": alert.get("message"),
                "camera_id": alert.get("camera_id"),
            }
        )

    for incident in incidents:
        timeline.append(
            {
                "timestamp": incident.get("timestamp"),
                "type": "INCIDENT",
                "id": incident.get("id"),
                "severity": incident.get("severity"),
                "risk_score": incident.get("risk_score"),
                "message": incident.get("title"),
                "camera_id": incident.get("camera_id"),
                "status": incident.get("status"),
            }
        )

    timeline.sort(
        key=lambda item: str(
            item.get("timestamp") or ""
        ),
        reverse=True,
    )

    return {
        "camera_id": camera_id,
        "timeline": timeline[:limit],
        "count": min(len(timeline), limit),
        "timestamp": _utc_now(),
    }


# ============================================================
# RECOMMENDATIONS
# ============================================================

def build_recommendations(
    camera_id: Optional[str] = None,
    **kwargs,
) -> dict:
    stats = get_detection_stats(
        camera_id=camera_id,
    )

    recommendations = []

    high_events = _safe_int(
        stats.get("high_events")
    )

    critical_events = _safe_int(
        stats.get("critical_events")
    )

    pedestrians = _safe_int(
        stats.get("pedestrian_count")
    )

    vehicles = _safe_int(
        stats.get("vehicle_count")
    )

    if critical_events > 0:
        recommendations.append(
            {
                "priority": "CRITICAL",
                "recommendation": (
                    "Review critical recorded events and "
                    "associated evidence."
                ),
            }
        )

    if high_events > 0:
        recommendations.append(
            {
                "priority": "HIGH",
                "recommendation": (
                    "Review high-risk alerts and verify "
                    "incident status."
                ),
            }
        )

    if pedestrians > 0 and vehicles > 0:
        recommendations.append(
            {
                "priority": "MEDIUM",
                "recommendation": (
                    "Monitor interactions between pedestrian "
                    "and vehicle detections."
                ),
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "priority": "INFO",
                "recommendation": (
                    "Continue monitoring and collect sufficient "
                    "telemetry for stronger trend analysis."
                ),
            }
        )

    return {
        "camera_id": camera_id,
        "recommendations": recommendations,
        "context": {
            "vehicle_count": vehicles,
            "pedestrian_count": pedestrians,
            "high_events": high_events,
            "critical_events": critical_events,
        },
        "timestamp": _utc_now(),
    }


# ============================================================
# EVIDENCE LINKING
# ============================================================

def link_evidence(
    incident_id: str,
    evidence_ids: Optional[list[str]] = None,
    **kwargs,
) -> dict:
    """
    Return evidence metadata associated with an incident.

    Evidence creation remains controlled by main.py.
    """

    evidence_ids = evidence_ids or []

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

        evidence = [
            _row_to_dict(row) or {}
            for row in rows
        ]

        if evidence_ids:
            allowed = set(str(x) for x in evidence_ids)

            evidence = [
                item
                for item in evidence
                if str(item.get("id")) in allowed
            ]

        return {
            "success": True,
            "incident_id": incident_id,
            "evidence": evidence,
            "count": len(evidence),
            "timestamp": _utc_now(),
        }

    finally:
        conn.close()


# ============================================================
# PUBLIC API
# ============================================================

__all__ = [
    "get_ai_context",
    "query_ai",
    "explain_risk",
    "build_incident_summary",
    "build_daily_report",
    "compute_priority_score",
    "build_predictive_warnings",
    "build_safety_timeline",
    "build_recommendations",
    "link_evidence",
]

