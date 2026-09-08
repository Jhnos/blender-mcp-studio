"""Application contracts for shared client-neutral scene operations.

The use case speaks the domain language only. Queries come back from the port
as typed DTOs, so nothing here narrows a Blender reply — that moved to
`src/adapters/blender_scene_decoding.py` (DEFERRALS D-001), and the last test
in this file keeps it there.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.domain.command import Command
from src.core.domain.exceptions import SceneOperationError
from src.core.domain.scene_operations import (
    ColorRGBA,
    CreateObjectSpec,
    MaterialSpec,
    ModifyObjectSpec,
    ObjectDetails,
    ObjectType,
    SceneObjectSummary,
    SceneSummary,
    Vector3,
    ViewportImage,
)
from src.core.ports.blender_port import BlenderPort
from src.core.ports.mcp_port import ToolResult
from src.core.use_cases.scene_operations import SceneOperationsService

PNG_1X1 = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
SCENE = SceneSummary(
    name="Scene",
    object_count=1,
    materials_count=1,
    objects=(SceneObjectSummary("Cube", "MESH", Vector3()),),
)
CUBE = ObjectDetails(
    name="Cube",
    object_type="MESH",
    location=Vector3(),
    rotation=Vector3(),
    scale=Vector3(1.0, 1.0, 1.0),
    visible=True,
    materials=("Red",),
)


class FakeBlender(BlenderPort):
    """Complete hand-written port fake; only the external Blender boundary is replaced."""

    def __init__(self) -> None:
        self.connected = True
        self.result = ToolResult(True, "ok")
        self.commands: list[Command] = []
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.queried: list[str] = []

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    async def is_connected(self) -> bool:
        return self.connected

    async def scene_summary(self) -> SceneSummary:
        self.queried.append("scene")
        return SCENE

    async def object_details(self, name: str) -> ObjectDetails:
        self.queried.append(name)
        return CUBE

    async def viewport_screenshot(self, max_size: int = 800) -> ViewportImage:
        self.queried.append(f"screenshot:{max_size}")
        return ViewportImage(png_bytes=PNG_1X1, width=1, height=1)

    async def execute(self, command: Command) -> ToolResult:
        self.commands.append(command)
        return self.result

    async def call_tool(self, tool_name: str, arguments: dict[str, object]) -> ToolResult:
        self.calls.append((tool_name, arguments))
        return self.result


@pytest.fixture
def fake_blender() -> FakeBlender:
    return FakeBlender()


def scene_service(fake_blender: FakeBlender) -> SceneOperationsService:
    return SceneOperationsService(fake_blender)


@pytest.mark.asyncio
async def test_status_reflects_shared_blender_connection(fake_blender: FakeBlender) -> None:
    fake_blender.connected = False

    status = await scene_service(fake_blender).status()

    assert status.connected is False


@pytest.mark.asyncio
async def test_create_object_uses_high_level_command(fake_blender: FakeBlender) -> None:
    receipt = await scene_service(fake_blender).create_object(
        CreateObjectSpec(
            object_type=ObjectType.CUBE,
            name="Cube",
            location=Vector3(1.0, 2.0, 3.0),
            scale=Vector3(2.0, 2.0, 2.0),
        )
    )

    assert receipt.operation == "create_object"
    assert receipt.object_name == "Cube"
    assert fake_blender.commands[0].tool_name == "create_object"
    assert fake_blender.commands[0].arguments == {
        "type": "CUBE",
        "location": [1.0, 2.0, 3.0],
        "scale": [2.0, 2.0, 2.0],
        "name": "Cube",
    }


@pytest.mark.asyncio
async def test_modify_object_sends_only_provided_fields(fake_blender: FakeBlender) -> None:
    await scene_service(fake_blender).modify_object(
        ModifyObjectSpec(name="Cube", location=Vector3(0.0, 0.0, 1.0), visible=False)
    )

    assert fake_blender.commands[0].tool_name == "modify_object"
    assert fake_blender.commands[0].arguments == {
        "name": "Cube",
        "location": [0.0, 0.0, 1.0],
        "visible": False,
    }


@pytest.mark.asyncio
async def test_delete_object_uses_high_level_command(fake_blender: FakeBlender) -> None:
    receipt = await scene_service(fake_blender).delete_object("Cube")

    assert receipt.operation == "delete_object"
    assert fake_blender.commands[0].tool_name == "delete_object"
    assert fake_blender.commands[0].arguments == {"name": "Cube"}


@pytest.mark.asyncio
async def test_apply_material_uses_high_level_command(fake_blender: FakeBlender) -> None:
    await scene_service(fake_blender).apply_material(
        MaterialSpec(
            object_name="Cube",
            material_name="Red",
            color=ColorRGBA(1.0, 0.0, 0.0),
            metallic=0.5,
            roughness=0.25,
        )
    )

    assert fake_blender.commands[0].tool_name == "apply_material"
    assert fake_blender.commands[0].arguments == {
        "object_name": "Cube",
        "material_name": "Red",
        "color": [1.0, 0.0, 0.0, 1.0],
        "metallic": 0.5,
        "roughness": 0.25,
    }


@pytest.mark.asyncio
async def test_failed_tool_result_is_not_silently_converted(
    fake_blender: FakeBlender,
) -> None:
    fake_blender.result = ToolResult(False, None, "Object not found")

    with pytest.raises(SceneOperationError, match="Object not found"):
        await scene_service(fake_blender).delete_object("Ghost")


@pytest.mark.asyncio
async def test_a_success_without_a_message_is_refused(fake_blender: FakeBlender) -> None:
    fake_blender.result = ToolResult(True, {"not": "a message"})

    with pytest.raises(SceneOperationError, match="invalid success message"):
        await scene_service(fake_blender).delete_object("Cube")


@pytest.mark.asyncio
async def test_queries_are_answered_by_the_port_as_typed_values(
    fake_blender: FakeBlender,
) -> None:
    service = scene_service(fake_blender)

    assert await service.get_scene_info() is SCENE
    assert await service.get_object_info("Cube") is CUBE
    shot = await service.get_viewport_screenshot(640)
    assert shot.png_bytes.startswith(b"\x89PNG") and (shot.width, shot.height) == (1, 1)
    assert fake_blender.queried == ["scene", "Cube", "screenshot:640"]


def test_the_use_case_decodes_nothing() -> None:
    """D-001 closed: the third copy of the narrowing predicates cannot reappear here."""
    source = Path(SceneOperationsService.__module__.replace(".", "/") + ".py").read_text(
        encoding="utf-8"
    )

    assert "_require_" not in source
    assert "Mapping" not in source and "Sequence" not in source
    assert "tempfile" not in source
