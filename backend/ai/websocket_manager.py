"""
SentinelAI WebSocket Manager

Lightweight connection manager for real-time SentinelAI updates.
Designed to work with FastAPI WebSocket connections.

The manager is intentionally defensive so the backend remains
usable even when no WebSocket clients are connected.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional


class WebSocketManager:
    """Manage connected WebSocket clients."""

    def __init__(self) -> None:
        self.active_connections: list[Any] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: Any) -> None:
        """Accept and register a WebSocket connection."""
        try:
            await websocket.accept()
        except Exception:
            # Some callers/tests may provide an already accepted
            # or lightweight mock connection.
            pass

        async with self._lock:
            if websocket not in self.active_connections:
                self.active_connections.append(websocket)

    def disconnect(self, websocket: Any) -> None:
        """Remove a WebSocket connection if present."""
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass

    async def send_personal_message(
        self,
        message: Any,
        websocket: Any,
    ) -> bool:
        """Send a message to one client."""
        try:
            await websocket.send_json(message)
            return True
        except Exception:
            self.disconnect(websocket)
            return False

    async def broadcast(self, message: Any) -> int:
        """Broadcast a JSON message to all connected clients."""
        async with self._lock:
            connections = list(self.active_connections)

        sent = 0
        failed = []

        for websocket in connections:
            try:
                await websocket.send_json(message)
                sent += 1
            except Exception:
                failed.append(websocket)

        for websocket in failed:
            self.disconnect(websocket)

        return sent

    async def broadcast_event(
        self,
        event_type: str,
        data: Optional[Any] = None,
    ) -> int:
        """Broadcast a standard SentinelAI event envelope."""
        payload = {
            "type": str(event_type),
            "event": str(event_type),
            "data": data,
        }

        return await self.broadcast(payload)

    def get_connection_count(self) -> int:
        """Return the current number of connected clients."""
        return len(self.active_connections)

    def clear(self) -> None:
        """Clear all tracked connections."""
        self.active_connections.clear()


_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """Return the singleton WebSocketManager."""
    global _manager

    if _manager is None:
        _manager = WebSocketManager()

    return _manager


__all__ = [
    "WebSocketManager",
    "get_websocket_manager",
]
