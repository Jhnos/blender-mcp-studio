"""A gate that fails and leaves no trace cannot be diagnosed the next morning.

`_run` prints the last fifteen lines of a failed command, which is fine while you
are watching. It is not fine when the caller pipes the run through `tail`, when a
flake appears once in a hundred runs, or when the failure happened three hours ago:
the evidence is gone and the only honest answer is "I cannot reproduce it".

These tests drive the real helper out of `scripts/ci.sh` rather than a copy of it,
so a rewrite that drops the log gets caught here.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CI = ROOT / "scripts" / "ci.sh"


def _helper_source() -> str:
    """The `_run` definition, lifted verbatim from the script under test."""
    text = CI.read_text(encoding="utf-8")
    match = re.search(r"^_run\(\).*?^\}", text, re.MULTILINE | re.DOTALL)
    assert match, "could not find _run() in scripts/ci.sh"
    return match.group(0)


def _drive(command: str, log_dir: Path) -> subprocess.CompletedProcess[str]:
    preamble = f"RED=''; GRN=''; YEL=''; DIM=''; BLD=''; RST=''\nFAILED=()\nCI_LOG_DIR={log_dir}\n"
    script = f"{preamble}{_helper_source()}\n{command}\n"
    return subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, check=False, cwd=ROOT
    )


def test_a_failing_gate_leaves_its_whole_output_on_disk(tmp_path: Path) -> None:
    noise = "; ".join(f"echo line{index}" for index in range(1, 41))
    result = _drive(f"_run hard 'noisy gate' bash -c '{noise}; exit 1'", tmp_path)

    assert "FAIL" in result.stdout
    logs = list(tmp_path.glob("*.log"))
    assert logs, f"no failure log written; stdout was:\n{result.stdout}"
    body = logs[0].read_text(encoding="utf-8")
    # The point of the file is the lines the terminal tail would have dropped.
    assert "line1" in body, "the log kept only what was already on screen"
    assert "line40" in body
    assert str(logs[0].name) in result.stdout, "the FAIL line must say where the log is"


def test_a_passing_gate_leaves_nothing_behind(tmp_path: Path) -> None:
    """Without this half, a helper that logs unconditionally would look correct."""
    result = _drive("_run hard 'quiet gate' bash -c 'echo fine'", tmp_path)

    assert "PASS" in result.stdout
    assert not list(tmp_path.glob("*.log"))


def test_real_failure_stops_before_next_scene_mutation(tmp_path: Path) -> None:
    result = _drive(
        "REAL_FAIL_FAST=1\n_run hard 'generation' false\necho NEXT_SCENE_MUTATION", tmp_path
    )
    assert result.returncode != 0
    assert "NEXT_SCENE_MUTATION" not in result.stdout
    assert list(tmp_path.glob("*.log"))


def test_static_failures_still_aggregate(tmp_path: Path) -> None:
    result = _drive("_run hard 'static' false\necho CONTINUED", tmp_path)
    assert "CONTINUED" in result.stdout


def test_real_success_and_warning_do_not_abort(tmp_path: Path) -> None:
    result = _drive(
        "REAL_FAIL_FAST=1\n_run hard 'passing' true\n_run warn 'warning' false\necho CONTINUED",
        tmp_path,
    )
    assert result.returncode == 0
    assert "CONTINUED" in result.stdout


def test_real_tier_enables_fail_fast_before_first_gate() -> None:
    source = CI.read_text(encoding="utf-8")
    real_tier = source.split("if (( REAL )); then", 1)[1]
    assert real_tier.index("REAL_FAIL_FAST=1") < real_tier.index("_run hard")
