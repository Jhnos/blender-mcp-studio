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

**Two layers, on purpose.** The predicates below answer "is it this shape?" and
return `None` when it is not. `required()` turns any predicate into a raising
one — but the exception type and the whole message come from the caller. Four
copies of these checks used to exist, each raising a different exception with
differently-worded text that reaches REST clients as a 422 `detail`. Folding the
message construction in here would quietly rewrite a published string, so the
predicate is shared and the wording stays where it is read.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Mapping, Sequence
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

#: Builds the exception a failed `required()` should raise. Injected by the
#: caller so each layer keeps its own error type and message.
ErrorFactory = Callable[[str], Exception]


def required(
    value: object,
    narrow: Callable[[object], T | None],
    *,
    message: str,
    error: ErrorFactory,
) -> T:
    """Narrow `value` with `narrow`, or raise `error(message)`.

    The predicate decides the shape; the caller decides the failure. Note the
    consequence for predicates whose success value can be falsy: they must not
    return a falsy sentinel for "no match" — `None` is the only miss.
    """
    narrowed = narrow(value)
    if narrowed is None:
        raise error(message)
    return narrowed


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


def as_mapping(value: object) -> Mapping[str, object] | None:
    """Narrow to a mapping without inspecting its keys.

    Separate from `as_str_keyed_exact` so a caller can tell "not an object" from
    "object with a non-string key" and report each differently.
    """
    if not isinstance(value, Mapping):
        return None
    return value


def as_str_keyed_exact(value: object) -> dict[str, object] | None:
    """Narrow to `dict[str, object]`, rejecting — not dropping — non-string keys.

    The strict counterpart of `as_str_keyed`, for boundaries where a surprising
    key means the payload is wrong rather than merely untidy.
    """
    if not isinstance(value, Mapping):
        return None
    narrowed: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            return None
        narrowed[key] = item
    return narrowed


def as_str(value: object) -> str | None:
    """Narrow to `str`, or None."""
    return value if isinstance(value, str) else None


def as_nonempty_str(value: object) -> str | None:
    """Narrow to a `str` with non-whitespace content, or None."""
    if not isinstance(value, str) or not value.strip():
        return None
    return value


def as_int(value: object) -> int | None:
    """Narrow to `int`, or None.

    `bool` is rejected on purpose: it subclasses `int`, so `True` would otherwise
    sail through as 1 wherever a count or a size is expected.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def as_positive_int(value: object) -> int | None:
    """Narrow to an `int` greater than zero, or None."""
    narrowed = as_int(value)
    if narrowed is None or narrowed <= 0:
        return None
    return narrowed


def as_finite_number(value: object) -> float | None:
    """Narrow to a finite `float`, or None. Rejects `bool`, NaN and infinities."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def as_sequence(value: object) -> Sequence[object] | None:
    """Narrow to a sequence that is not text, or None.

    `str` and `bytes` are sequences, and letting them through turns "a list of
    names" into "a list of characters" without any error.
    """
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return None
    return value


def as_nonempty_sequence(value: object) -> Sequence[object] | None:
    """Narrow to a non-empty, non-text sequence, or None."""
    narrowed = as_sequence(value)
    if narrowed is None or not narrowed:
        return None
    return narrowed


def dig(node: object, *keys: str) -> object:
    """Walk nested mappings, returning None if any hop is absent or not a mapping.

    Stays `object` in and out so callers must narrow whatever they end up with.
    """
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node
