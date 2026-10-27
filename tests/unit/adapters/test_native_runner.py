"""Protocol controls use an opaque native; actual geometry is qualified separately."""

import asyncio
import hashlib
from dataclasses import asdict
from unittest.mock import AsyncMock

import pytest

from src.adapters.artifacts.native_execution import NativeExecutionJournal
from src.adapters.generation.native_runner import NativeRunner
from src.adapters.mcp.leased_blender import LeasedBlenderPort
from src.adapters.security.request_script_authority import RequestScriptAuthority
from src.core.domain.exceptions import BlenderBusyError, BlenderExecutionUncertainError
from src.core.domain.model_spec import ImportedArtifact, ModelSpec
from src.core.domain.native_revision import (
    NativeModelSource,
    NativeRevisionRequest,
    PreparedNativeRevision,
    SourceArtifact,
    StagedNativeSource,
)
from src.core.ports.blender_port import BlenderPort
from src.core.ports.mcp_port import ToolResult
from src.core.use_cases.blender_lease import BlenderLease


def fixture(tmp_path):
    directory = "a" * 32 + "/native-source"
    snapshot = tmp_path / directory
    snapshot.mkdir(parents=True)

    def asset(name, payload):
        path = snapshot / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return SourceArtifact(name, hashlib.sha256(payload).hexdigest(), len(payload))

    native = asset("native.blend", b"opaque native")
    parts = tuple(
        asset("STL/" + name + ".stl", b"part")
        for name in ("LS_FIT_lcd_back", "LS_FIT_lid", "TE_pH_temp_three_point_wrist")
    )
    source = NativeModelSource("selected", "models/selected", native, parts, None, "0" * 64, 4, 25)
    spec = ModelSpec("1", "selected", ImportedArtifact("models/selected", "STL/*.stl"))
    prepared = PreparedNativeRevision(
        spec, NativeRevisionRequest("screen-clamp", 30), StagedNativeSource(source, directory)
    )
    lease, authority = BlenderLease(), RequestScriptAuthority()
    backend = AsyncMock(spec=BlenderPort)
    port = LeasedBlenderPort(backend, lease)
    runner = NativeRunner(
        port, lease, authority, tmp_path, completion_timeout=0.1, poll_interval=0.001
    )
    return prepared, lease, authority, backend, port, runner


def finish(directory):
    journal = NativeExecutionJournal(directory)

    def output(name, payload):
        path = directory / name
        path.write_bytes(payload)
        return asdict(SourceArtifact(name, hashlib.sha256(payload).hexdigest(), len(payload)))

    journal.publish_terminal(
        {
            **journal.identity(),
            "status": "completed",
            "restored": True,
            "output": output("candidate.blend", b"saved"),
            "surfaces": output("changed-surfaces.json", b"{}"),
            "error": None,
        }
    )


async def test_execution_consumes_captured_context_and_grant_in_the_lease_owner(tmp_path):
    prepared, lease, authority, backend, _, runner = fixture(tmp_path)
    directory = tmp_path / ("a" * 32) / "native-execution"

    async def execute(command):
        assert authority.timeout_for(command.arguments["code"]) is not None
        assert lease.holder == "native-revision"
        finish(directory)
        return ToolResult(True, "reply is not the completion evidence")

    backend.execute.side_effect = execute
    result = await runner.execute(prepared)
    assert result.prepared is prepared and result.native.path == "candidate.blend"
    assert result.directory == "a" * 32 + "/native-execution"
    assert not lease.busy and not NativeExecutionJournal(directory).unfinished()
    backend.execute.assert_awaited_once()


async def test_late_terminal_resolves_timeout_without_replay_and_blocks_foreign_mutation(tmp_path):
    prepared, lease, authority, backend, port, runner = fixture(tmp_path)
    sent = asyncio.Event()
    directory = tmp_path / ("a" * 32) / "native-execution"

    async def execute(command):
        sent.set()
        raise BlenderExecutionUncertainError("late response")

    backend.execute.side_effect = execute
    task = asyncio.create_task(runner.execute(prepared))
    await sent.wait()
    while lease.recovery_ticket is None:
        await asyncio.sleep(0)
    with pytest.raises(BlenderBusyError):
        await port.call_tool("execute_code", {"code": "foreign"})
    assert authority.timeout_for("foreign") is None
    finish(directory)
    result = await task
    assert result.prepared is prepared and not lease.busy
    backend.execute.assert_awaited_once()


async def test_missing_terminal_stays_isolated_across_runner_restart(tmp_path):
    prepared, lease, _, backend, _, runner = fixture(tmp_path)
    backend.execute.side_effect = BlenderExecutionUncertainError("lost reply")
    with pytest.raises(BlenderExecutionUncertainError):
        await runner.execute(prepared)
    assert lease.busy
    next_lease = BlenderLease()
    restarted = NativeRunner(
        AsyncMock(spec=BlenderPort), next_lease, RequestScriptAuthority(), tmp_path
    )
    assert await restarted.recover_unfinished() == 1
    assert next_lease.busy
    finish(tmp_path / ("a" * 32) / "native-execution")
    assert await restarted.recover_unfinished() == 0
    assert not next_lease.busy


