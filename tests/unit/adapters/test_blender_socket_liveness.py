"""A dead Blender socket must be visible as a dead socket.

`/api/health`'s `blender` field is the project's declared readiness signal
(docs/30-verification.md), and `LESSONS_LEARNED.md` already records the failure
class: a dropped addon connection that degrades into a *content* error sends the
reader hunting for a data-format bug instead of a connection bug.

`StreamWriter.is_closing()` only reports whether *this* side asked to close, so
it stays False forever after Blender exits — health then reports `connected`
while port 9876 is shut. These tests use a real loopback server (no mocks) and
pin both halves: the signal must go false when the peer leaves, and must stay
true while the peer is holding the socket.
"""

from __future__ import annotations

import asyncio

import pytest

from src.adapters.mcp.blender_mcp_adapter import BlenderSocketClient
from src.core.domain.exceptions import BlenderConnectionError

_DEADLINE = 2.0


async def _serve(handler) -> tuple[asyncio.Server, int]:
    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    return server, int(server.sockets[0].getsockname()[1])


async def _hangs_up(_reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Stands in for Blender quitting right after the API connected."""
    writer.close()
    await writer.wait_closed()


async def _holds_the_socket(_reader: asyncio.StreamReader, _writer: asyncio.StreamWriter) -> None:
    """Stands in for a healthy addon: accepts and keeps the connection open."""
    await asyncio.sleep(_DEADLINE * 2)


async def _connected_client(handler) -> tuple[BlenderSocketClient, asyncio.Server]:
    server, port = await _serve(handler)
    client = BlenderSocketClient(host="127.0.0.1", port=port, timeout=1.0)
    await client.connect()
    return client, server


async def _wait_until_not_connected(client: BlenderSocketClient) -> bool:
    """Poll the signal under test until the deadline; report what it settled on."""
    loop = asyncio.get_running_loop()
    end = loop.time() + _DEADLINE
    while loop.time() < end:
        if not client.is_connected:
            return True
        await asyncio.sleep(0.02)
    return not client.is_connected


@pytest.mark.asyncio
async def test_is_connected_goes_false_after_the_addon_hangs_up() -> None:
    client, server = await _connected_client(_hangs_up)
    try:
        assert await _wait_until_not_connected(client), (
            "is_connected still reports True after the addon closed the socket — "
            "/api/health would report `connected` with Blender gone"
        )
    finally:
        await client.disconnect()
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_is_connected_stays_true_while_the_addon_holds_the_socket() -> None:
    client, server = await _connected_client(_holds_the_socket)
    try:
        assert client.is_connected
        await asyncio.sleep(0.2)
        assert client.is_connected, "a live addon connection must not be reported as dead"
    finally:
        await client.disconnect()
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_send_command_on_a_dead_socket_raises_a_connection_error() -> None:
    """The empty reply from a dead socket must not surface as a decode failure."""
    client, server = await _connected_client(_hangs_up)
    try:
        await _wait_until_not_connected(client)
        with pytest.raises(BlenderConnectionError):
            await client.send_command({"type": "get_scene_info", "params": {}})
    finally:
        await client.disconnect()
        server.close()
        await server.wait_closed()
