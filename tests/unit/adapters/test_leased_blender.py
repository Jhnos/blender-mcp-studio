"""Every caller uses the same ownership gate, not just MCP handler decorators."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from src.adapters.mcp.leased_blender import LeasedBlenderPort
from src.core.domain.command import Command
from src.core.domain.exceptions import (
    BlenderBusyError,
    BlenderConnectionError,
    BlenderExecutionUncertainError,
)
from src.core.ports.blender_port import BlenderPort
from src.core.ports.mcp_port import ToolResult
from src.core.use_cases.blender_lease import BlenderLease


def setup():
    backend = AsyncMock(spec=BlenderPort)
    backend.execute.return_value = ToolResult(True, "ok")
    backend.call_tool.return_value = ToolResult(True, "ok")
    lease = BlenderLease()
    return LeasedBlenderPort(backend, lease), backend, lease


@pytest.mark.parametrize("entry", ["execute", "call_tool"])
async def test_foreign_owner_blocks_all_command_entry_paths(entry):
    port, backend, lease = setup()
    async with lease.hold("native-revision"):

        async def other():
            with pytest.raises(BlenderBusyError):
                if entry == "execute":
                    await port.execute(
                        Command(tool_name="delete_object", arguments={"name": "Cube"})
                    )
                else:
                    await port.call_tool("execute_code", {"code": "x"})

        await asyncio.create_task(other())
    backend.execute.assert_not_called()
    backend.call_tool.assert_not_called()


async def test_owner_calls_are_reentrant_but_inherited_child_tasks_are_not_owners():
    port, backend, lease = setup()
    async with lease.hold("native-revision"):
        assert (
            await port.execute(Command(tool_name="delete_object", arguments={"name": "Cube"}))
        ).success

        async def child():
            with pytest.raises(BlenderBusyError):
                await port.execute(Command(tool_name="delete_object", arguments={"name": "Cube"}))

        await asyncio.create_task(child())
    backend.execute.assert_awaited_once()
    assert not lease.busy


async def test_read_queries_remain_available_while_another_job_owns_the_lease():
    port, backend, lease = setup()
    async with lease.hold("native-revision"):

        async def reader():
            await port.scene_summary()
            await port.object_details("Cube")
            await port.viewport_screenshot(800)
            await port.call_tool("get_scene_info", {})

        await asyncio.create_task(reader())
    backend.scene_summary.assert_awaited_once()
    backend.object_details.assert_awaited_once_with("Cube")
    backend.viewport_screenshot.assert_awaited_once_with(800)


async def test_uncertain_completion_quarantines_mutations_until_matching_recovery_ticket():
    port, backend, lease = setup()
    backend.execute.side_effect = BlenderExecutionUncertainError("command completion unknown")
    with pytest.raises(BlenderExecutionUncertainError):
        await port.execute(Command(tool_name="delete_object", arguments={"name": "Cube"}))
    assert lease.busy and lease.recovery_ticket is not None
    ticket = lease.recovery_ticket
    with pytest.raises(ValueError):
        lease.resolve_quarantine("wrong-ticket")
    with pytest.raises(BlenderBusyError):
        await port.call_tool("execute_code", {"code": "x"})
    assert lease.busy
    lease.resolve_quarantine(ticket)
    backend.execute.side_effect = None
    assert (
        await port.execute(Command(tool_name="delete_object", arguments={"name": "Cube"}))
    ).success
    assert not lease.busy


async def test_cancelled_command_retains_quarantine_and_cannot_release_a_waiter_into_unknown_state():
    port, backend, lease = setup()
    started = asyncio.Event()

    async def pending(_):
        started.set()
        await asyncio.Event().wait()

    backend.execute.side_effect = pending
    task = asyncio.create_task(
        port.execute(Command(tool_name="delete_object", arguments={"name": "Cube"}))
    )
    await started.wait()
    entered = []

    async def queued():
        with pytest.raises(BlenderBusyError):
            async with lease.hold("later"):
                entered.append(True)

    waiter = asyncio.create_task(queued())
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await waiter
    assert not entered and lease.busy


@pytest.mark.parametrize("interruption", ["timeout", "eof", "cancel"])
async def test_actual_socket_uncertainty_blocks_a_second_mutation_without_replay(interruption):
    from src.adapters.mcp.blender_mcp_adapter import BlenderMCPAdapter

    received, release, finished = asyncio.Event(), asyncio.Event(), asyncio.Event()
    packets = []

    async def peer(reader, writer):
        try:
            packets.append(await reader.read(4096))
            received.set()
            if interruption != "eof":
                await release.wait()
        finally:
            writer.close()
            await writer.wait_closed()
            finished.set()

    server = await asyncio.start_server(peer, "127.0.0.1", 0)
    backend = BlenderMCPAdapter("127.0.0.1", server.sockets[0].getsockname()[1])
    backend._socket._timeout = 0.02
    lease = BlenderLease()
    port = LeasedBlenderPort(backend, lease)
    try:
        task = asyncio.create_task(port.call_tool("execute_code", {"code": "pass"}))
        await asyncio.wait_for(received.wait(), 2)
        if interruption == "cancel":
            task.cancel()
        with pytest.raises(
            asyncio.CancelledError if interruption == "cancel" else BlenderExecutionUncertainError
        ):
            await task
        assert lease.busy and not await port.is_connected()
        with pytest.raises(BlenderBusyError):
            await port.call_tool("execute_code", {"code": "second"})
        assert len(packets) == 1
    finally:
        release.set()
        await asyncio.wait_for(finished.wait(), 2)
        await port.disconnect()
        server.close()
        await server.wait_closed()


async def test_connection_failure_before_send_does_not_quarantine():
    port, backend, lease = setup()
    backend.execute.side_effect = BlenderConnectionError("cannot connect before send")
    with pytest.raises(BlenderConnectionError):
        await port.execute(Command(tool_name="delete_object"))
    assert not lease.busy and lease.recovery_ticket is None


@pytest.mark.parametrize("response", [b"[]", b"\xff"])
async def test_unusable_reply_after_a_mutation_is_unknown_not_a_script_failure(response):
    from src.adapters.mcp.blender_mcp_adapter import BlenderMCPAdapter

    finished = asyncio.Event()

    async def peer(reader, writer):
        try:
            await reader.read(4096)
            writer.write(response)
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()
            finished.set()

    server = await asyncio.start_server(peer, "127.0.0.1", 0)
    lease = BlenderLease()
    port = LeasedBlenderPort(
        BlenderMCPAdapter("127.0.0.1", server.sockets[0].getsockname()[1]), lease
    )
    try:
        with pytest.raises(BlenderExecutionUncertainError):
            await port.call_tool("execute_code", {"code": "pass"})
        assert lease.busy and not await port.is_connected()
    finally:
        await asyncio.wait_for(finished.wait(), 2)
        await port.disconnect()
        server.close()
        await server.wait_closed()
