#!/usr/bin/env python3
"""Real-machine gate: the installed LaunchAgents must match this checkout.

The installed plists under ``~/Library/LaunchAgents/`` are derived state; the
templates in ``deploy/launchd/`` are the source. ``docs/12-deployment.md`` rule 7
calls a clean diff between them "the contract" — and then says it is checked
manually after every change. Manual checking is what let a plist keep pointing at
a repository path that no longer exists after the tree moved, with nothing
reporting it until the next machine reboot tried to launch the service.

This runs in the real tier on purpose. A hermetic checkout has no installed
LaunchAgents at all; asking the portable tier to inspect them would either fail
everywhere or, worse, "pass" by finding nothing.

Two checks per installed plist:

1. **Every absolute path it names exists.** This is what catches a moved tree.
2. **Every path under a project root points at this checkout.** A plist that
   resolves to *some other* copy of the repository is drift that check 1 misses,
   because that other copy may well exist.

Usage: ``python scripts/check_installed_plists.py [--labels a.b.c ...]``
"""

from __future__ import annotations

import argparse
import plistlib
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"

DEFAULT_LABELS = (
    "com.blender-mcp.api",
    "com.blender-mcp.web",
    "com.blender-mcp.blender",
)

#: A filesystem path embedded inside a longer string (e.g. a command line).
#:
#: Anchored on real filesystem roots rather than a bare leading slash. A looser
#: pattern matched the host part of ``https://bearmacminimac-mini…`` and the
#: ``/.bin/vite`` tail of a relative ``node_modules/.bin/vite`` — two findings
#: nobody could act on, which is how a gate teaches people to ignore it.
EMBEDDED_PATH = re.compile(r"(?:/Users|/opt|/Applications|/Library|/usr|/tmp)(?:/[\w.@+-]+)+")

#: Recognises a path that belongs to *a* checkout of this project.
PROJECT_MARKER = PROJECT_ROOT.name


def _strings(value: object) -> list[str]:
    """Every string reachable in a decoded plist value.

    Deliberately standalone rather than importing the narrowing SSOT: this
    checker is executed as a plain script, where the repository root is not on
    ``sys.path``. Four verifiers broke that way earlier today.
    """
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):  # narrow-ok: each element re-enters this function as object
        return [item for entry in value for item in _strings(entry)]
    if isinstance(value, dict):  # narrow-ok: each value re-enters this function as object
        return [item for entry in value.values() for item in _strings(entry)]
    return []


def candidate_paths(plist: object) -> list[str]:
    """Filesystem paths a plist refers to.

    A whole string that is itself a path counts; so does a path embedded in a
    longer command string. Nothing else does — a URL is not a path even though
    it contains slashes.
    """
    found: list[str] = []
    for text in _strings(plist):
        if text.startswith("/") and "://" not in text:
            found.append(text)
        else:
            found.extend(match.group(0) for match in EMBEDDED_PATH.finditer(text))
    return sorted(set(found))


def check_plist(path: Path, project_root: Path) -> list[str]:
    """Return human-readable problems for one installed plist."""
    problems: list[str] = []
    with path.open("rb") as handle:
        plist = plistlib.load(handle)

    for candidate in candidate_paths(plist):
        target = Path(candidate)
        if PROJECT_MARKER in target.parts:
            index = target.parts.index(PROJECT_MARKER)
            root = Path(*target.parts[: index + 1])
            if root != project_root:
                problems.append(
                    f"{path.name}: points at {root} but this checkout is {project_root}"
                )
                continue
        if not target.exists():
            problems.append(f"{path.name}: {candidate} does not exist")
    return problems


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", nargs="*", default=list(DEFAULT_LABELS))
    args = parser.parse_args(argv)

    installed = [LAUNCH_AGENTS / f"{label}.plist" for label in args.labels]
    present = [path for path in installed if path.is_file()]

    if not present:
        # Explicit, not silent: "nothing installed" and "nothing wrong" are
        # different answers and must not look the same.
        print(f"installed-plist gate: SKIP — no project LaunchAgents under {LAUNCH_AGENTS}")
        return 0

    seen: list[str] = []
    for path in present:
        for problem in check_plist(path, PROJECT_ROOT):
            if problem not in seen:
                seen.append(problem)
    problems = seen

    if problems:
        print("installed-plist gate: FAIL — installed LaunchAgents have drifted")
        print("  The installed copy is derived state; re-render it from the template:")
        print("    bash deploy/launchd/install.sh <service>")
        print("  (installing 'blender' restarts Blender — save your scene first)")
        for problem in problems:
            print(f"  {problem}")
        return 1

    checked = ", ".join(path.stem for path in present)
    print(f"installed-plist gate: OK — {checked} all resolve to {PROJECT_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
