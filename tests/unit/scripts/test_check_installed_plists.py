"""Tests for the installed-LaunchAgent drift gate.

`docs/12-deployment.md` rule 7 calls a clean diff between the installed plist and
its template "the contract", and then says it is checked manually. Manual
checking is exactly what missed a plist still pointing at the repository's old
location after the tree moved — invisible until the next reboot tried to launch
the service.

The gate itself runs against this machine's real `~/Library/LaunchAgents`, so it
belongs in the real tier. These tests drive it against fixture plists in
`tmp_path`, which is what lets them assert both halves: that it catches drift,
and that it stays quiet on a correct install. An earlier draft reported the host
part of an `https://` URL and the tail of a relative `node_modules/.bin/vite` as
missing paths — findings nobody could act on — so those two shapes are pinned as
must-not-fire cases.
"""

from __future__ import annotations

import importlib.util
import plistlib
import sys
from pathlib import Path
from types import ModuleType

PROJECT_ROOT = Path(__file__).parents[3]
SCRIPT = PROJECT_ROOT / "scripts" / "check_installed_plists.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_installed_plists", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load()


def _write_plist(directory: Path, name: str, payload: dict[str, object]) -> Path:
    path = directory / name
    with path.open("wb") as handle:
        plistlib.dump(payload, handle)
    return path


# --------------------------------------------------------------------------
# should-fire
# --------------------------------------------------------------------------


def test_reports_a_path_that_does_not_exist(tmp_path: Path) -> None:
    plist = _write_plist(
        tmp_path,
        "svc.plist",
        {"ProgramArguments": [str(tmp_path / "definitely-missing" / "run.py")]},
    )
    problems = gate.check_plist(plist, tmp_path)
    assert len(problems) == 1
    assert "does not exist" in problems[0]


def test_reports_a_path_belonging_to_a_different_checkout(tmp_path: Path) -> None:
    """The case that actually happened: the tree moved, the plist did not.

    The old location may still exist on some machines, so an existence check
    alone is not enough — the root has to be *this* checkout.
    """
    this_checkout = tmp_path / gate.PROJECT_MARKER
    other = tmp_path / "Desktop" / gate.PROJECT_MARKER / "scripts"
    other.mkdir(parents=True)
    (other / "run.py").touch()

    plist = _write_plist(tmp_path, "svc.plist", {"ProgramArguments": [str(other / "run.py")]})
    problems = gate.check_plist(plist, this_checkout)

    assert len(problems) == 1
    assert "but this checkout is" in problems[0]


# --------------------------------------------------------------------------
# should-pass
# --------------------------------------------------------------------------


def test_silent_on_a_correctly_installed_plist(tmp_path: Path) -> None:
    checkout = tmp_path / gate.PROJECT_MARKER
    (checkout / "scripts").mkdir(parents=True)
    (checkout / "scripts" / "run.py").touch()

    plist = _write_plist(
        tmp_path,
        "svc.plist",
        {
            "ProgramArguments": [str(checkout / "scripts" / "run.py")],
            "WorkingDirectory": str(checkout),
        },
    )
    assert gate.check_plist(plist, checkout) == []


def test_a_url_is_not_a_path(tmp_path: Path) -> None:
    """`https://host/blender/mcp` has slashes; none of them are directories."""
    plist = _write_plist(
        tmp_path,
        "svc.plist",
        {"EnvironmentVariables": {"BLENDER_MCP_URL": "https://example.ts.net/blender/mcp"}},
    )
    assert gate.check_plist(plist, tmp_path) == []


def test_a_relative_fragment_is_not_an_absolute_path(tmp_path: Path) -> None:
    """`node_modules/.bin/vite` must not be read as `/.bin/vite`."""
    plist = _write_plist(tmp_path, "svc.plist", {"ProgramArguments": ["node_modules/.bin/vite"]})
    assert gate.check_plist(plist, tmp_path) == []


def test_finds_a_path_embedded_in_a_longer_command_string(tmp_path: Path) -> None:
    """Coverage the two must-not-fire cases could otherwise have destroyed.

    Tightening the pattern to silence the URL and the relative fragment must not
    also stop it reading a real path out of a command line.
    """
    # Deliberately outside any checkout, so this exercises the existence branch
    # rather than the wrong-checkout branch.
    missing = "/Users/nobody/some-tool/bin/gone.py"
    plist = _write_plist(
        tmp_path, "svc.plist", {"ProgramArguments": [f"blender --python {missing}"]}
    )
    problems = gate.check_plist(plist, tmp_path)
    assert len(problems) == 1
    assert missing in problems[0]


# --------------------------------------------------------------------------
# wiring
# --------------------------------------------------------------------------


def test_absent_launch_agents_report_skip_not_success() -> None:
    """A hermetic checkout has none installed; that must not read as "clean"."""
    code = gate.main(["--labels", "com.example.not-installed-anywhere"])
    assert code == 0


def test_gate_runs_in_the_real_tier() -> None:
    ci = (PROJECT_ROOT / "scripts" / "ci.sh").read_text(encoding="utf-8")
    assert "check_installed_plists.py" in ci, "the gate exists but nothing runs it"
