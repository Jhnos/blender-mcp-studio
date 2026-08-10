"""Application contracts for shared client-neutral scene operations."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.domain.command import Command
from src.core.domain.scene_operations import (
    ColorRGBA,
    CreateObjectSpec,
    MaterialSpec,
    ModifyObjectSpec,
    ObjectType,
    Vector3,
)
from src.core.ports.blender_port import BlenderPort
from src.core.ports.mcp_port import ToolResult
from src.core.use_cases.scene_operations import SceneOperationsService

PNG_1X1 = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"


class FakeBlender(BlenderPort):
    """Complete hand-written port fake; only the external Blender boundary is replaced."""

    def __init__(self) -> None:
        self.connected = True
        self.result = ToolResult(True, "ok")
        self.scene_response: dict[str, object] = {
            "name": "Scene",
            "object_count": 1,
            "materials_count": 1,
            "objects": [{"name": "Cube", "type": "MESH", "location": [0.0, 0.0, 0.0]}],
        }
        self.commands: list[Command] = []
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.write_screenshot = True

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    async def is_connected(self) -> bool:
        return self.connected

    async def get_scene_info(self) -> dict[str, object]:
        return self.scene_response

    async def execute(self, command: Command) -> ToolResult:
        self.commands.append(command)
        return self.result

    async def call_tool(self, tool_name: str, arguments: dict[str, object]) -> ToolResult:
        self.calls.append((tool_name, arguments))
        if tool_name == "get_viewport_screenshot" and self.result.success:
            if self.write_screenshot:
                Path(str(arguments["filepath"])).write_bytes(PNG_1X1)
            return ToolResult(True, {"width": 1, "height": 1})
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
    fake_blender.result = ToolResult(True, "created Cube")

    receipt = await scene_service(fake_blender).create_object(
        CreateObjectSpec(ObjectType.MESH, "Cube")
    )

    assert fake_blender.commands == [
        Command(
            tool_name="create_object",
            arguments={
                "type": "MESH",
                "name": "Cube",
                "location": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
            },
        )
    ]
    assert receipt.object_name == "Cube"
    assert receipt.message == "created Cube"


@pytest.mark.asyncio
async def test_modify_object_sends_only_provided_fields(fake_blender: FakeBlender) -> None:
    spec = ModifyObjectSpec("Cube", location=Vector3(1.0, 2.0, 3.0), visible=False)

    await scene_service(fake_blender).modify_object(spec)

    assert fake_blender.commands == [
        Command(
            tool_name="modify_object",
            arguments={"name": "Cube", "location": [1.0, 2.0, 3.0], "visible": False},
        )
    ]


@pytest.mark.asyncio
async def test_delete_object_uses_high_level_command(fake_blender: FakeBlender) -> None:
    receipt = await scene_service(fake_blender).delete_object("Cube")

    assert fake_blender.commands == [Command(tool_name="delete_object", arguments={"name": "Cube"})]
    assert receipt.operation == "delete_object"


@pytest.mark.asyncio
async def test_apply_material_uses_high_level_command(fake_blender: FakeBlender) -> None:
    spec = MaterialSpec("Cube", "Red", ColorRGBA(1.0, 0.0, 0.0), 0.2, 0.8)

    await scene_service(fake_blender).apply_material(spec)

    assert fake_blender.commands == [
        Command(
            tool_name="apply_material",
            arguments={
                "object_name": "Cube",
                "material_name": "Red",
                "color": [1.0, 0.0, 0.0, 1.0],
                "metallic": 0.2,
                "roughness": 0.8,
            },
        )
    ]


@pytest.mark.asyncio
async def test_failed_tool_result_is_not_silently_converted(
    fake_blender: FakeBlender,
) -> None:
    from src.core.domain.exceptions import SceneOperationError

    fake_blender.result = ToolResult(False, None, "Object not found")

    with pytest.raises(SceneOperationError, match="Object not found"):
        await scene_service(fake_blender).delete_object("Ghost")


@pytest.mark.asyncio
async def test_scene_info_is_narrowed_to_domain_values(fake_blender: FakeBlender) -> None:
    scene = await scene_service(fake_blender).get_scene_info()

    assert scene.name == "Scene"
    assert scene.object_count == 1
    assert scene.objects[0].name == "Cube"
    assert scene.objects[0].location == Vector3()


@pytest.mark.asyncio
async def test_scene_info_missing_field_fails_explicitly(fake_blender: FakeBlender) -> None:
    from src.core.domain.exceptions import SceneOperationError

    del fake_blender.scene_response["objects"]

    with pytest.raises(SceneOperationError, match="missing: objects"):
        await scene_service(fake_blender).get_scene_info()


@pytest.mark.asyncio
async def test_scene_info_invalid_vector_fails_explicitly(fake_blender: FakeBlender) -> None:
    from src.core.domain.exceptions import SceneOperationError

    fake_blender.scene_response["objects"] = [
        {"name": "Cube", "type": "MESH", "location": [0.0, 1.0]}
    ]

    with pytest.raises(SceneOperationError, match="expected three finite numbers"):
        await scene_service(fake_blender).get_scene_info()


@pytest.mark.asyncio
async def test_object_info_is_narrowed_to_domain_values(fake_blender: FakeBlender) -> None:
    fake_blender.result = ToolResult(
        True,
        {
            "name": "Cube",
            "type": "MESH",
            "location": [0.0, 0.0, 0.0],
            "rotation": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
            "visible": True,
            "materials": ["Red"],
        },
    )

    details = await scene_service(fake_blender).get_object_info("Cube")

    assert details.name == "Cube"
    assert details.materials == ("Red",)
    assert fake_blender.calls == [("get_object_info", {"name": "Cube"})]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "bad_value", "message"),
    [
        ("visible", "true", "visible; expected a boolean"),
        ("materials", ["Red", 7], "materials; expected a list of strings"),
    ],
)
async def test_object_info_rejects_coerced_values(
    fake_blender: FakeBlender,
    field: str,
    bad_value: object,
    message: str,
) -> None:
    from src.core.domain.exceptions import SceneOperationError

    response: dict[str, object] = {
        "name": "Cube",
        "type": "MESH",
        "location": [0.0, 0.0, 0.0],
        "rotation": [0.0, 0.0, 0.0],
        "scale": [1.0, 1.0, 1.0],
        "visible": True,
        "materials": ["Red"],
    }
    response[field] = bad_value
    fake_blender.result = ToolResult(True, response)

    with pytest.raises(SceneOperationError, match=message):
        await scene_service(fake_blender).get_object_info("Cube")


@pytest.mark.asyncio
async def test_screenshot_bytes_are_returned_and_temp_file_is_deleted(
    fake_blender: FakeBlender,
) -> None:
    shot = await scene_service(fake_blender).get_viewport_screenshot(800)
    screenshot_path = Path(str(fake_blender.calls[-1][1]["filepath"]))

    assert shot.png_bytes.startswith(b"\x89PNG")
    assert (shot.width, shot.height) == (1, 1)
    assert not screenshot_path.exists()


@pytest.mark.asyncio
async def test_screenshot_missing_file_fails_explicitly_and_cleans_up(
    fake_blender: FakeBlender,
) -> None:
    from src.core.domain.exceptions import SceneOperationError

    fake_blender.write_screenshot = False

    with pytest.raises(SceneOperationError, match="created no PNG file"):
        await scene_service(fake_blender).get_viewport_screenshot(800)

    screenshot_path = Path(str(fake_blender.calls[-1][1]["filepath"]))
    assert not screenshot_path.exists()
