"""Safe dispatch provider abstraction.

The default provider only updates local simulated unit state. It never contacts
real emergency services or claims that a real unit was dispatched.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any


class DispatchProvider:
    name = "unavailable"

    def dispatch(self, response_id: str, unit_id: str, eta_minutes: int | None = None) -> dict[str, Any]:
        raise NotImplementedError


class SimulationDispatchProvider(DispatchProvider):
    name = "simulation"

    def dispatch(self, response_id: str, unit_id: str, eta_minutes: int | None = None) -> dict[str, Any]:
        return {
            "response_id": response_id,
            "unit_id": unit_id,
            "status": "DISPATCHED",
            "eta_minutes": eta_minutes,
            "mode": "SIMULATED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


class ExternalDispatchProvider(DispatchProvider):
    name = "external"

    def dispatch(self, response_id: str, unit_id: str, eta_minutes: int | None = None) -> dict[str, Any]:
        raise RuntimeError("External dispatch provider is not configured")


def get_dispatch_provider() -> DispatchProvider:
    mode = os.getenv("DISPATCH_MODE", "simulation").strip().lower()
    if mode == "external":
        return ExternalDispatchProvider()
    if mode == "simulation":
        return SimulationDispatchProvider()
    return DispatchProvider()


def dispatch_status() -> dict[str, Any]:
    provider = get_dispatch_provider()
    return {
        "mode": os.getenv("DISPATCH_MODE", "simulation").strip().lower(),
        "provider": provider.name,
        "safe_simulation": provider.name == "simulation",
        "description": "Local simulated dispatch only" if provider.name == "simulation" else "External dispatch is not configured",
    }
