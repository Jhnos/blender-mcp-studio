"""Blender 5.1 scene-export adapter contract tests."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.adapters.export.blender_scene_exporter import BlenderSceneExportAdapter
from src.core.domain.command import Command
from src.core.domain.exceptions import SceneExportError
from src.core.domain.scene_export import SceneExportFormat, SceneExportSpec
from src.core.ports.mcp_port import ToolResult


class ExportingBlender:
    def __init__(self, *, success: bool = True) -> None:
        self.success = success
        self.commands: list[Command] = []

    async def execute(self, command: Command) -> ToolResult:
        self.commands.append(command)
        if not self.success:
            return ToolResult(False, None, "operator unavailable")
        code = str(command.arguments["code"])
        match = re.search(r"^filepath = (.+)$", code, re.MULTILINE)
        assert match is not None
        Path(json.loads(match.group(1))).write_bytes(b"printable mesh")
        return ToolResult(True, "exported")


@pytest.mark.asyncio
async def test_stl_export_uses_blender_51_operator_and_millimetres() -> None:
    blender = ExportingBlender()
    adapter = BlenderSceneExportAdapter(blender)  # type: ignore[arg-type]

    artifact = await adapter.export(
        SceneExportSpec(SceneExportFormat.STL, selection_only=True, apply_modifiers=True)
    )

    code = str(blender.commands[0].arguments["code"])
    assert "bpy.ops.wm.stl_export(" in code
    assert "export_selected_objects=True" in code
    assert "apply_modifiers=True" in code
    assert "global_scale=1000.0" in code
    assert artifact.content == b"printable mesh"
    assert artifact.filename == "blender-scene.stl"
    assert artifact.media_type == "model/stl"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("format", "operator", "media_type"),
    [
        (SceneExportFormat.OBJ, "bpy.ops.wm.obj_export(", "model/obj"),
        (SceneExportFormat.PLY, "bpy.ops.wm.ply_export(", "application/octet-stream"),
        (SceneExportFormat.GLB, "bpy.ops.export_scene.gltf(", "model/gltf-binary"),
        (SceneExportFormat.FBX, "bpy.ops.export_scene.fbx(", "application/octet-stream"),
    ],
)
async def test_export_registry_covers_each_supported_format(
    format: SceneExportFormat, operator: str, media_type: str
) -> None:
    blender = ExportingBlender()
    adapter = BlenderSceneExportAdapter(blender)  # type: ignore[arg-type]

    artifact = await adapter.export(SceneExportSpec(format))

    assert operator in str(blender.commands[0].arguments["code"])
    assert artifact.filename.endswith(f".{format.value}")
    assert artifact.media_type == media_type


@pytest.mark.asyncio
async def test_export_failure_is_explicit() -> None:
    adapter = BlenderSceneExportAdapter(ExportingBlender(success=False))  # type: ignore[arg-type]

    with pytest.raises(SceneExportError, match="operator unavailable"):
        await adapter.export(SceneExportSpec(SceneExportFormat.STL))
