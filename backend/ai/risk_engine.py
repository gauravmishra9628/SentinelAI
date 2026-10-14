"""
SentinelAI risk scoring engine.

The scoring is deterministic and transparent.
It is not presented as a trained ML risk model.
"""

from __future__ import annotations

import threading
import time
from typing import Any


RISK_LEVELS = {
    "LOW": {
        "min": 0,
        "max": 29,
        "color": "#22c55e",
        "description": "Low road-safety risk",
    },
    "MEDIUM": {
        "min": 30,
        "max": 59,
        "color": "#eab308",
        "description": "Moderate road-safety risk",
    },
    "HIGH": {
        "min": 60,
        "max": 79,
        "color": "#f97316",
        "description": "High road-safety risk",
    },
    "CRITICAL": {
        "min": 80,
        "max": 100,
        "color": "#ef4444",
        "description": "Critical road-safety risk",
    },
}


class AlertCooldownManager:
    """Small in-memory cooldown manager for repeated alert suppression."""

    def __init__(self, cooldown_seconds: float = 30.0):
        self.cooldown_seconds = cooldown_seconds
        self._last_alert: dict[str, float] = {}
        self._lock = threading.Lock()

    def should_alert(self, key: str) -> bool:
        now = time.time()

        with self._lock:
            previous = self._last_alert.get(key)

            if previous is not None and now - previous < self.cooldown_seconds:
                return False

            self._last_alert[key] = now
            return True

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._last_alert.clear()
            else:
                self._last_alert.pop(key, None)


_cooldown_manager = AlertCooldownManager()


def get_alert_cooldown_manager() -> AlertCooldownManager:
    return _cooldown_manager


def get_risk_level(score: int | float) -> str:
    score = max(0, min(100, int(round(score))))

    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"


def get_risk_color(level: str) -> str:
    return RISK_LEVELS.get(str(level).upper(), RISK_LEVELS["LOW"])["color"]


def get_risk_description(level: str) -> str:
    return RISK_LEVELS.get(
        str(level).upper(),
        RISK_LEVELS["LOW"],
    )["description"]


def _base_detection_score(detections: list[dict[str, Any]]) -> int:
    """Calculate a conservative score from object presence/count."""
    score = 0

    weights = {
        "person": 8,
        "bicycle": 8,
        "motorcycle": 12,
        "car": 6,
        "bus": 8,
        "truck": 9,
    }

    for detection in detections or []:
        class_name = str(detection.get("class", "")).lower()
        confidence = float(detection.get("confidence", 0) or 0)

        weight = weights.get(class_name, 2)

        # Confidence affects contribution, but never creates a high risk
        # by itself.
        score += int(round(weight * max(0.0, min(1.0, confidence))))

    return score


def calculate_risk(
    detections: list[dict[str, Any]] | None,
    alerts: list[dict[str, Any]] | None,
    *,
    event_type: str | None = None,
    enriched_detections: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Return a deterministic risk assessment.

    Existing detector alerts may increase the score.
    Event-specific high-risk claims are deliberately conservative.
    """
    detections = detections or []
    alerts = alerts or []

    score = _base_detection_score(
        enriched_detections if enriched_detections is not None else detections
    )

    factors: list[str] = []

    if detections:
        factors.append(f"{len(detections)} object(s) detected")

    vehicle_count = sum(
        1
        for d in detections
        if str(d.get("class", "")).lower()
        in {"car", "truck", "bus", "motorcycle", "bicycle"}
    )

    pedestrian_count = sum(
        1
        for d in detections
        if str(d.get("class", "")).lower() == "person"
    )

    if vehicle_count >= 5:
        score += 15
        factors.append("high vehicle count")

    if pedestrian_count >= 3:
        score += 10
        factors.append("multiple pedestrians")

    if alerts:
        score += min(25, 10 * len(alerts))
        factors.append("detector alert signal")

    # Event labels alone are not treated as proof of a collision or
    # dangerous event. They receive only a modest contextual adjustment.
    event = (event_type or "").upper()

    event_adjustments = {
        "WRONG_WAY": 15,
        "COLLISION": 20,
        "PEDESTRIAN_RISK": 10,
        "OVERSPEED": 10,
        "DANGEROUS_DRIVING": 15,
        "CONGESTION": 5,
        "ROAD_OBSTRUCTION": 5,
    }

    if event in event_adjustments:
        score += event_adjustments[event]
        factors.append(f"event context: {event}")

    score = max(0, min(100, int(score)))

    level = get_risk_level(score)

    if not detections and not alerts:
        level = "LOW"
        score = 0

    return {
        "risk_score": score,
        "risk_level": level,
        "risk_color": get_risk_color(level),
        "risk_description": get_risk_description(level),
        "factors": factors,
        "event_type": event_type or "NONE",
    }
