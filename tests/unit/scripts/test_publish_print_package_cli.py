"""The documented publisher command must work from the repository root."""

import subprocess
import sys
from pathlib import Path


def test_publisher_cli_bootstraps_project_imports() -> None:
    root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [sys.executable, "scripts/publish_print_package.py", "--help"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "verified manufacturing files" in result.stdout
    # The publisher serves more than one model now, so the choice has to be visible.
    assert "--package" in result.stdout
    for slug in ("biaxial-hinge-v6", "octopus-hand-v1"):
        assert slug in result.stdout
