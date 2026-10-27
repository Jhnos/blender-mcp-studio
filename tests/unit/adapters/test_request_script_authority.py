"""An internal program exemption belongs to one exact task and lexical scope."""

import asyncio
from contextvars import copy_context

import pytest

from src.adapters.mcp.blender_mcp_adapter import BlenderMCPAdapter
from src.adapters.security.blender_code_sandbox import BlenderCodeSandbox
from src.adapters.security.request_script_authority import RequestScriptAuthority
from src.core.domain.command import Command

CODE = "import sys\nprint('internally derived job')"


async def test_exact_program_is_authorized_only_inside_its_owning_scope():
    authority = RequestScriptAuthority()
    assert authority.timeout_for(CODE) is None
    with authority.scope(CODE, timeout=120):
        assert authority.timeout_for(CODE) == 120
        assert authority.timeout_for(CODE + "\n") is None
        assert RequestScriptAuthority().timeout_for(CODE) is None
    assert authority.timeout_for(CODE) is None


async def test_child_task_and_copied_thread_context_cannot_borrow_a_live_grant():
    authority = RequestScriptAuthority()

    async def lookup():
        return authority.timeout_for(CODE)

    with authority.scope(CODE, timeout=120):
        child = asyncio.create_task(lookup())  # ContextVar values are inherited.
        assert await child is None
        assert await asyncio.to_thread(authority.timeout_for, CODE) is None
        assert authority.timeout_for(CODE) == 120


async def test_unrelated_request_cannot_replay_another_live_requests_exact_program():
    authority = RequestScriptAuthority()
    granted, release = asyncio.Event(), asyncio.Event()

    async def owner():
        with authority.scope(CODE, timeout=120):
            granted.set()
            await release.wait()
            assert authority.timeout_for(CODE) == 120

    task = asyncio.create_task(owner())
    await granted.wait()
    try:
        assert authority.timeout_for(CODE) is None
    finally:
        release.set()
        await task


async def test_nested_scope_restores_the_outer_program_after_failure():
    authority = RequestScriptAuthority()
    with authority.scope(CODE, timeout=120):
        with (
            pytest.raises(RuntimeError, match="operation failed"),
            authority.scope("import sys\nprint('inner')", timeout=60),
        ):
            assert authority.timeout_for(CODE) is None
            raise RuntimeError("operation failed")
        assert authority.timeout_for(CODE) == 120
    assert authority.timeout_for(CODE) is None


async def test_a_copied_context_cannot_resurrect_a_scope_after_it_has_exited():
    authority = RequestScriptAuthority()
    with authority.scope(CODE, timeout=120):
        saved = copy_context()
        assert saved.run(authority.timeout_for, CODE) == 120
    assert saved.run(authority.timeout_for, CODE) is None


async def test_cancellation_clears_the_grant_before_the_same_task_continues():
    authority = RequestScriptAuthority()
    granted = asyncio.Event()

    async def owner():
        try:
            with authority.scope(CODE, timeout=120):
                granted.set()
                await asyncio.Event().wait()
        except asyncio.CancelledError:
            return authority.timeout_for(CODE)

    task = asyncio.create_task(owner())
    await granted.wait()
    task.cancel()
    assert await task is None


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan"), True, "120", 10**1000])
async def test_invalid_deadlines_never_create_a_grant(timeout):
    authority = RequestScriptAuthority()
    with pytest.raises(ValueError, match="timeout"), authority.scope(CODE, timeout=timeout):
        pytest.fail("invalid grant entered")
    assert authority.timeout_for(CODE) is None


def test_grant_cannot_be_created_outside_an_async_request():
    with (
        pytest.raises(RuntimeError, match="task"),
        RequestScriptAuthority().scope(CODE, timeout=120),
    ):
        pytest.fail("synchronous grant entered")


