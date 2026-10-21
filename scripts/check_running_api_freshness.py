#!/usr/bin/env python3
"""Real-machine gate: the running API must be newer than every source it serves.

The API derives the registered verification scripts from the files on disk at
call time, but its sandbox allowlist and per-script deadlines are snapshots taken
at startup. Edit a module in that import graph while the API keeps running and the
API blocks its own script with "Security: blocked code" (observed 2026-10-21 12:34,
38 minutes into a real-tier run). Generators and deadlines drift the same way.

Usage: ``python scripts/check_running_api_freshness.py [--port 19505]``
Exit 1 lists every source newer than the API process and names the fix:
``bash deploy/launchd/install.sh api``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
#: Trees the API imports from or reads at startup; `tmp`, caches and archives are not source.
SOURCE_TREES = ("api", "src", "scripts", "config")
SOURCE_SUFFIXES = (".py", ".yaml", ".yml", ".toml")
EXCLUDED_PARTS = ("__pycache__", "archive", "tmp", "node_modules")


def newer_than(root: Path, started_at: float) -> list[tuple[str, float]]:
    """Sources modified after `started_at` (epoch seconds), newest first, repo-relative."""
    rows: list[tuple[str, float]] = []
    candidates = [root / tree for tree in SOURCE_TREES] + [root / "pyproject.toml"]
    for base in candidates:
        files = [base] if base.is_file() else sorted(base.rglob("*")) if base.is_dir() else []
        for path in files:
            if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
                continue
            if any(part in EXCLUDED_PARTS for part in path.relative_to(root).parts):
                continue
            modified = path.stat().st_mtime
            if modified > started_at:
                rows.append((path.relative_to(root).as_posix(), modified))
    return sorted(rows, key=lambda row: -row[1])


def listening_pid(port: int) -> int | None:
    result = subprocess.run(
        ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
        capture_output=True,
        text=True,
        check=False,
    )
    pids = [int(line) for line in result.stdout.split() if line.strip().isdigit()]
    return min(pids) if pids else None


def process_started_at(pid: int) -> float:
    result = subprocess.run(
        ["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True, check=True
    )
    # ps prints e.g. "Wed Oct 21 12:36:50 2026" in the local zone.
    return dt.datetime.strptime(result.stdout.strip(), "%a %b %d %H:%M:%S %Y").timestamp()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=19505)
    args = parser.parse_args(argv)

    pid = listening_pid(args.port)
    if pid is None:
        print(f"api-freshness gate: FAIL — nothing is listening on {args.port}")
        return 1
    started = process_started_at(pid)
    stale = newer_than(PROJECT_ROOT, started)
    if stale:
        print("api-freshness gate: FAIL — the running API is older than this checkout")
        print(f"  pid {pid} started {dt.datetime.fromtimestamp(started):%Y-%m-%d %H:%M:%S}")
        print("  Its sandbox allowlist and script deadlines are startup snapshots; restart it:")
        print("    bash deploy/launchd/install.sh api")
        for path, modified in stale[:20]:
            print(f"  {path}  modified {dt.datetime.fromtimestamp(modified):%H:%M:%S}")
        return 1
    print(f"api-freshness gate: OK — pid {pid} started after every source in {PROJECT_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
