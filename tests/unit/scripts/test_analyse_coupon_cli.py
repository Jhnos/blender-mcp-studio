"""The documented coupon command judges from the repository root and exits by verdict."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FULL_PASS = [
    "--c1", "4.52", "4.48", "--c2", "yes", "--c3", "8.05", "8.12",
    "--c4", "yes", "--c5", "yes", "--c6", "yes", "--c7", "yes",
]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/analyse_coupon.py", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_a_fully_passing_coupon_exits_zero_with_rows_to_paste() -> None:
    result = _run(*FULL_PASS, "--date", "2026-09-10")

    assert result.returncode == 0, result.stderr
    assert "COUPON PASS" in result.stdout
    assert result.stdout.count("| 2026-09-10 | C1 |") == 2


def test_an_undersized_bore_exits_one_and_says_which_way() -> None:
    args = list(FULL_PASS)
    args[1] = "4.30"

    result = _run(*args)

    assert result.returncode == 1
    assert "偏小" in result.stdout and "COUPON NOT PASSED" in result.stdout


def test_an_unfinished_coupon_is_not_a_pass() -> None:
    result = _run("--c1", "4.52", "4.48")

    assert result.returncode == 1
    assert "VACUOUS" in result.stdout