async def test_repeated_cancellation_drains_the_same_worker_and_receipt(tmp_path):
    prepared, lease, authority, backend, _, runner = fixture(tmp_path)
    started, release = asyncio.Event(), asyncio.Event()
    directory = tmp_path / ("a" * 32) / "native-execution"

    async def execute(command):
        assert authority.timeout_for(command.arguments["code"]) is not None
        started.set()
        await release.wait()
        finish(directory)
        return ToolResult(True, "done")

    backend.execute.side_effect = execute
    task = asyncio.create_task(runner.execute(prepared))
    await started.wait()
    for _ in range(3):
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done() and lease.busy
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not lease.busy and not NativeExecutionJournal(directory).unfinished()
    backend.execute.assert_awaited_once()


async def test_unexpected_dispatch_failure_is_also_isolated(tmp_path):
    prepared, lease, _, backend, _, runner = fixture(tmp_path)
    backend.execute.side_effect = RuntimeError("unexpected dispatch failure")
    with pytest.raises(RuntimeError):
        await runner.execute(prepared)
    assert lease.busy


async def test_cancelling_a_queued_revision_does_not_start_it_later(tmp_path):
    prepared, lease, _, backend, _, runner = fixture(tmp_path)
    task = None
    try:
        async with lease.hold("another-job"):
            task = asyncio.create_task(runner.execute(prepared))
            for _ in range(4):
                await asyncio.sleep(0)
            task.cancel()
            for _ in range(12):
                await asyncio.sleep(0)
            assert task.done(), "cancelled queued work must not wait and then mutate later"
            backend.execute.assert_not_awaited()
            assert not (tmp_path / ("a" * 32) / "native-execution").exists()
    finally:
        if task is not None:
            await asyncio.gather(task, return_exceptions=True)


def test_generated_program_and_its_dependency_bootstrap_compile(tmp_path):
    prepared, _, _, _, _, runner = fixture(tmp_path)
    body, _ = runner.program(prepared)
    compile(body, "<native-body>", "exec")
    compile(runner.dispatch_program(body), "<native-dispatch>", "exec")
    assert "scripts.native_revision_execution" in body
    assert "scripts.lab_station_screen_clamp" in body


def test_program_fingerprint_includes_the_transitive_callback_source(tmp_path, monkeypatch):
    import src.adapters.generation.native_runner as module

    prepared, _, _, _, _, runner = fixture(tmp_path)
    repository = tmp_path / "repository"
    scripts = repository / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "native_revision_execution.py").write_text("import scripts.helper\n")
    (scripts / "verify").mkdir()
    checker = scripts / "verify/native_revision_checks.py"
    checker.write_text("VALUE = 1\n")
    helper = scripts / "helper.py"
    helper.write_text("VALUE = 1\n")
    monkeypatch.setattr(module, "ROOT", repository)
    before, _ = runner.program(prepared)
    helper.write_text("VALUE = 2\n")
    after, _ = runner.program(prepared)
    assert before != after
    checker.write_text("VALUE = 2\n")
    changed_checker, _ = runner.program(prepared)
    assert changed_checker != after
    with pytest.raises(RuntimeError, match="source fingerprint"):
        exec(before, {"_native_program_sha256": "unused"})


async def test_verified_failed_callback_releases_engine_and_keeps_raw_error_private(tmp_path):
    from src.core.domain.native_revision import NativeSceneError

    prepared, lease, _, backend, _, runner = fixture(tmp_path)
    directory = tmp_path / ("a" * 32) / "native-execution"

    async def execute(command):
        journal = NativeExecutionJournal(directory)
        journal.publish_terminal(
            {
                **journal.identity(),
                "status": "failed",
                "restored": True,
                "output": None,
                "surfaces": None,
                "error": str(tmp_path / "private-diagnostic"),
            }
        )
        return ToolResult(False, None, "script failed")

    backend.execute.side_effect = execute
    with pytest.raises(NativeSceneError) as caught:
        await runner.execute(prepared)
    assert str(tmp_path) not in str(caught.value)
    assert not lease.busy and not NativeExecutionJournal(directory).unfinished()


async def test_terminal_after_the_observation_deadline_can_recover_without_restart(tmp_path):
    prepared, lease, _, backend, _, runner = fixture(tmp_path)
    backend.execute.side_effect = BlenderExecutionUncertainError("lost reply")
    with pytest.raises(BlenderExecutionUncertainError):
        await runner.execute(prepared)
    assert await runner.recover_unfinished() == 1
    assert lease.busy
    finish(tmp_path / ("a" * 32) / "native-execution")
    assert await runner.recover_unfinished() == 0
    assert not lease.busy
