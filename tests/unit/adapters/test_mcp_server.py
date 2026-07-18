"""Protocol-level contracts for the client-neutral FastMCP adapter."""

from __future__ import annotations

from typing import Any

import pytest
from fastmcp import Client, FastMCP

from src.core.domain.exceptions import SceneOperationError
from src.core.domain.scene_operations import (
    BlenderStatus,
    ColorRGBA,
    CreateObjectSpec,
    MaterialSpec,
    ModifyObjectSpec,
    ObjectDetails,
    ObjectType,
    OperationReceipt,
    SceneSummary,
    Vector3,
    ViewportImage,
)

EXPECTED_TOOLS = {
    "apply_material",
    "blender_status",
    "create_object",
    "delete_object",
    "get_object_info",
    "get_scene_info",
    "get_viewport_screenshot",
    "modify_object",
}

POLICY = {
    "blender_status": (True, False, True, False),
    "get_scene_info": (True, False, True, False),
    "get_object_info": (True, False, True, False),
    "get_viewport_screenshot": (True, False, True, False),
    "create_object": (False, False, False, False),
    "modify_object": (False, True, True, False),
    "delete_object": (False, True, False, False),
    "apply_material": (False, True, False, False),
}


class FakeSceneService:
    """Complete fake implementing both scene-operation ports."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.error: SceneOperationError | None = None

    def _record(self, operation: str, argument: object = None) -> None:
        if self.error is not None:
            raise self.error
        self.calls.append((operation, argument))

    async def status(self) -> BlenderStatus:
        self._record("status")
        return BlenderStatus(True)

    async def get_scene_info(self) -> SceneSummary:
        self._record("get_scene_info")
        return SceneSummary("Scene", 0, 0, ())

    async def get_object_info(self, name: str) -> ObjectDetails:
        self._record("get_object_info", name)
        origin = Vector3()
        return ObjectDetails(name, "MESH", origin, origin, Vector3(1.0, 1.0, 1.0), True, ())

    async def get_viewport_screenshot(self, max_size: int = 800) -> ViewportImage:
        self._record("get_viewport_screenshot", max_size)
        return ViewportImage(b"\x89PNG\r\n\x1a\n", 1, 1)

    async def create_object(self, spec: CreateObjectSpec) -> OperationReceipt:
        self._record("create_object", spec)
        return OperationReceipt("create_object", spec.name or "active object", "created")

    async def modify_object(self, spec: ModifyObjectSpec) -> OperationReceipt:
        self._record("modify_object", spec)
        return OperationReceipt("modify_object", spec.name, "modified")

    async def delete_object(self, name: str) -> OperationReceipt:
        self._record("delete_object", name)
        return OperationReceipt("delete_object", name, "deleted")

    async def apply_material(self, spec: MaterialSpec) -> OperationReceipt:
        self._record("apply_material", spec)
        return OperationReceipt("apply_material", spec.object_name, "applied")


@pytest.fixture
def fake_scene_service() -> FakeSceneService:
    return FakeSceneService()


def server_for(fake_scene_service: FakeSceneService) -> FastMCP:
    from src.adapters.mcp_server import create_mcp_server

    return create_mcp_server(fake_scene_service, fake_scene_service)


@pytest.mark.asyncio
async def test_catalog_is_exact_and_annotations_match_policy(
    fake_scene_service: FakeSceneService,
) -> None:
    async with Client(server_for(fake_scene_service)) as client:
        tools = await client.list_tools()

    assert {tool.name for tool in tools} == EXPECTED_TOOLS
    by_name = {tool.name: tool for tool in tools}
    for name, expected in POLICY.items():
        annotations = by_name[name].annotations
        assert annotations is not None
        assert annotations.title
        assert (
            annotations.readOnlyHint,
            annotations.destructiveHint,
            annotations.idempotentHint,
            annotations.openWorldHint,
        ) == expected


@pytest.mark.asyncio
async def test_mutation_schemas_reject_unknown_fields(
    fake_scene_service: FakeSceneService,
) -> None:
    async with Client(server_for(fake_scene_service)) as client:
        tools = await client.list_tools()
        result = await client.call_tool(
            "create_object",
            {"object_type": "MESH", "code": "import bpy"},
            raise_on_error=False,
        )

    by_name = {tool.name: tool for tool in tools}
    for name in ("create_object", "modify_object", "apply_material"):
        assert by_name[name].inputSchema["additionalProperties"] is False
    assert result.is_error is True
    assert fake_scene_service.calls == []


@pytest.mark.asyncio
async def test_invalid_color_is_rejected_before_service(
    fake_scene_service: FakeSceneService,
) -> None:
    async with Client(server_for(fake_scene_service)) as client:
        result = await client.call_tool(
            "apply_material",
            {
                "object_name": "Cube",
                "material_name": "Red",
                "color": [2.0, 0.0, 0.0, 1.0],
            },
            raise_on_error=False,
        )

    assert result.is_error is True
    assert fake_scene_service.calls == []


TOOL_CALLS: list[tuple[str, dict[str, Any], tuple[str, object]]] = [
    ("blender_status", {}, ("status", None)),
    ("get_scene_info", {}, ("get_scene_info", None)),
    ("get_object_info", {"name": "Cube"}, ("get_object_info", "Cube")),
    (
        "get_viewport_screenshot",
        {"max_size": 640},
        ("get_viewport_screenshot", 640),
    ),
    (
        "create_object",
        {"object_type": "MESH", "name": "Cube"},
        ("create_object", CreateObjectSpec(ObjectType.MESH, "Cube")),
    ),
    (
        "modify_object",
        {"name": "Cube", "location": [1.0, 2.0, 3.0], "visible": False},
        (
            "modify_object",
            ModifyObjectSpec("Cube", location=Vector3(1.0, 2.0, 3.0), visible=False),
        ),
    ),
    ("delete_object", {"name": "Cube"}, ("delete_object", "Cube")),
    (
        "apply_material",
        {
            "object_name": "Cube",
            "material_name": "Red",
            "color": [1.0, 0.0, 0.0, 1.0],
            "metallic": 0.2,
            "roughness": 0.8,
        },
        (
            "apply_material",
            MaterialSpec("Cube", "Red", ColorRGBA(1.0, 0.0, 0.0, 1.0), 0.2, 0.8),
        ),
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("tool_name", "arguments", "expected_call"), TOOL_CALLS)
async def test_every_tool_routes_to_its_narrow_port_operation(
    fake_scene_service: FakeSceneService,
    tool_name: str,
    arguments: dict[str, Any],
    expected_call: tuple[str, object],
) -> None:
    async with Client(server_for(fake_scene_service)) as client:
        result = await client.call_tool(tool_name, arguments)

    assert result.is_error is False
    assert fake_scene_service.calls == [expected_call]


@pytest.mark.asyncio
async def test_recoverable_service_error_becomes_actionable_tool_error(
    fake_scene_service: FakeSceneService,
) -> None:
    fake_scene_service.error = SceneOperationError("Object not found: Ghost")

    async with Client(server_for(fake_scene_service)) as client:
        result = await client.call_tool("get_object_info", {"name": "Ghost"}, raise_on_error=False)

    assert result.is_error is True
    assert "Object not found: Ghost" in result.content[0].text  # type: ignore[union-attr]
    assert "Traceback" not in result.content[0].text  # type: ignore[union-attr]
