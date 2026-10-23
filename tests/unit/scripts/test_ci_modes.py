"""Execute the real CI dispatcher with fake boundaries, never a live service."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def drive(
    tmp_path: Path, *args: str, fail: str = ""
) -> tuple[subprocess.CompletedProcess[str], str]:
    trace = tmp_path / "trace"
    executable = tmp_path / "stub"
    executable.write_text(
        '#!/bin/bash\nprintf "%s\\n" "$*" >> "$TRACE"\n'
        'if [[ -n "$FAIL_GATE" && "$*" == *"$FAIL_GATE"* ]]; then exit 1; fi\n'
    )
    executable.chmod(0o755)
    for name in ("npm", "npx", "nc"):
        (tmp_path / name).symlink_to(executable)
    result = subprocess.run(
        ["bash", "scripts/ci.sh", *args],
        cwd=ROOT,
        env={
            **os.environ,
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "CI_PYTHON": str(executable),
            "TRACE": str(trace),
            "FAIL_GATE": fail,
            "CI_LOG_DIR": str(tmp_path / "logs"),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    return result, trace.read_text() if trace.exists() else ""


@pytest.mark.parametrize("args", [(), ("--real",)])
def test_core_never_invokes_ollama_chat(tmp_path: Path, args: tuple[str, ...]) -> None:
    result, trace = drive(tmp_path, *args, fail="mcp_verify_chat.py")
    assert result.returncode == 0, result.stdout
    assert "mcp_verify_chat.py" not in trace
    assert "-m pytest" in trace
    if args:
        assert "mcp_verify_real.py" in trace
        assert "design_pipeline_v80.json" in trace


def test_chat_is_independent_and_failure_is_fatal(tmp_path: Path) -> None:
    result, trace = drive(tmp_path, "--chat", fail="mcp_verify_chat.py")
    assert result.returncode == 1
    assert "mcp_verify_chat.py" in trace
    assert "design_pipeline_v80.json" not in trace
    assert "-m pytest" not in trace
    assert "CI PASSED" not in result.stdout


def test_all_runs_core_before_chat(tmp_path: Path) -> None:
    result, trace = drive(tmp_path, "--all")
    assert result.returncode == 0, result.stdout
    assert trace.index("design_pipeline_v80.json") < trace.index("mcp_verify_chat.py")
    assert trace.count("mcp_verify_chat.py") == 1


def test_unknown_option_fails_before_running_checks(tmp_path: Path) -> None:
    result, trace = drive(tmp_path, "--typo")
    assert result.returncode == 2
    assert trace == ""


def test_chat_requires_blender_instead_of_vacuous_success(tmp_path: Path) -> None:
    result, trace = drive(tmp_path, "--chat", fail="-z localhost")
    assert result.returncode != 0
    assert "mcp_verify_chat.py" not in trace
    assert "CI PASSED" not in result.stdout


def test_core_failure_prevents_chat_from_mutating_shared_scene(tmp_path: Path) -> None:
    result, trace = drive(tmp_path, "--all", fail="mcp_verify_real.py")
    assert result.returncode == 1
    assert "mcp_verify_chat.py" not in trace


def test_chat_can_pass_without_running_model_or_slicing_gates(tmp_path: Path) -> None:
    result, trace = drive(tmp_path, "--chat")
    assert result.returncode == 0, result.stdout
    assert "mcp_verify_chat.py" in trace
    assert "design_pipeline_v80.json" not in trace
    assert "-m pytest" not in trace
