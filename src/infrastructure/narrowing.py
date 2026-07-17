"""Narrowing helpers for untrusted, externally-decoded data (JSON, YAML, SDKs).

An anti-corruption boundary: outside data arrives as `object` and these turn it
into types the rest of the code can trust.

Why this module exists at all — `isinstance(x, dict)` cannot check type
parameters at runtime, so it narrows only to `dict[Any, Any]`. Every lookup
after that is `Any`, and mypy silently stops checking while still reporting
success:

    section = files_data.get("hdri", {})   # files_data: dict[str, object]
    if isinstance(section, dict):
        section.get("4k").get("exr")       # ← Any. Unchecked. mypy says nothing.

So narrowing has to re-establish honest types rather than merely assert a shape.
Two rules follow, and both are load-bearing:

  * Every hop is annotated back to `object`, which forces the next check.
  * Mappings are rebuilt with explicitly checked keys — returning a narrowed
    `dict[Any, Any]` as `dict[str, object]` type-checks while the keys were
    never actually looked at.

See docs/LESSONS_LEARNED.md, 2026-07-17.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def as_str_keyed(value: object, *, context: str) -> dict[str, object] | None:
    """Narrow to a genuine `dict[str, object]`, or None when it isn't a mapping.

    Non-string keys are dropped with a warning: unreachable for JSON (whose keys
    are always strings) but real for YAML, where `yes:` parses to `True`.
    `context` names the source in that warning.
    """
    if not isinstance(value, dict):
        return None
    narrowed: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            logger.warning("%s: ignoring non-string key %r", context, key)
            continue
        narrowed[key] = item
    return narrowed


def as_str(value: object) -> str | None:
    """Narrow to `str`, or None."""
    return value if isinstance(value, str) else None


def as_int(value: object) -> int | None:
    """Narrow to `int`, or None.

    `bool` is rejected on purpose: it subclasses `int`, so `True` would otherwise
    sail through as 1 wherever a count or a size is expected.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def dig(node: object, *keys: str) -> object:
    """Walk nested mappings, returning None if any hop is absent or not a mapping.

    Stays `object` in and out so callers must narrow whatever they end up with.
    """
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node
