"""Tests for ConnectionManager and viewport_broadcast_loop."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.routers.ws_manager import ConnectionManager, viewport_broadcast_loop


# ---------------------------------------------------------------------------
# ConnectionManager unit tests
# ---------------------------------------------------------------------------


class TestConnectionManager:
    def test_register_increases_count(self):
        mgr = ConnectionManager()
        ws = MagicMock()
        mgr.register(ws)
        assert mgr.count == 1
        assert mgr.has_connections

    def test_unregister_decreases_count(self):
        mgr = ConnectionManager()
        ws = MagicMock()
        mgr.register(ws)
        mgr.unregister(ws)
        assert mgr.count == 0
        assert not mgr.has_connections

    def test_unregister_unknown_ws_is_idempotent(self):
        mgr = ConnectionManager()
        mgr.unregister(MagicMock())  # no error

    def test_has_connections_false_when_empty(self):
        mgr = ConnectionManager()
        assert not mgr.has_connections

    @pytest.mark.asyncio
    async def test_broadcast_json_sends_to_all(self):
        mgr = ConnectionManager()
        ws1, ws2 = AsyncMock(), AsyncMock()
        mgr.register(ws1)
        mgr.register(ws2)
        await mgr.broadcast_json({"type": "ping"})
        ws1.send_json.assert_awaited_once_with({"type": "ping"})
        ws2.send_json.assert_awaited_once_with({"type": "ping"})

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_connections(self):
        mgr = ConnectionManager()
        ws_alive = AsyncMock()
        ws_dead = AsyncMock()
        ws_dead.send_json.side_effect = RuntimeError("closed")
        mgr.register(ws_alive)
        mgr.register(ws_dead)

        await mgr.broadcast_json({"type": "test"})

        assert mgr.count == 1
        assert ws_dead not in mgr._connections
        assert ws_alive in mgr._connections

    @pytest.mark.asyncio
    async def test_broadcast_viewport_wraps_screenshot(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        mgr.register(ws)
        await mgr.broadcast_viewport("abc123")
        ws.send_json.assert_awaited_once_with(
            {"type": "viewport_update", "screenshot": "abc123"}
        )

    @pytest.mark.asyncio
    async def test_broadcast_json_no_connections_is_noop(self):
        mgr = ConnectionManager()
        await mgr.broadcast_json({"type": "ping"})  # no error


# ---------------------------------------------------------------------------
# viewport_broadcast_loop tests
# ---------------------------------------------------------------------------


class FakeShot:
    success = True


class FakeAppState:
    def __init__(self, blender, ws_manager):
        self.blender = blender
        self.ws_manager = ws_manager


@pytest.mark.asyncio
async def test_broadcast_loop_skips_when_no_connections():
    """Loop should not call Blender at all when no clients are connected."""
    mgr = ConnectionManager()  # empty
    blender = AsyncMock()
    state = FakeAppState(blender, mgr)

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        # Make loop run once then cancel
        call_count = 0

        async def sleep_side_effect(t):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise asyncio.CancelledError

        mock_sleep.side_effect = sleep_side_effect
        with pytest.raises(asyncio.CancelledError):
            await viewport_broadcast_loop(state, interval=0.01)

    blender.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_broadcast_loop_sends_when_connected(tmp_path):
    """Loop captures screenshot and broadcasts when clients present."""
    mgr = ConnectionManager()
    ws = AsyncMock()
    mgr.register(ws)

    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8

    blender = AsyncMock()
    blender.call_tool.return_value = FakeShot()

    state = FakeAppState(blender, mgr)

    call_count = 0

    async def sleep_side_effect(t):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError

    with (
        patch("asyncio.sleep", new_callable=AsyncMock, side_effect=sleep_side_effect),
        patch("tempfile.mktemp", return_value=str(tmp_path / "shot.png")),
        patch("builtins.open", create=True) as mock_open,
        patch("os.path.exists", return_value=True),
        patch("os.unlink"),
    ):
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.read = MagicMock(return_value=png_bytes)

        with pytest.raises(asyncio.CancelledError):
            await viewport_broadcast_loop(state, interval=0.01)

    blender.call_tool.assert_called_once()
    ws.send_json.assert_awaited_once()
    sent = ws.send_json.call_args[0][0]
    assert sent["type"] == "viewport_update"
    assert "screenshot" in sent


@pytest.mark.asyncio
async def test_broadcast_loop_continues_after_blender_error():
    """Loop must not crash if Blender raises — just log and continue."""
    mgr = ConnectionManager()
    ws = AsyncMock()
    mgr.register(ws)

    blender = AsyncMock()
    blender.call_tool.side_effect = RuntimeError("Blender offline")

    state = FakeAppState(blender, mgr)
    call_count = 0

    async def sleep_side_effect(t):
        nonlocal call_count
        call_count += 1
        if call_count >= 3:
            raise asyncio.CancelledError

    with patch("asyncio.sleep", new_callable=AsyncMock, side_effect=sleep_side_effect):
        with pytest.raises(asyncio.CancelledError):
            await viewport_broadcast_loop(state, interval=0.01)

    # No screenshot sent — but no crash either
    ws.send_json.assert_not_awaited()
