"""No tailnet FQDN or home path may be committed in code, scripts, config or deploy sources.

The service must be movable to other hardware: the public base URL is resolved at run
or install time (``src/infrastructure/public_base_url.py``). ``docs/`` and ``tests/`` are
documentation and fixtures and are not scanned; neither is retired ``scripts/archive/``
or the vendored ``config/slicer-profiles/``.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCAN_DIRS = ("api", "src", "scripts", "config", "deploy")
SKIP_PARTS = ("scripts/archive/", "config/slicer-profiles/")
SELF = Path(__file__).resolve()

PATTERNS = (
    re.compile(r"[A-Za-z0-9-]+\.tail[0-9a-f]+\.ts\.net"),
    re.compile(r"/Users/[a-z][A-Za-z0-9._-]*/"),
    re.compile(r"/home/[a-z][A-Za-z0-9._-]*/"),
)

#: file:line -> reason. Empty on purpose; reword instead of allowing.
ALLOWLIST: dict[str, str] = {}


def find_hits(text: str) -> list[str]:
    return [m.group(0) for p in PATTERNS for m in p.finditer(text)]


def test_guard_fires_on_hosts_and_home_paths() -> None:
    assert find_hits("https://box-1.tail1a2b3c.ts.net/blender")
    assert find_hits("PATH=/Users/someone/miniconda3/bin")
    assert find_hits("cd /home/ubuntu/app")


def test_guard_passes_on_placeholders_and_neutral_text() -> None:
    assert not find_hits("https://<your-tailnet-host>/blender")
    assert not find_hits("__HOME__/miniconda3 and ~/data and /Users")
    assert not find_hits("the tailnet host, e.g. example.ts.net")


def test_no_hardcoded_hosts_or_home_paths() -> None:
    offenders: list[str] = []
    for name in SCAN_DIRS:
        for path in sorted((ROOT / name).rglob("*")):
            rel = path.relative_to(ROOT).as_posix()
            if not path.is_file() or path.resolve() == SELF:
                continue
            if any(part in rel + "/" for part in SKIP_PARTS) or "__pycache__" in rel:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                continue  # binary
            for number, line in enumerate(lines, 1):
                for hit in find_hits(line):
                    key = f"{rel}:{number}"
                    if key not in ALLOWLIST:
                        offenders.append(f"{key}: {hit}")
    assert not offenders, "hardcoded host/home path:\n" + "\n".join(offenders)
