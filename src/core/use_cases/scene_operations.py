"""Shared application service for client-neutral Blender scene operations."""

from __future__ import annotations

import math
import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

from src.core.domain.command import Command
from src.core.domain.exceptions import SceneOperationError
from src.core.domain.scene_operations import (
    BlenderStatus,
    CreateObjectSpec,
    MaterialSpec,
    ModifyObjectSpec,
    ObjectDetails,
    OperationReceipt,
    SceneObjectSummary,
    SceneSummary,
    Vector3,
    ViewportImage,
)
from src.core.ports.blender_port import BlenderPort
from src.core.ports.mcp_port import ToolResult

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _require_mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(
        value, Mapping
    ):  # narrow-ok: rebuilt below with explicitly checked string keys
        raise SceneOperationError(f"Blender returned invalid {context}; expected an object")
    narrowed: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise SceneOperationError(f"Blender returned invalid {context}; keys must be strings")
        narrowed[key] = item
    return narrowed


def _require_fields(value: dict[str, object], fields: set[str], context: str) -> None:
    missing = sorted(fields.difference(value))
    if missing:
        raise SceneOperationError(f"Blender {context} is missing: {', '.join(missing)}")


def _require_str(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise SceneOperationError(f"Blender returned invalid {field}; expected a string")
    return value


def _require_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SceneOperationError(f"Blender returned invalid {field}; expected an integer")
    return value


def _require_bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise SceneOperationError(f"Blender returned invalid {field}; expected a boolean")
    return value


def _require_sequence(value: object, field: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(
        value, Sequence
    ):  # narrow-ok: elements stay object and are narrowed per field by the callers
        raise SceneOperationError(f"Blender returned invalid {field}; expected a list")
    return value


def _vector(value: object, field: str) -> Vector3:
    items = _require_sequence(value, field)
    if len(items) != 3:
        raise SceneOperationError(
            f"Blender returned invalid {field}; expected three finite numbers"
        )
    numbers: list[float] = []
    for item in items:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise SceneOperationError(
                f"Blender returned invalid {field}; expected three finite numbers"
            )
        number = float(item)
        if not math.isfinite(number):
            raise SceneOperationError(
                f"Blender returned invalid {field}; expected three finite numbers"
            )
        numbers.append(number)
    return Vector3(*numbers)


def _string_tuple(value: object, field: str) -> tuple[str, ...]:
    items = _require_sequence(value, field)
    if any(not isinstance(item, str) for item in items):
        raise SceneOperationError(f"Blender returned invalid {field}; expected a list of strings")
    return tuple(item for item in items if isinstance(item, str))


class SceneOperationsService:
    """Orchestrate scene queries and commands through one injected Blender port."""

    def __init__(self, blender: BlenderPort) -> None:
        self._blender = blender

    async def status(self) -> BlenderStatus:
        return BlenderStatus(connected=await self._blender.is_connected())

    async def get_scene_info(self) -> SceneSummary:
        raw = _require_mapping(await self._blender.get_scene_info(), "scene info")
        _require_fields(raw, {"name", "object_count", "materials_count", "objects"}, "scene info")
        objects: list[SceneObjectSummary] = []
        for item in _require_sequence(raw["objects"], "scene objects"):
            obj = _require_mapping(item, "scene object")
            _require_fields(obj, {"name", "type", "location"}, "scene object")
            objects.append(
                SceneObjectSummary(
                    name=_require_str(obj["name"], "object name"),
                    object_type=_require_str(obj["type"], "object type"),
                    location=_vector(obj["location"], "object location"),
                )
            )
        return SceneSummary(
            name=_require_str(raw["name"], "scene name"),
            object_count=_require_int(raw["object_count"], "object count"),
            materials_count=_require_int(raw["materials_count"], "materials count"),
            objects=tuple(objects),
        )

    async def get_object_info(self, name: str) -> ObjectDetails:
        result = await self._blender.call_tool("get_object_info", {"name": name})
        raw = _require_mapping(self._success(result, "get_object_info"), "object info")
        _require_fields(
            raw,
            {"name", "type", "location", "rotation", "scale", "visible", "materials"},
            "object info",
        )
        return ObjectDetails(
            name=_require_str(raw["name"], "object name"),
            object_type=_require_str(raw["type"], "object type"),
            location=_vector(raw["location"], "location"),
            rotation=_vector(raw["rotation"], "rotation"),
            scale=_vector(raw["scale"], "scale"),
            visible=_require_bool(raw["visible"], "visible"),
            materials=_string_tuple(raw["materials"], "materials"),
        )

    async def get_viewport_screenshot(self, max_size: int = 800) -> ViewportImage:
        file_descriptor, raw_path = tempfile.mkstemp(suffix=".png")
        os.close(file_descriptor)
        path = Path(raw_path)
        try:
            result = await self._blender.call_tool(
                "get_viewport_screenshot",
                {"filepath": raw_path, "max_size": max_size, "format": "png"},
            )
            metadata = _require_mapping(
                self._success(result, "get_viewport_screenshot"), "screenshot metadata"
            )
            _require_fields(metadata, {"width", "height"}, "screenshot metadata")
            if not path.exists() or path.stat().st_size == 0:
                raise SceneOperationError("Blender reported a screenshot but created no PNG file")
            data = path.read_bytes()
            if not data.startswith(_PNG_SIGNATURE):
                raise SceneOperationError("Blender screenshot is not a PNG file")
            return ViewportImage(
                png_bytes=data,
                width=_require_int(metadata["width"], "screenshot width"),
                height=_require_int(metadata["height"], "screenshot height"),
            )
        finally:
            path.unlink(missing_ok=True)

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