async def test_shared_adapter_uses_the_same_exact_grant_for_sandbox_and_deadline(monkeypatch):
    authority = RequestScriptAuthority()
    sandbox = BlenderCodeSandbox(scoped_timeout=authority.timeout_for)
    adapter = BlenderMCPAdapter("unused", 1, sandbox, scoped_timeout=authority.timeout_for)
    calls = []

    async def send(payload, *, timeout=None):
        calls.append((payload, timeout))
        return {"status": "success", "result": {"executed": True}}

    monkeypatch.setattr(adapter._socket, "send_command", send)
    command = Command(tool_name="execute_code", arguments={"code": CODE})
    assert not (await adapter.execute(command)).success
    assert not calls
    with authority.scope(CODE, timeout=120):
        assert (await adapter.execute(command)).success
        assert len(calls) == 1 and calls[0][1] == 120
        assert not (await asyncio.create_task(adapter.execute(command))).success
        assert len(calls) == 1
    assert not (await adapter.execute(command)).success
    assert len(calls) == 1


async def test_factory_injects_scoped_deadlines_without_changing_static_exemptions(monkeypatch):
    from src.adapters.mcp.factory import build_blender_adapter

    monkeypatch.setenv("BLENDER_TRANSPORT", "socket")
    authority = RequestScriptAuthority()
    sandbox = BlenderCodeSandbox(
        authorized=lambda: frozenset({CODE}), scoped_timeout=authority.timeout_for
    )
    adapter = build_blender_adapter(sandbox=sandbox, scoped_timeout=authority.timeout_for)
    assert isinstance(adapter, BlenderMCPAdapter)
    assert sandbox.validate(CODE).allowed
    assert authority.timeout_for(CODE) is None


async def test_unsupported_transport_cannot_silently_drop_the_scoped_policy(monkeypatch):
    from src.adapters.mcp.factory import build_blender_adapter

    monkeypatch.setenv("BLENDER_TRANSPORT", "mcp_sse")
    with pytest.raises(ValueError, match="shared socket"):
        build_blender_adapter(scoped_timeout=RequestScriptAuthority().timeout_for)


async def test_real_loopback_socket_observes_the_scoped_deadline():
    import json

    authority = RequestScriptAuthority()
    received = []
    closed = asyncio.Event()

    async def peer(reader, writer):
        try:
            received.append(json.loads(await reader.read(4096)))
            await asyncio.sleep(0.02)
            writer.write(b'{"status":"success","result":{"actual_socket":true}}')
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()
            closed.set()

    server = await asyncio.start_server(peer, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    sandbox = BlenderCodeSandbox(scoped_timeout=authority.timeout_for)
    adapter = BlenderMCPAdapter("127.0.0.1", port, sandbox, scoped_timeout=authority.timeout_for)
    adapter._socket._timeout = 0.001  # A missing scoped deadline must really fail.
    try:
        with authority.scope(CODE, timeout=2):
            outcome = await adapter.execute(
                Command(tool_name="execute_code", arguments={"code": CODE})
            )
        assert outcome.success and outcome.output == {"actual_socket": True}
        assert received == [{"type": "execute_code", "params": {"code": CODE}}]
        assert authority.timeout_for(CODE) is None
        await asyncio.wait_for(closed.wait(), 2)
    finally:
        await adapter.disconnect()
        server.close()
        await server.wait_closed()


async def test_cancellation_drain_keeps_the_grant_inside_its_worker_until_completion():
    from src.core.use_cases.blender_lease import BlenderLease, run_to_completion

    authority, lease = RequestScriptAuthority(), BlenderLease()
    started, release = asyncio.Event(), asyncio.Event()
    observed = []

    async def work():
        with authority.scope(CODE, timeout=120):
            started.set()
            await release.wait()
            observed.append(authority.timeout_for(CODE))
        observed.append(authority.timeout_for(CODE))

    async def owner():
        async with lease.hold("native-revision"):
            await run_to_completion(work())

    task = asyncio.create_task(owner())
    await started.wait()
    for _ in range(3):
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done() and lease.busy
        assert authority.timeout_for(CODE) is None
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert observed == [120, None] and not lease.busy
