"""Provider-neutral location abstraction for cameras and response units."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any


SOURCES = {"CAMERA", "GPS", "MANUAL", "SIMULATED", "UNAVAILABLE"}


def unavailable_location() -> dict[str, Any]:
    return {"latitude": None, "longitude": None, "accuracy": None, "source": "UNAVAILABLE", "timestamp": None}


class LocationProvider:
    name = "unavailable"

    def get_location(self, subject_id: str) -> dict[str, Any]:
        return unavailable_location()


class SimulatedLocationProvider(LocationProvider):
    name = "simulation"

    def get_location(self, subject_id: str) -> dict[str, Any]:
        # No coordinates are invented; simulation is explicitly unavailable unless configured.
        return {**unavailable_location(), "source": "SIMULATED", "timestamp": datetime.now(timezone.utc).isoformat()}


class ManualLocationProvider(LocationProvider):
    name = "manual"

    def get_location(self, subject_id: str) -> dict[str, Any]:
        return unavailable_location()


class GPSLocationProvider(LocationProvider):
    name = "gps"

    def get_location(self, subject_id: str) -> dict[str, Any]:
        return unavailable_location()


def get_location_provider() -> LocationProvider:
    mode = os.getenv("GPS_MODE", "simulation").strip().lower()
    if mode == "gps":
        return GPSLocationProvider()
    if mode == "manual":
        return ManualLocationProvider()
    if mode == "simulation":
        return SimulatedLocationProvider()
    return LocationProvider()


def location_status() -> dict[str, Any]:
    provider = get_location_provider()
    return {
        "mode": os.getenv("GPS_MODE", "simulation").strip().lower(),
        "provider": provider.name,
        "available": provider.name in {"gps", "manual", "simulation"},
        "description": "Provider configured; coordinates are unavailable" if provider.name != "unavailable" else "No location provider configured",
    }
