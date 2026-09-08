"""Decoding Blender's dialect is the adapter's job, and this is where it now lives.

DEFERRALS D-001 recorded the root cause: `BlenderPort` returned `object`, so
the use case had to narrow the addon's replies itself, duplicating the
predicates the adapters already had. The port now returns typed DTOs and the
adapter decodes. These tests carry over every message the use-case tests used
to pin, because REST clients read them verbatim as 422 details.
"""

from __future__ import annotations

import pytest

from src.adapters.blender_scene_decoding import (
    decode_object_details,
    decode_scene_summary,
    decode_screenshot_size,
)
from src.core.domain.exceptions import SceneOperationError
from src.core.domain.scene_operations import Vector3

SCENE: dict[str, object] = {
    "name": "Scene",
    "object_count": 1,
    "materials_count": 1,
    "objects": [{"name": "Cube", "type": "MESH", "location": [0.0, 0.0, 0.0]}],
}
OBJECT: dict[str, object] = {
    "name": "Cube",
    "type": "MESH",
    "location": [0.0, 0.0, 0.0],
    "rotation": [0.0, 0.0, 0.0],
    "scale": [1.0, 1.0, 1.0],
    "visible": True,
    "materials": ["Red"],
}


def test_scene_summary_is_decoded_to_domain_values() -> None:
    scene = decode_scene_summary(SCENE)

    assert scene.name == "Scene"
    assert scene.object_count == 1
    assert scene.objects[0].name == "Cube"
    assert scene.objects[0].location == Vector3()


def test_a_missing_scene_field_fails_explicitly() -> None:
    with pytest.raises(SceneOperationError, match="missing: objects"):
        decode_scene_summary({key: value for key, value in SCENE.items() if key != "objects"})


def test_a_non_object_scene_reply_is_an_error_not_an_empty_scene() -> None:
    """The adapter used to warn and return {}; a silent empty scene is the worse lie."""
    with pytest.raises(SceneOperationError, match="scene info; expected an object"):
        decode_scene_summary(["not", "a", "scene"])


def test_an_invalid_vector_fails_explicitly() -> None:
    broken = dict(SCENE, objects=[{"name": "Cube", "type": "MESH", "location": [0.0, 1.0]}])

    with pytest.raises(SceneOperationError, match="expected three finite numbers"):
        decode_scene_summary(broken)


def test_object_details_are_decoded_to_domain_values() -> None:
    details = decode_object_details(OBJECT)

    assert details.name == "Cube"
    assert details.materials == ("Red",)
    assert details.scale == Vector3(1.0, 1.0, 1.0)


@pytest.mark.parametrize(
    ("field", "bad_value", "message"),
    [
        ("visible", "true", "visible; expected a boolean"),
        ("materials", ["Red", 7], "materials; expected a list of strings"),
        ("name", 7, "object name; expected a string"),
        ("location", [0.0, "x", 0.0], "expected three finite numbers"),
    ],
)
def test_object_details_reject_coerced_values(field: str, bad_value: object, message: str) -> None:
    with pytest.raises(SceneOperationError, match=message):
        decode_object_details(dict(OBJECT, **{field: bad_value}))


def test_screenshot_size_needs_both_dimensions_as_integers() -> None:
    assert decode_screenshot_size({"width": 640, "height": 480}) == (640, 480)
    with pytest.raises(SceneOperationError, match="missing: height"):
        decode_screenshot_size({"width": 640})
    with pytest.raises(SceneOperationError, match="screenshot width; expected an integer"):
        decode_screenshot_size({"width": "640", "height": 480})
