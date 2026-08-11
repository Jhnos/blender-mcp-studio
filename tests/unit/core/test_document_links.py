"""Keep local Markdown navigation valid when knowledge is archived or moved."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

PROJECT_ROOT = Path(__file__).parents[3]
DOCS_ROOT = PROJECT_ROOT / "docs"
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def _local_target(raw_target: str) -> str | None:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    elif " " in target:
        target = target.split(" ", 1)[0]

    parsed = urlparse(target)
    if parsed.scheme or target.startswith("#"):
        return None
    path = unquote(parsed.path)
    return path or None


def test_every_local_markdown_link_resolves() -> None:
    broken: list[str] = []

    for document in sorted(DOCS_ROOT.rglob("*.md")):
        for raw_target in MARKDOWN_LINK.findall(document.read_text()):
            target = _local_target(raw_target)
            if target is None:
                continue
            resolved = (document.parent / target).resolve()
            if not resolved.exists():
                broken.append(f"{document.relative_to(PROJECT_ROOT)} -> {target}")

    assert not broken, "broken local Markdown links:\n" + "\n".join(broken)
