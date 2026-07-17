#!/usr/bin/env python3
"""CI gate: every ``isinstance(_, dict)`` must be an honestly-narrowed decision.

The bug class (docs/LESSONS_LEARNED.md, 2026-07-17 / 2026-07-18)
--------------------------------------------------------------
``isinstance(x, dict)`` cannot check type parameters at runtime, so it narrows
only to ``dict[Any, Any]``. Returning or using that as ``dict[str, object]``
type-checks while every value is a silent ``Any`` — and ``mypy --strict`` stays
green because ``Any`` is compatible with everything. The checker is BLIND to it.
The SSOT fix is ``src.infrastructure.narrowing.as_str_keyed`` (and ``dig`` for
staying at ``object``), which rebuilds mappings with explicitly checked keys.

Four instances were cleaned by hand; a fifth (``blender_mcp_adapter``'s second
method) survived a "same file, only fixed the spot a human happened to see" pass.
Manual ``grep`` was the only defence and it was not in CI. This gate is that
defence, made un-silent and un-forgettable.

Why a waiver instead of clever flow analysis
--------------------------------------------
The meta-lesson is that a checker which is *itself* blind to the class will
happily report "clean". Auto-deciding "is this site honestly narrowed?" from the
AST is exactly such a blind heuristic — honesty is only provable with
``reveal_type`` at the value site, which CI cannot do per-call. So this gate does
NOT try to prove honesty. It makes every ``isinstance(_, dict)`` a *declared,
greppable, reviewable* decision — the same discipline the project already
requires of ``# type: ignore``. A site is allowed only when:

  1. it lives in the narrowing SSOT module itself (where the primitives are
     defined), or
  2. it carries an explicit ``# narrow-ok: <reason>`` waiver on the
     ``isinstance`` statement.

The realistic silent-failure mode — a fresh, unannotated hit copied in by a
future edit or a subagent — then fails loudly. AST parsing (not literal grep) is
used so that mentions of ``isinstance`` inside strings/docstrings/comments do not
false-match.

Usage
-----
    scripts/check_dict_narrowing.py [ROOT ...]     # default roots: src api

Exit 0 when every hit is accounted for; exit 1 (with a report) otherwise. Run
from the repo root — ci.sh guarantees that.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from collections.abc import Iterator

# The SSOT module that DEFINES the narrowing primitives. Its own isinstance
# checks are the honest reference implementation, so the gate does not police
# them. Any other file must route through these primitives or waive explicitly.
ALLOWLIST_PATHS = {"src/infrastructure/narrowing.py"}

# A waiver must carry a non-whitespace reason after the colon, so it reads as a
# claim a reviewer can judge — never a bare mute switch.
WAIVER_RE = re.compile(r"#\s*narrow-ok:\s*\S")

DEFAULT_ROOTS = ("src", "api")


def _iter_py_files(roots: tuple[str, ...]) -> Iterator[str]:
    for root in roots:
        if os.path.isfile(root) and root.endswith(".py"):
            yield root
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for name in sorted(filenames):
                if name.endswith(".py"):
                    yield os.path.join(dirpath, name)


def _is_dict_isinstance(node: ast.AST) -> bool:
    """True for ``isinstance(<expr>, dict)`` or ``isinstance(<expr>, (..., dict, ...))``."""
    if not isinstance(node, ast.Call):
        return False
    if not (isinstance(node.func, ast.Name) and node.func.id == "isinstance"):
        return False
    if len(node.args) < 2:
        return False
    type_arg = node.args[1]
    candidates = type_arg.elts if isinstance(type_arg, ast.Tuple) else [type_arg]
    return any(isinstance(c, ast.Name) and c.id == "dict" for c in candidates)


def _rel(path: str) -> str:
    return os.path.relpath(path).replace(os.sep, "/")


def _check_file(path: str) -> list[tuple[str, int, str]]:
    """Return unaccounted-for hits as (relpath, lineno, source-line) tuples."""
    rel = _rel(path)
    with open(path, encoding="utf-8") as fh:
        source = fh.read()
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        # Never silently skip: an unparseable file is a hole, not a pass.
        return [(rel, exc.lineno or 0, f"<syntax error: {exc.msg}>")]

    if rel in ALLOWLIST_PATHS:
        return []

    lines = source.splitlines()
    findings: list[tuple[str, int, str]] = []
    for node in ast.walk(tree):
        if not _is_dict_isinstance(node):
            continue
        start = node.lineno  # type: ignore[attr-defined]  # Call always has lineno
        end = getattr(node, "end_lineno", start) or start
        span = lines[start - 1 : end]  # physical lines the call spans
        if any(WAIVER_RE.search(line) for line in span):
            continue
        findings.append((rel, start, lines[start - 1].strip()))
    return findings


def main(argv: list[str]) -> int:
    roots = tuple(argv[1:]) or DEFAULT_ROOTS
    findings: list[tuple[str, int, str]] = []
    for path in _iter_py_files(roots):
        findings.extend(_check_file(path))
    findings.sort()

    if not findings:
        print("dict-narrowing gate: OK — every isinstance(_, dict) is accounted for")
        return 0

    print("dict-narrowing gate: FAIL — isinstance(_, dict) hit(s) with no honest narrowing")
    print("  This narrows only to dict[Any, Any]; using it as dict[str, object] is a silent")
    print("  Any hole mypy --strict cannot see (docs/LESSONS_LEARNED.md 2026-07-17/18).")
    print("  Fix: route the value through src.infrastructure.narrowing (as_str_keyed / dig),")
    print("  or, if the site rebuilds keys honestly, annotate it: `# narrow-ok: <reason>`.")
    print()
    for rel, lineno, text in findings:
        print(f"  {rel}:{lineno}: {text}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
