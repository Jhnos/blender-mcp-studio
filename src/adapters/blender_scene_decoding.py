"""Blender's replies, decoded into the domain's DTOs at the adapter boundary.

DEFERRALS D-001 named the root cause of the duplicated narrowing: the Blender
port returned `object`, so decoding the addon's dialect fell to the use case.
The port now returns typed DTOs and this module is the one place a scene
reply is taken apart. The messages are the ones REST clients already read as
422 details, so they are kept word for word.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from src.adapters.blender_response import integer, mapping, sequence
from src.core.domain.exceptions import SceneOperationError
from src.core.domain.scene_operations import (
    ObjectDetails,
    SceneObjectSummary,
    SceneSummary,
    Vector3,
)
from src.infrastructure.narrowing import as_str, required


def _fields(value: dict[str, object], fields: set[str], context: str) -> None:
    missing = sorted(fields.difference(value))
    if missing:
        raise SceneOperationError(f"Blender {context} is missing: {', '.join(missing)}")


def _text(value: object, field: str) -> str:
    return required(
        value,
        as_str,
        message=f"Blender returned invalid {field}; expected a string",
        error=SceneOperationError,
    )


def _boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise SceneOperationError(f"Blender returned invalid {field}; expected a boolean")
    return value


def _vector(value: object, field: str) -> Vector3:
    items: Sequence[object] = sequence(value, field, SceneOperationError)
    numbers: list[float] = []
    for item in items:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            break
        number = float(item)
        if not math.isfinite(number):
            break
        numbers.append(number)
    if len(numbers) != 3 or len(items) != 3:
        raise SceneOperationError(
            f"Blender returned invalid {field}; expected three finite numbers"
        )
    return Vector3(*numbers)


def _strings(value: object, field: str) -> tuple[str, ...]:
    items = sequence(value, field, SceneOperationError)
    if any(not isinstance(item, str) for item in items):
        raise SceneOperationError(f"Blender returned invalid {field}; expected a list of strings")
    return tuple(item for item in items if isinstance(item, str))


def decode_scene_summary(raw: object) -> SceneSummary:
    data = mapping(raw, "scene info", SceneOperationError)
    _fields(data, {"name", "object_count", "materials_count", "objects"}, "scene info")
    objects: list[SceneObjectSummary] = []
    for item in sequence(data["objects"], "scene objects", SceneOperationError):
        entry = mapping(item, "scene object", SceneOperationError)
        _fields(entry, {"name", "type", "location"}, "scene object")
        objects.append(
            SceneObjectSummary(
                name=_text(entry["name"], "object name"),
                object_type=_text(entry["type"], "object type"),
                location=_vector(entry["location"], "object location"),
            )
        )
    return SceneSummary(
        name=_text(data["name"], "scene name"),
        object_count=integer(data["object_count"], "object count", SceneOperationError),
        materials_count=integer(data["materials_count"], "materials count", SceneOperationError),
        objects=tuple(objects),
    )


def decode_object_details(raw: object) -> ObjectDetails:
    data = mapping(raw, "object info", SceneOperationError)
    _fields(
        data,
        {"name", "type", "location", "rotation", "scale", "visible", "materials"},
        "object info",
    )
    return ObjectDetails(
        name=_text(data["name"], "object name"),
        object_type=_text(data["type"], "object type"),
        location=_vector(data["location"], "location"),
        rotation=_vector(data["rotation"], "rotation"),
        scale=_vector(data["scale"], "scale"),
        visible=_boolean(data["visible"], "visible"),
        materials=_strings(data["materials"], "materials"),
    )


def decode_screenshot_size(raw: object) -> tuple[int, int]:
    data = mapping(raw, "screenshot metadata", SceneOperationError)
    _fields(data, {"width", "height"}, "screenshot metadata")
    return (
        integer(data["width"], "screenshot width", SceneOperationError),
        integer(data["height"], "screenshot height", SceneOperationError),
    )
