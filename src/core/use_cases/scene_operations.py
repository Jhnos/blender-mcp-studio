"""Shared application service for client-neutral Blender scene operations.

Queries are answered by the port as domain DTOs; nothing here narrows a
Blender reply. That decoding lives in the adapters (DEFERRALS D-001), which
is why this file imports no narrowing helpers and knows nothing about the
temporary file a screenshot is written to.
"""

from __future__ import annotations

from src.core.domain.command import Command
from src.core.domain.exceptions import SceneOperationError
from src.core.domain.scene_operations import (
    BlenderStatus,
    CreateObjectSpec,
    MaterialSpec,
    ModifyObjectSpec,
    ObjectDetails,
    OperationReceipt,
    SceneSummary,
    ViewportImage,
)
from src.core.ports.blender_port import BlenderPort
from src.core.ports.mcp_port import ToolResult


class SceneOperationsService:
    """Orchestrate scene queries and commands through one injected Blender port."""

    def __init__(self, blender: BlenderPort) -> None:
        self._blender = blender

    async def status(self) -> BlenderStatus:
        return BlenderStatus(connected=await self._blender.is_connected())

    async def get_scene_info(self) -> SceneSummary:
        return await self._blender.scene_summary()

    async def get_object_info(self, name: str) -> ObjectDetails:
        return await self._blender.object_details(name)

    async def get_viewport_screenshot(self, max_size: int = 800) -> ViewportImage:
        return await self._blender.viewport_screenshot(max_size)

    async def create_object(self, spec: CreateObjectSpec) -> OperationReceipt:
        arguments: dict[str, object] = {
            "type": spec.object_type.value,
            "location": spec.location.as_list(),
            "scale": spec.scale.as_list(),
        }
        if spec.name is not None:
            arguments["name"] = spec.name
        message = await self._execute("create_object", arguments)
        return OperationReceipt("create_object", spec.name or "active object", message)

    async def modify_object(self, spec: ModifyObjectSpec) -> OperationReceipt:
        arguments: dict[str, object] = {"name": spec.name}
        for key, value in (
            ("location", spec.location),
            ("rotation", spec.rotation),
            ("scale", spec.scale),
        ):
            if value is not None:
                arguments[key] = value.as_list()
        if spec.visible is not None:
            arguments["visible"] = spec.visible
        message = await self._execute("modify_object", arguments)
        return OperationReceipt("modify_object", spec.name, message)

    async def delete_object(self, name: str) -> OperationReceipt:
        message = await self._execute("delete_object", {"name": name})
        return OperationReceipt("delete_object", name, message)

    async def apply_material(self, spec: MaterialSpec) -> OperationReceipt:
        arguments: dict[str, object] = {
            "object_name": spec.object_name,
            "material_name": spec.material_name,
        }
        if spec.color is not None:
            arguments["color"] = spec.color.as_list()
        if spec.metallic is not None:
            arguments["metallic"] = spec.metallic
        if spec.roughness is not None:
            arguments["roughness"] = spec.roughness
        message = await self._execute("apply_material", arguments)
        return OperationReceipt("apply_material", spec.object_name, message)

    async def _execute(self, operation: str, arguments: dict[str, object]) -> str:
        result = await self._blender.execute(Command(tool_name=operation, arguments=arguments))
        output = self._success(result, operation)
        if not isinstance(output, str):
            raise SceneOperationError(f"{operation} returned an invalid success message")
        return output

    @staticmethod
    def _success(result: ToolResult, operation: str) -> object:
        if not result.success:
            raise SceneOperationError(
                result.error or f"{operation} failed without an error message"
            )
        return result.output
