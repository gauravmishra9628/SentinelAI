"""
SentinelAI Prediction Service

Deterministic statistical baseline for predictive-risk endpoints.
No fabricated ML accuracy or trained-model claims.
"""

from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from .storage import get_connection


# ============================================================
# CONFIGURATION
# ============================================================

PREDICTION_WINDOWS = {
    "1h": 1,
    "6h": 6,
    "24h": 24,
}

DEFAULT_WINDOW = "1h"


# ============================================================
# HELPERS
# ============================================================

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "pred") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


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


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


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

    for key in ("features", "prediction", "metadata"):
        if key in result and isinstance(result[key], str):
            result[key] = _json_load(result[key], {})

    return result


# ============================================================
# DATABASE
# ============================================================

def _init_db() -> None:
    conn = get_connection()

    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                camera_id TEXT,
                window TEXT NOT NULL DEFAULT '1h',
                predicted_risk_score REAL NOT NULL DEFAULT 0,
                predicted_risk_level TEXT NOT NULL DEFAULT 'LOW',
                confidence REAL NOT NULL DEFAULT 0,
                confidence_label TEXT NOT NULL DEFAULT 'LOW',
                model_type TEXT NOT NULL DEFAULT 'STATISTICAL_BASELINE',
                has_sufficient_data INTEGER NOT NULL DEFAULT 0,
                data_note TEXT,
                features TEXT,
                prediction TEXT,
                metadata TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_predictions_timestamp
                ON predictions(timestamp);

            CREATE INDEX IF NOT EXISTS idx_predictions_camera
                ON predictions(camera_id);

            CREATE INDEX IF NOT EXISTS idx_predictions_window
                ON predictions(window);
            """
        )

        conn.commit()

    finally:
        conn.close()


_init_db()


# ============================================================
# RISK HELPERS
# ============================================================

def _risk_level(score: float) -> str:
    score = _clamp(score)

    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.75:
        return "HIGH"
    if confidence >= 0.45:
        return "MEDIUM"
    return "LOW"


# ============================================================
# FEATURE EXTRACTION
# ============================================================

def get_recent_features(
    camera_id: Optional[str] = None,
    hours: int = 24,
    limit: int = 500,
    **kwargs,
) -> dict:
    """
    Build transparent statistical features from detection history.
    """

    hours = max(1, min(int(hours), 168))
    limit = max(1, min(int(limit), 5000))

    conn = get_connection()

    try:
        where = [
            "timestamp >= datetime('now', ?)"
        ]
        params: list[Any] = [f"-{hours} hours"]

        if camera_id:
            where.append("camera_id = ?")
            params.append(camera_id)

        sql = f"""
            SELECT
                timestamp,
                camera_id,
                risk_score,
                risk_level,
                event_type,
                detections
            FROM detection_history
            WHERE {' AND '.join(where)}
            ORDER BY timestamp DESC
            LIMIT ?
        """

        params.append(limit)

        rows = conn.execute(sql, params).fetchall()

        scores = [
            _safe_float(row["risk_score"])
            for row in rows
        ]

        event_count = len(rows)

        average_risk = (
            sum(scores) / len(scores)
            if scores
            else 0.0
        )

        max_risk = max(scores) if scores else 0.0

        high_count = sum(
            1
            for row in rows
            if str(row["risk_level"]).upper()
            in {"HIGH", "CRITICAL"}
        )

        critical_count = sum(
            1
            for row in rows
            if str(row["risk_level"]).upper()
            == "CRITICAL"
        )

        return {
            "camera_id": camera_id,
            "hours": hours,
            "event_count": event_count,
            "average_risk": round(average_risk, 2),
            "max_risk": round(max_risk, 2),
            "high_risk_events": high_count,
            "critical_events": critical_count,
            "recent_scores": scores[:20],
            "has_data": event_count > 0,
        }

    finally:
        conn.close()


# ============================================================
# PREDICTION
# ============================================================

def predict_risk(
    camera_id: Optional[str] = None,
    window: str = DEFAULT_WINDOW,
    **kwargs,
) -> dict:
    """
    Predict near-future risk using a transparent statistical baseline.

    This is NOT a trained machine-learning model.
    """

    window = str(window or DEFAULT_WINDOW).lower()

    if window not in PREDICTION_WINDOWS:
        window = DEFAULT_WINDOW

    hours = PREDICTION_WINDOWS[window]

    features = get_recent_features(
        camera_id=camera_id,
        hours=max(24, hours * 4),
    )

    event_count = features["event_count"]
    average_risk = features["average_risk"]
    max_risk = features["max_risk"]
    high_events = features["high_risk_events"]
    critical_events = features["critical_events"]

    has_sufficient_data = event_count >= 3

    if event_count == 0:
        predicted_score = 0.0
        confidence = 0.10
        data_note = (
            "Insufficient historical detection data; "
            "no-risk baseline returned."
        )

    else:
        recent_scores = features.get("recent_scores") or []

        recent_average = (
            sum(recent_scores[:5])
            / len(recent_scores[:5])
            if recent_scores[:5]
            else average_risk
        )

        # Conservative statistical baseline.
        predicted_score = (
            average_risk * 0.55
            + recent_average * 0.30
            + max_risk * 0.15
        )

        if high_events:
            predicted_score += min(10.0, high_events * 1.5)

        if critical_events:
            predicted_score += min(15.0, critical_events * 3.0)

        predicted_score = _clamp(predicted_score)

        confidence = min(
            0.90,
            0.25
            + min(event_count / 20.0, 0.45)
            + (0.20 if has_sufficient_data else 0.0),
        )

        if has_sufficient_data:
            data_note = (
                "Prediction based on recent detection-history "
                "statistics."
            )
        else:
            data_note = (
                "Limited historical data; prediction confidence "
                "is reduced."
            )

    level = _risk_level(predicted_score)
    confidence_label = _confidence_label(confidence)

    prediction = {
        "camera_id": camera_id,
        "window": window,
        "risk_score": round(predicted_score, 2),
        "risk_level": level,
        "confidence": round(confidence, 3),
        "confidence_label": confidence_label,
        "model_type": "STATISTICAL_BASELINE",
        "has_sufficient_data": has_sufficient_data,
        "data_note": data_note,
        "features": features,
        "timestamp": _utc_now(),
    }

    return {
        "aggregate": prediction,
        "predictions": [prediction],
        "model_type": "STATISTICAL_BASELINE",
        "confidence_label": confidence_label,
        "has_sufficient_data": has_sufficient_data,
        "data_note": data_note,
        "timestamp": prediction["timestamp"],
    }


# ============================================================
# STORAGE
# ============================================================

def store_prediction(
    prediction: Optional[dict] = None,
    camera_id: Optional[str] = None,
    window: str = DEFAULT_WINDOW,
    **kwargs,
) -> dict:
    """
    Store a prediction result.
    """

    prediction = prediction or {}

    if "aggregate" in prediction:
        data = prediction["aggregate"]
    else:
        data = prediction

    camera_id = (
        camera_id
        or data.get("camera_id")
    )

    window = str(
        data.get("window")
        or window
        or DEFAULT_WINDOW
    )

    timestamp = str(
        data.get("timestamp")
        or _utc_now()
    )

    risk_score = _safe_float(
        data.get("risk_score")
        or data.get("predicted_risk_score")
    )

    risk_level = str(
        data.get("risk_level")
        or data.get("predicted_risk_level")
        or _risk_level(risk_score)
    ).upper()

    confidence = _safe_float(
        data.get("confidence"),
        0.0,
    )

    confidence_label = str(
        data.get("confidence_label")
        or _confidence_label(confidence)
    ).upper()

    model_type = str(
        data.get("model_type")
        or prediction.get("model_type")
        or "STATISTICAL_BASELINE"
    )

    has_sufficient_data = bool(
        data.get(
            "has_sufficient_data",
            prediction.get("has_sufficient_data", False),
        )
    )

    data_note = str(
        data.get("data_note")
        or prediction.get("data_note")
        or ""
    )

    features = data.get("features") or {}
    metadata = {
        "source": "prediction_service",
    }

    prediction_id = _new_id()

    conn = get_connection()

    try:
        conn.execute(
            """
            INSERT INTO predictions (
                id,
                timestamp,
                camera_id,
                window,
                predicted_risk_score,
                predicted_risk_level,
                confidence,
                confidence_label,
                model_type,
                has_sufficient_data,
                data_note,
                features,
                prediction,
                metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prediction_id,
                timestamp,
                camera_id,
                window,
                risk_score,
                risk_level,
                confidence,
                confidence_label,
                model_type,
                int(has_sufficient_data),
                data_note,
                json.dumps(features),
                json.dumps(data),
                json.dumps(metadata),
            ),
        )

        conn.commit()

        row = conn.execute(
            """
            SELECT *
            FROM predictions
            WHERE id = ?
            """,
            (prediction_id,),
        ).fetchone()

        return _row_to_dict(row) or {}

    finally:
        conn.close()


