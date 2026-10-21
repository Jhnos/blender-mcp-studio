"""The running API must be at least as new as the checkout it is verified against.

Observed 2026-10-21 12:34: the API process had been restarted at 11:46; a source
edit at 11:58 changed the import graph of the registered verification scripts.
The API derives each suite's Blender script at call time from the files on disk,
but its sandbox allowlist and per-script deadlines are snapshots taken at
startup, so the API blocked its own script ("Security: blocked code (importlib)")
and the seventh real-tier run stopped after 38 minutes. The class is "a resident
process verified against files newer than itself"; the precondition belongs at
the top of the real tier next to the LaunchAgent drift gate.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

PROJECT_ROOT = Path(__file__).parents[3]
SCRIPT = PROJECT_ROOT / "scripts" / "check_running_api_freshness.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_running_api_freshness", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load()


def _tree(tmp_path: Path) -> Path:
    for relative in ("api/runtime.py", "src/core/a.py", "scripts/verify/b.py", "config/c.yaml"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x = 1\n", encoding="utf-8")
        os.utime(path, (1_000, 1_000))
    return tmp_path


def test_silent_when_the_process_started_after_every_source(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    assert gate.newer_than(root, started_at=2_000) == []


def test_reports_every_source_newer_than_the_process(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    os.utime(root / "scripts/verify/b.py", (3_000, 3_000))
    os.utime(root / "config/c.yaml", (2_500, 2_500))
    rows = gate.newer_than(root, started_at=2_000)
    assert [path for path, _ in rows] == ["scripts/verify/b.py", "config/c.yaml"]


def test_ignores_scratch_and_caches(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    for relative in ("tmp/x.py", "scripts/__pycache__/y.py", "scripts/archive/z.py"):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x = 1\n", encoding="utf-8")
        os.utime(path, (9_000, 9_000))
    assert gate.newer_than(root, started_at=2_000) == []


def test_gate_runs_in_the_real_tier_before_the_api_is_exercised() -> None:
    ci = (PROJECT_ROOT / "scripts" / "ci.sh").read_text(encoding="utf-8")
    assert "check_running_api_freshness.py" in ci, "the gate exists but nothing runs it"
    assert ci.index("check_running_api_freshness.py") < ci.index("mcp_verify_rest.py")
