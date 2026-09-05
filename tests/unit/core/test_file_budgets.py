"""God-file ratchet for the application and adapter trees.

A file past the budget is carrying more than one responsibility. The only legal
fix is splitting that responsibility out — never compressing lines to slip under
the number, and never raising the number because a file grew.

The budget is deliberately a *hard* cap rather than a per-file allowlist: an
allowlist ages into a list of permanent exceptions nobody revisits.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]

#: Trees under the ratchet. ``scripts/`` is excluded for now — its generators
#: are still being consolidated; it joins once that work lands.
BUDGETED_TREES = ("api", "src")

MAX_LINES = 400

#: The headroom warning fires here, so growth is visible while splitting is
#: still cheap rather than on the commit that crosses the hard cap.
WARN_LINES = int(MAX_LINES * 0.95)


def oversized(roots: list[Path], limit: int) -> list[tuple[str, int]]:
    """Return ``(path, line_count)`` for every Python file over ``limit``."""
    rows: list[tuple[str, int]] = []
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            count = len(path.read_text(encoding="utf-8").splitlines())
            if count > limit:
                rows.append((str(path), count))
    return sorted(rows, key=lambda row: -row[1])


def _budgeted_roots() -> list[Path]:
    return [PROJECT_ROOT / tree for tree in BUDGETED_TREES]


def test_no_file_exceeds_the_budget() -> None:
    rows = oversized(_budgeted_roots(), MAX_LINES)
    assert not rows, (
        f"files over {MAX_LINES} lines carry more than one responsibility;\n"
        "split the responsibility — do not raise this number:\n"
        + "\n".join(f"  {path}: {count}" for path, count in rows)
    )


def test_no_file_is_within_five_percent_of_the_budget() -> None:
    rows = oversized(_budgeted_roots(), WARN_LINES)
    assert not rows, (
        f"files within 5% of the {MAX_LINES}-line budget — split them now, while\n"
        "the seams are still obvious:\n" + "\n".join(f"  {p}: {c}" for p, c in rows)
    )


# --------------------------------------------------------------------------
# Guard self-tests
# --------------------------------------------------------------------------


def test_ratchet_fires_on_an_oversized_file(tmp_path: Path) -> None:
    (tmp_path / "big.py").write_text("x = 1\n" * 12, encoding="utf-8")
    rows = oversized([tmp_path], limit=10)
    assert rows == [(str(tmp_path / "big.py"), 12)]


def test_ratchet_passes_a_file_at_the_limit(tmp_path: Path) -> None:
    """Exactly at the budget is compliant; only *over* it fails."""
    (tmp_path / "exact.py").write_text("x = 1\n" * 10, encoding="utf-8")
    assert oversized([tmp_path], limit=10) == []


def test_ratchet_skips_bytecode_caches(tmp_path: Path) -> None:
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "big.py").write_text("x = 1\n" * 99, encoding="utf-8")
    assert oversized([tmp_path], limit=10) == []