# ============================================================
# HISTORY
# ============================================================

def get_prediction_history(
    camera_id: Optional[str] = None,
    limit: int = 100,
    **kwargs,
) -> list[dict]:
    limit = max(1, min(int(limit), 1000))

    conn = get_connection()

    try:
        where = []
        params: list[Any] = []

        if camera_id:
            where.append("camera_id = ?")
            params.append(camera_id)

        sql = """
            SELECT *
            FROM predictions
        """

        if where:
            sql += " WHERE " + " AND ".join(where)

        sql += """
            ORDER BY timestamp DESC
            LIMIT ?
        """

        params.append(limit)

        rows = conn.execute(sql, params).fetchall()

        return [
            _row_to_dict(row) or {}
            for row in rows
        ]

    finally:
        conn.close()


# ============================================================
# ACCURACY
# ============================================================

def compute_prediction_accuracy(
    camera_id: Optional[str] = None,
    **kwargs,
) -> dict:
    """
    Compare stored predictions with subsequent observed detection
    history where enough data exists.

    Returns transparent evaluation information rather than claiming
    ML accuracy when no ground-truth dataset exists.
    """

    history = get_prediction_history(
        camera_id=camera_id,
        limit=100,
    )

    if not history:
        return {
            "available": False,
            "accuracy": None,
            "evaluated_predictions": 0,
            "note": (
                "No stored predictions are available for evaluation."
            ),
        }

    return {
        "available": False,
        "accuracy": None,
        "evaluated_predictions": 0,
        "note": (
            "Ground-truth future-risk labels are not available; "
            "statistical predictions are therefore not assigned "
            "a fabricated accuracy percentage."
        ),
    }


# ============================================================
# PUBLIC API
# ============================================================

__all__ = [
    "PREDICTION_WINDOWS",
    "predict_risk",
    "store_prediction",
    "get_prediction_history",
    "compute_prediction_accuracy",
    "get_recent_features",
]
