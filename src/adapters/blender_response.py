"""Shared strict narrowing for Blender execute-code responses."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

ErrorFactory = Callable[[str], Exception]


def mapping(
    value: object,
    context: str,
    error: ErrorFactory,
) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise error(f"Blender returned invalid {context}; expected an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise error(f"Blender returned invalid {context}; keys must be strings")
        result[key] = item
    return result


def sequence(value: object, context: str, error: ErrorFactory) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise error(f"Blender returned invalid {context}; expected a list")
    return value


def text(value: object, context: str, error: ErrorFactory) -> str:
    if not isinstance(value, str):
        raise error(f"Blender returned invalid {context}; expected text")
    return value


def execute_code_output(value: object, error: ErrorFactory) -> str:
    if isinstance(value, str):
        return value
    envelope = mapping(value, "execute-code result", error)
    return text(envelope.get("result"), "execute-code output", error)
