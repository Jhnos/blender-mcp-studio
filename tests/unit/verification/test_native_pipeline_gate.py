"""Public native qualification must reject stale APIs before any job and never replay."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from scripts.verify import design_gate_checks as checks
from scripts.verify.design_pipeline_verify_real import job_budget_s, run_job
from scripts.verify.native_pipeline_verify_real import require_native_tool


async def test_native_gate_refuses_old_tool_schema_before_submitting():
    client = SimpleNamespace(
        list_tools=AsyncMock(
            return_value=[
                SimpleNamespace(
                    name="run_design_pipeline", inputSchema={"properties": {"spec": {}}}
                )
            ]
        ),
        call_tool=AsyncMock(),
    )
    with pytest.raises(checks.GateError, match="revision"):
        await require_native_tool(client)
    client.call_tool.assert_not_awaited()
    client.list_tools.return_value[0].inputSchema["properties"]["revision"] = {"type": "object"}
    await require_native_tool(client)
    client.call_tool.assert_not_awaited()


async def test_native_job_helper_sends_only_revision_and_does_not_replay_lost_reply():
    client = SimpleNamespace(call_tool=AsyncMock(side_effect=ConnectionError("reply lost")))
    request = {"recipe_id": "screen-clamp", "target_angle_deg": 30}
    with pytest.raises(ConnectionError):
        await run_job(client, None, "native", revision=request)
    client.call_tool.assert_awaited_once_with("run_design_pipeline", {"revision": request})


async def test_native_job_helper_rejects_conflicting_spec_before_submission():
    client = SimpleNamespace(call_tool=AsyncMock())
    with pytest.raises(checks.GateError):
        await run_job(
            client, {"name": "alternate"}, "native", revision={"recipe_id": "screen-clamp"}
        )
    client.call_tool.assert_not_awaited()


def test_native_poll_budget_covers_the_same_runner_and_slicer_deadlines():
    from src.adapters.generation.native_runner import (
        NATIVE_COMMAND_TIMEOUT_S,
        NATIVE_COMPLETION_TIMEOUT_S,
    )

    assert (
        job_budget_s(native=True)
        == checks.poll_budget_s() + NATIVE_COMMAND_TIMEOUT_S + NATIVE_COMPLETION_TIMEOUT_S
    )
    assert job_budget_s() == checks.poll_budget_s()


def test_real_ci_runs_public_native_job_after_existing_current_import_gate():
    from pathlib import Path

    real = (
        (Path(__file__).resolve().parents[3] / "scripts/ci.sh")
        .read_text()
        .split("if (( REAL )); then", 1)[1]
    )
    assert "scripts/verify/native_pipeline_verify_real.py" in real
    assert real.index("scripts/verify/design_pipeline_verify_real.py") < real.index(
        "scripts/verify/native_pipeline_verify_real.py"
    )
