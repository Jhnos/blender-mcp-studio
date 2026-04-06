"""Unit tests for Scene aggregate root."""

from src.core.domain.scene import Scene, SceneObject


def test_scene_starts_empty() -> None:
    scene = Scene()
    assert scene.objects == []


def test_scene_with_object_returns_new_scene() -> None:
    scene = Scene()
    obj = SceneObject(name="Cube", object_type="MESH")
    updated = scene.with_object(obj)
    assert len(updated.objects) == 1
    assert updated.objects[0].name == "Cube"
    assert scene.objects == []  # original unchanged


def test_scene_without_object_removes_by_name() -> None:
    obj = SceneObject(name="Cube", object_type="MESH")
    scene = Scene(objects=[obj])
    updated = scene.without_object("Cube")
    assert updated.objects == []


def test_scene_object_names() -> None:
    objs = [
        SceneObject(name="Cube", object_type="MESH"),
        SceneObject(name="Light", object_type="LIGHT"),
    ]
    scene = Scene(objects=objs)
    assert set(scene.object_names()) == {"Cube", "Light"}


def test_scene_object_is_immutable() -> None:
    import pytest

    obj = SceneObject(name="Cube", object_type="MESH")
    with pytest.raises(Exception):
        obj.name = "Sphere"  # type: ignore[misc]
