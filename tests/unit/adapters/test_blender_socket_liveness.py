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
import json

import pytest

from src.adapters.mcp.blender_mcp_adapter import BlenderMCPClient, BlenderSocketClient
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


def _hangs_up_once_then_answers() -> tuple[object, dict[str, int]]:
    """Stands in for Blender being restarted underneath a long-lived API process."""
    served = {"connections": 0}

    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        served["connections"] += 1
        if served["connections"] == 1:
            writer.close()
            await writer.wait_closed()
            return
        await reader.read(4096)
        writer.write(json.dumps({"status": "success", "result": {}}).encode("utf-8"))
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    return handler, served


@pytest.mark.asyncio
async def test_send_command_dials_back_after_the_addon_returns() -> None:
    """Detecting a dead peer is not the same as recovering from one.

    Observed on the production machine, 2026-09-07: `connect()` is only ever called
    at API startup, so once the link dropped it stayed dropped for the life of the
    process — `/api/health` reported `disconnected` for hours with Blender alive and
    listening, and restarting the service was the only cure. The signal was right; the
    recovery did not exist.
    """
    handler, served = _hangs_up_once_then_answers()
    client, server = await _connected_client(handler)
    try:
        assert await _wait_until_not_connected(client), "test needs the first peer to hang up"

        reply = await client.send_command({"type": "get_scene_info", "params": {}})

        assert reply["status"] == "success"
        assert served["connections"] == 2, (
            "the client never dialled back — a dropped link stays dropped until the "
            "whole process is restarted"
        )
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


@pytest.mark.asyncio
async def test_timeout_is_not_reported_as_a_failed_script() -> None:
    server, port = await _serve(_holds_the_socket)
    socket = BlenderSocketClient("127.0.0.1", port, timeout=0.02)
    client = BlenderMCPClient(socket)
    try:
        with pytest.raises(BlenderConnectionError, match="completion is unknown"):
            await client.call_tool("execute_code", {"code": "pass"})
        assert not socket.is_connected
    finally:
        await socket.disconnect()
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool,code,allowed",
    [
        ("execute_code", "registered", True),
        ("execute_code", "other", False),
        ("get_scene_info", "registered", False),
    ],
)
async def test_only_exact_registered_scripts_receive_their_longer_deadline(
    tool: str, code: str, allowed: bool
) -> None:
    async def slow_reply(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            await reader.read(4096)
            await asyncio.sleep(0.04)
            writer.write(b'{"status":"success","result":"done"}')
            await writer.drain()
        finally:
            writer.close()

    server, port = await _serve(slow_reply)
    socket = BlenderSocketClient("127.0.0.1", port, timeout=0.01)
    client = BlenderMCPClient(socket, script_timeouts={"registered": 0.5})
    try:
        if allowed:
            result = await client.call_tool(tool, {"code": code})
            assert result.success and result.output == "done"
        else:
            with pytest.raises(BlenderConnectionError, match="completion is unknown"):
                await client.call_tool(tool, {"code": code})
    finally:
        await socket.disconnect()
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
@pytest.mark.parametrize("interruption", ["timeout", "cancel"])
async def test_interrupted_request_cannot_poison_next_reply(interruption: str) -> None:
    received = asyncio.Event()
    release = asyncio.Event()
    finished = asyncio.Event()
    connections = 0

    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        nonlocal connections
        connections += 1
        ordinal = connections
        try:
            await reader.read(4096)
            if ordinal == 1:
                received.set()
                await release.wait()
            writer.write(json.dumps({"request": ordinal}).encode())
            await writer.drain()
            if ordinal == 1:
                finished.set()
                await reader.read(4096)
        except ConnectionError:
            pass
        finally:
            if ordinal == 1:
                finished.set()
            writer.close()

    server, port = await _serve(handler)
    client = BlenderSocketClient("127.0.0.1", port, timeout=0.05)
    await client.connect()
    try:
        first = asyncio.create_task(client.send_command({"type": "first"}))
        await asyncio.wait_for(received.wait(), _DEADLINE)
        if interruption == "cancel":
            first.cancel()
        with pytest.raises(TimeoutError if interruption == "timeout" else asyncio.CancelledError):
            await first
        release.set()
        await asyncio.wait_for(finished.wait(), _DEADLINE)
        reply = await client.send_command({"type": "second"})
        assert reply == {"request": 2}, "late first reply was returned to the second caller"
        assert connections == 2
    finally:
        release.set()
        await client.disconnect()
        server.close()
        await server.wait_closed()
