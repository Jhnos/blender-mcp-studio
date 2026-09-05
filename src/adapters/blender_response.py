"""Shared strict narrowing for Blender execute-code responses.

Thin Blender-specific wording over the predicates in
``src/infrastructure/narrowing.py``. The shapes are checked there; only the
messages — which reach REST clients verbatim as a 422 ``detail`` — live here.
"""

from __future__ import annotations

from collections.abc import Sequence

from src.infrastructure.narrowing import (
    ErrorFactory,
    as_int,
    as_mapping,
    as_sequence,
    as_str,
    as_str_keyed_exact,
    required,
)

__all__ = [
    "ErrorFactory",
    "execute_code_output",
    "integer",
    "mapping",
    "sequence",
    "text",
]


def mapping(value: object, context: str, error: ErrorFactory) -> dict[str, object]:
    """Narrow a Blender payload to a string-keyed object.

    "Not an object" and "object with a non-string key" are reported separately,
    because they point at different bugs on the addon side.
    """
    required(
        value,
        as_mapping,
        message=f"Blender returned invalid {context}; expected an object",
        error=error,
    )
    return required(
        value,
        as_str_keyed_exact,
        message=f"Blender returned invalid {context}; keys must be strings",
        error=error,
    )


def sequence(value: object, context: str, error: ErrorFactory) -> Sequence[object]:
    return required(
        value,
        as_sequence,
        message=f"Blender returned invalid {context}; expected a list",
        error=error,
    )


def text(value: object, context: str, error: ErrorFactory) -> str:
    return required(
        value,
        as_str,
        message=f"Blender returned invalid {context}; expected text",
        error=error,
    )


def integer(value: object, context: str, error: ErrorFactory) -> int:
    """Narrow a Blender payload field to an int, rejecting bool.

    Previously copied verbatim into two adapters, differing only in the
    exception class — which is exactly what ``error`` now carries.
    """
    return required(
        value,
        as_int,
        message=f"Blender returned invalid {context}; expected an integer",
        error=error,
    )


def execute_code_output(value: object, error: ErrorFactory) -> str:
    direct = as_str(value)
    if direct is not None:
        return direct
    envelope = mapping(value, "execute-code result", error)
    return text(envelope.get("result"), "execute-code output", error)
