"""WebSocket connection manager.

Maintains the set of active WebSocket connections and provides
a broadcast primitive used by the viewport live-preview background task.

This lives in the web layer (api/) — not in src/core/ — because it is
an infrastructure concern (FastAPI WebSocket), not a domain concern.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Thread-safe registry of active WebSocket connections with broadcast."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def register(self, ws: WebSocket) -> None:
        """Register an already-accepted WebSocket."""
        self._connections.add(ws)
        logger.debug("WS connected (total=%d)", len(self._connections))

    def unregister(self, ws: WebSocket) -> None:
        """Remove a WebSocket on disconnect."""
        self._connections.discard(ws)
        logger.debug("WS disconnected (total=%d)", len(self._connections))

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def has_connections(self) -> bool:
        return bool(self._connections)

    @property
    def count(self) -> int:
        return len(self._connections)

    # ------------------------------------------------------------------
    # Broadcast
    # ------------------------------------------------------------------

    async def broadcast_json(self, data: dict) -> None:
        """Send *data* to all active connections; silently drops dead ones."""
        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.unregister(ws)

    async def broadcast_viewport(self, screenshot_b64: str) -> None:
        """Convenience wrapper: broadcast a viewport_update message."""
        await self.broadcast_json({"type": "viewport_update", "screenshot": screenshot_b64})


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------

async def viewport_broadcast_loop(
    app_state,
    interval: float = 3.0,
) -> None:
    """Periodically capture the Blender viewport and push to all clients.

    Runs forever; designed to be launched as an asyncio background task.
    Only captures a screenshot when at least one WebSocket client is connected.

    Args:
        app_state: FastAPI ``app.state`` (provides ``blender`` and ``ws_manager``).
        interval:  Seconds between captures. Defaults to 3 s.
    """
    import base64
    import os
    import tempfile

    while True:
        await asyncio.sleep(interval)

        ws_manager: ConnectionManager = getattr(app_state, "ws_manager", None)
        if ws_manager is None or not ws_manager.has_connections:
            continue  # no clients — skip capture

        blender = getattr(app_state, "blender", None)
        if blender is None:
            continue

        try:
            tmp = tempfile.mktemp(suffix=".png")
            shot = await blender.call_tool("get_viewport_screenshot", {"filepath": tmp})
            if shot.success and os.path.exists(tmp):
                with open(tmp, "rb") as fh:
                    b64 = base64.b64encode(fh.read()).decode()
                os.unlink(tmp)
                await ws_manager.broadcast_viewport(b64)
        except Exception as exc:
            logger.debug("Viewport broadcast failed: %s", exc)
