"""Contracts for the client-neutral scene operation vocabulary and ports."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest


def test_object_type_values_are_exact() -> None:
    from src.core.domain.scene_operations import ObjectType

    assert {item.value for item in ObjectType} == {"MESH", "CURVE", "LIGHT", "CAMERA"}


def test_scene_operation_values_are_immutable() -> None:
    from src.core.domain.scene_operations import (
        BlenderStatus,
        ColorRGBA,
        CreateObjectSpec,
        MaterialSpec,
        ModifyObjectSpec,
        ObjectDetails,
        ObjectType,
        OperationReceipt,
        SceneObjectSummary,
        SceneSummary,
        Vector3,
        ViewportImage,
    )

    origin = Vector3()
    samples = [
        (origin, "x"),
        (ColorRGBA(1.0, 0.5, 0.0), "red"),
        (CreateObjectSpec(ObjectType.MESH), "name"),
        (ModifyObjectSpec("Cube"), "visible"),
        (MaterialSpec("Cube", "Material"), "metallic"),
        (SceneObjectSummary("Cube", "MESH", origin), "name"),
        (SceneSummary("Scene", 1, 0, ()), "object_count"),
        (ObjectDetails("Cube", "MESH", origin, origin, origin, True, ()), "visible"),
        (OperationReceipt("create_object", "Cube", "created"), "message"),
        (ViewportImage(b"png", 1, 1), "width"),
        (BlenderStatus(True), "connected"),
    ]

    for value, field_name in samples:
        with pytest.raises(FrozenInstanceError):
            setattr(value, field_name, None)


def test_vector_and_color_export_fresh_lists() -> None:
    from src.core.domain.scene_operations import ColorRGBA, Vector3

    vector = Vector3(1.0, 2.0, 3.0)
    color = ColorRGBA(0.1, 0.2, 0.3, 0.4)

    first_vector = vector.as_list()
    first_color = color.as_list()
    first_vector[0] = 99.0
    first_color[0] = 99.0

    assert vector.as_list() == [1.0, 2.0, 3.0]
    assert color.as_list() == [0.1, 0.2, 0.3, 0.4]


def test_scene_ports_are_runtime_checkable_and_segregated() -> None:
    from src.core.ports.scene_operations_port import SceneCommandPort, SceneQueryPort

    class QueriesOnly:
        async def status(self):
            return None

        async def get_scene_info(self):
            return None

        async def get_object_info(self, name):
            return None

        async def get_viewport_screenshot(self, max_size=800):
            return None

    class BothPorts(QueriesOnly):
        async def create_object(self, spec):
            return None

        async def modify_object(self, spec):
            return None

        async def delete_object(self, name):
            return None

        async def apply_material(self, spec):
            return None

    queries = QueriesOnly()
    service = BothPorts()

    assert isinstance(queries, SceneQueryPort)
    assert not isinstance(queries, SceneCommandPort)
    assert isinstance(service, SceneQueryPort)
    assert isinstance(service, SceneCommandPort)
