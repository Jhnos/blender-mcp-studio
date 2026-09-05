"""Fail-closed guards for the docs/ DCC tree.

Three rules the tree must keep, each enforced here rather than by convention:

1. **No broken links** — every ``[[wikilink]]`` resolves to a file that exists.
2. **No orphans** — every topic file is reachable from ``docs/README.md`` within
   two hops, so a takeover never has to guess which file to open.
3. **Fact uniqueness** — ports live only in ``10-runtime-ssot.md``. A fact
   written in two places drifts; this is the machine that stops it.

Every check below ships with a should-fire *and* a should-pass fixture. The
should-pass half is the one that catches a guard which has degenerated into
"always fails" — a mis-measuring guard is worse than no guard, because it hands
out false assurance.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
DOCS = PROJECT_ROOT / "docs"

NAV_ROOT = "README"
MAX_HOPS = 2

#: Ports whose single source of truth is ``docs/10-runtime-ssot.md``.
PORT_TOKENS = ("19505", "19504", "9876")
PORT_SSOT = "10-runtime-ssot.md"

#: Trees excluded from the live rules. ``archive/`` is frozen history and must
#: keep its original wording; ``verification/`` rubrics cite real fixture ports.
EXCLUDED_DIRS = ("archive", "verification")

#: Append-only files. The 5S hard line forbids rewriting recorded history, so a
#: port quoted inside a past lesson stays as written; correct the present docs
#: instead. Excluded from the fact-uniqueness rule only — links still apply.
FROZEN_FILES = ("LESSONS_LEARNED.md",)

WIKILINK = re.compile(r"\[\[([^\]|]+)")
#: Relative markdown links, e.g. ``[label](02_task.md)``. Skips absolute URLs.
MD_LINK = re.compile(r"\[[^\]]*\]\((?!https?://|#)([^)#]+)")
FENCED = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")


def _live_docs(root: Path) -> list[Path]:
    """Markdown files under ``root`` that the live rules apply to."""
    return sorted(
        path
        for path in root.rglob("*.md")
        if not any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts)
    )


def _strip_code(text: str) -> str:
    """Drop code blocks and inline code.

    Prose that *documents* the link syntax — ``[[name]]`` inside backticks — is
    not a link. Without this the guard reports the documentation of its own rule
    as a broken link, which is a false positive, not a finding.
    """
    return INLINE_CODE.sub("", FENCED.sub("", text))


def _wikilink_targets(text: str) -> list[str]:
    return [match.group(1).strip() for match in WIKILINK.finditer(_strip_code(text))]


def _outbound_targets(root: Path, path: Path) -> list[str]:
    """Every navigable target of ``path``: wikilinks plus relative md links.

    Reachability is about whether a reader can get there, so both link syntaxes
    count. Markdown link targets are resolved relative to the linking file.
    """
    text = _strip_code(path.read_text(encoding="utf-8"))
    targets = [match.group(1).strip() for match in WIKILINK.finditer(text)]
    for match in MD_LINK.finditer(text):
        resolved = (path.parent / match.group(1).strip()).resolve()
        try:
            targets.append(str(resolved.relative_to(root.resolve())))
        except ValueError:
            continue  # points outside docs/; not part of this tree's navigation
    return targets


def _resolve(root: Path, target: str) -> Path | None:
    """Resolve a wikilink target to a real file, or ``None`` when it is broken."""
    for candidate in (root / f"{target}.md", root / target, root / f"{target}/README.md"):
        if candidate.is_file():
            return candidate
    return None


def find_broken_links(root: Path) -> list[str]:
    """Return ``file -> target`` strings for every unresolvable wikilink."""
    broken: list[str] = []
    for path in _live_docs(root):
        for target in _wikilink_targets(path.read_text(encoding="utf-8")):
            if _resolve(root, target) is None:
                broken.append(f"{path.relative_to(root)} -> [[{target}]]")
    return broken


def find_orphans(root: Path) -> list[str]:
    """Return live docs not reachable from the navigation root within MAX_HOPS."""
    start = root / f"{NAV_ROOT}.md"
    if not start.is_file():
        return [f"missing navigation root: {NAV_ROOT}.md"]

    reached = {start.resolve()}
    frontier = [start]
    for _ in range(MAX_HOPS):
        nxt: list[Path] = []
        for path in frontier:
            for target in _outbound_targets(root, path):
                found = _resolve(root, target)
                if found is not None and found.resolve() not in reached:
                    reached.add(found.resolve())
                    nxt.append(found)
        frontier = nxt

    return sorted(
        str(path.relative_to(root)) for path in _live_docs(root) if path.resolve() not in reached
    )


def find_duplicated_ports(root: Path) -> list[str]:
    """Return ``file:line`` strings where a port appears outside its SSOT."""
    offenders: list[str] = []
    for path in _live_docs(root):
        if path.name == PORT_SSOT or path.name in FROZEN_FILES:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for token in PORT_TOKENS:
                if token in line:
                    offenders.append(f"{path.relative_to(root)}:{lineno} ({token})")
    return offenders


# --------------------------------------------------------------------------
# Live rules
# --------------------------------------------------------------------------


def test_no_broken_wikilinks() -> None:
    broken = find_broken_links(DOCS)
    assert not broken, "wikilinks pointing at missing files:\n" + "\n".join(broken)


def test_no_orphan_docs() -> None:
    orphans = find_orphans(DOCS)
    assert not orphans, (
        "docs unreachable from README within "
        f"{MAX_HOPS} hops (add them to the navigation table):\n" + "\n".join(orphans)
    )


def test_ports_only_in_runtime_ssot() -> None:
    offenders = find_duplicated_ports(DOCS)
    assert not offenders, (
        f"ports belong only in docs/{PORT_SSOT}; link to it instead of "
        "restating them:\n" + "\n".join(offenders)
    )


# --------------------------------------------------------------------------
# Guard self-tests: each rule must fire on a defect AND stay silent on a
# clean tree. Without the should-pass half, an always-failing guard looks
# exactly like a working one.
# --------------------------------------------------------------------------


def _clean_tree(root: Path) -> None:
    (root / "README.md").write_text(
        "# nav\n\n| File | When |\n|---|---|\n| [[10-runtime-ssot]] | ports |\n| [[01-topic]] | x |\n",
        encoding="utf-8",
    )
    (root / "10-runtime-ssot.md").write_text(
        "# ports\n\nAPI 19505, web 19504, addon 9876.\n", encoding="utf-8"
    )
    (root / "01-topic.md").write_text(
        "# topic\n\nSee [[10-runtime-ssot]] for ports.\n", encoding="utf-8"
    )


def test_broken_link_guard_fires(tmp_path: Path) -> None:
    _clean_tree(tmp_path)
    (tmp_path / "01-topic.md").write_text(
        "# topic\n\nSee [[99-does-not-exist]].\n", encoding="utf-8"
    )
    assert find_broken_links(tmp_path)


def test_broken_link_guard_passes_clean_tree(tmp_path: Path) -> None:
    _clean_tree(tmp_path)
    assert find_broken_links(tmp_path) == []


def test_orphan_guard_fires(tmp_path: Path) -> None:
    _clean_tree(tmp_path)
    (tmp_path / "80-unlinked.md").write_text("# nobody links here\n", encoding="utf-8")
    assert find_orphans(tmp_path) == ["80-unlinked.md"]


def test_orphan_guard_passes_clean_tree(tmp_path: Path) -> None:
    _clean_tree(tmp_path)
    assert find_orphans(tmp_path) == []


def test_orphan_guard_accepts_second_hop(tmp_path: Path) -> None:
    """Reachable via 01-topic, not directly from README — still not an orphan."""
    _clean_tree(tmp_path)
    (tmp_path / "01-topic.md").write_text(
        "# topic\n\n[[10-runtime-ssot]] and [[70-deep]].\n", encoding="utf-8"
    )
    (tmp_path / "70-deep.md").write_text("# deep\n", encoding="utf-8")
    assert find_orphans(tmp_path) == []


def test_port_guard_fires(tmp_path: Path) -> None:
    _clean_tree(tmp_path)
    (tmp_path / "01-topic.md").write_text(
        "# topic\n\nThe API listens on 19505.\n", encoding="utf-8"
    )
    assert find_duplicated_ports(tmp_path)


def test_port_guard_passes_clean_tree(tmp_path: Path) -> None:
    """Ports inside the SSOT file itself must NOT be reported."""
    _clean_tree(tmp_path)
    assert find_duplicated_ports(tmp_path) == []


def test_port_guard_ignores_archive(tmp_path: Path) -> None:
    """Frozen history keeps its original wording and is never rewritten."""
    _clean_tree(tmp_path)
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "old.md").write_text(
        "# old\n\nPort 19505 as it was written then.\n", encoding="utf-8"
    )
    assert find_duplicated_ports(tmp_path) == []


def test_port_guard_ignores_append_only_lessons(tmp_path: Path) -> None:
    """A port quoted inside a recorded lesson is history, not a live restatement."""
    _clean_tree(tmp_path)
    (tmp_path / "LESSONS_LEARNED.md").write_text(
        "# lessons\n\nCORS Origin=19504 was blocked under both configs.\n", encoding="utf-8"
    )
    assert find_duplicated_ports(tmp_path) == []


def test_link_guard_ignores_syntax_documentation(tmp_path: Path) -> None:
    """Prose documenting the link syntax in backticks is not a link."""
    _clean_tree(tmp_path)
    (tmp_path / "01-topic.md").write_text(
        "# topic\n\nCross-link with `[[name]]`, e.g. [[10-runtime-ssot]].\n", encoding="utf-8"
    )
    assert find_broken_links(tmp_path) == []


def test_link_guard_ignores_fenced_blocks(tmp_path: Path) -> None:
    _clean_tree(tmp_path)
    (tmp_path / "01-topic.md").write_text(
        "# topic\n\n```text\n[[not-a-real-file]]\n```\n\nSee [[10-runtime-ssot]].\n",
        encoding="utf-8",
    )
    assert find_broken_links(tmp_path) == []


def test_orphan_guard_follows_markdown_links(tmp_path: Path) -> None:
    """Reachability counts markdown links too, not only wikilinks."""
    _clean_tree(tmp_path)
    (tmp_path / "01-topic.md").write_text(
        "# topic\n\n[[10-runtime-ssot]] and [a task](60-linked.md).\n", encoding="utf-8"
    )
    (tmp_path / "60-linked.md").write_text("# linked by markdown only\n", encoding="utf-8")
    assert find_orphans(tmp_path) == []


def test_orphan_guard_still_fires_with_markdown_links_enabled(tmp_path: Path) -> None:
    """Broadening reachability must not turn the guard into a no-op."""
    _clean_tree(tmp_path)
    (tmp_path / "61-nobody.md").write_text("# genuinely unreachable\n", encoding="utf-8")
    assert find_orphans(tmp_path) == ["61-nobody.md"]
