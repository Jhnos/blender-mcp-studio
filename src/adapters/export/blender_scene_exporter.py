"""Blender 5.1 exporter anti-corruption layer."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from src.core.domain.command import Command
from src.core.domain.exceptions import BlenderConnectionError, SceneExportError
from src.core.domain.scene_export import ExportArtifact, SceneExportFormat, SceneExportSpec
from src.core.ports.blender_port import BlenderPort


@dataclass(frozen=True, slots=True)
class _ExportDefinition:
    operator: str
    media_type: str
    selection_key: str
    modifiers_key: str
    triangulate_key: str | None = None
    millimetres: bool = False
    fixed_arguments: tuple[tuple[str, object], ...] = ()


_EXPORTERS = {
    SceneExportFormat.STL: _ExportDefinition(
        "bpy.ops.wm.stl_export",
        "model/stl",
        "export_selected_objects",
        "apply_modifiers",
        millimetres=True,
        fixed_arguments=(("ascii_format", False),),
    ),
    SceneExportFormat.OBJ: _ExportDefinition(
        "bpy.ops.wm.obj_export",
        "model/obj",
        "export_selected_objects",
        "apply_modifiers",
        "export_triangulated_mesh",
        True,
        (("export_materials", True),),
    ),
    SceneExportFormat.PLY: _ExportDefinition(
        "bpy.ops.wm.ply_export",
        "application/octet-stream",
        "export_selected_objects",
        "apply_modifiers",
        "export_triangulated_mesh",
        True,
    ),
    SceneExportFormat.GLB: _ExportDefinition(
        "bpy.ops.export_scene.gltf",
        "model/gltf-binary",
        "use_selection",
        "export_apply",
        fixed_arguments=(
            ("export_format", "GLB"),
            ("export_animations", False),
            ("export_cameras", False),
            ("export_lights", False),
        ),
    ),
    SceneExportFormat.FBX: _ExportDefinition(
        "bpy.ops.export_scene.fbx",
        "application/octet-stream",
        "use_selection",
        "use_mesh_modifiers",
        "use_triangles",
        fixed_arguments=(("bake_anim", False),),
    ),
}


def _python_literal(value: object) -> str:
    if isinstance(value, str):
        return json.dumps(value)
    return repr(value)


def _export_code(path: Path, spec: SceneExportSpec) -> str:
    definition = _EXPORTERS[spec.format]
    arguments: list[tuple[str, object]] = [
        ("filepath", str(path)),
        ("check_existing", False),
        (definition.selection_key, spec.selection_only),
        (definition.modifiers_key, spec.apply_modifiers),
    ]
    if definition.triangulate_key is not None:
        arguments.append((definition.triangulate_key, spec.triangulate))
    if definition.millimetres:
        arguments.append(("global_scale", 1000.0))
    arguments.extend(definition.fixed_arguments)
    rendered = ",\n    ".join(f"{key}={_python_literal(value)}" for key, value in arguments)
    return (
        "import bpy\n"
        f"filepath = {json.dumps(str(path))}\n"
        f"{definition.operator}(\n    {rendered}\n)\n"
        "print('exported', filepath)"
    )


class BlenderSceneExportAdapter:
    """Translate export specs to current Blender operators and return file bytes."""

    def __init__(self, blender: BlenderPort) -> None:
        self._blender = blender

    async def export(self, spec: SceneExportSpec) -> ExportArtifact:
        file_descriptor, raw_path = tempfile.mkstemp(suffix=f".{spec.format.value}")
        os.close(file_descriptor)
        path = Path(raw_path)
        path.unlink(missing_ok=True)
        try:
            result = await self._blender.execute(
                Command(tool_name="execute_code", arguments={"code": _export_code(path, spec)})
            )
            if not result.success:
                raise SceneExportError(result.error or "Blender export failed without a reason")
            if not path.exists() or path.stat().st_size == 0:
                raise SceneExportError("Blender reported success but produced no export file")
            definition = _EXPORTERS[spec.format]
            return ExportArtifact(
                content=path.read_bytes(),
                filename=f"blender-scene.{spec.format.value}",
                media_type=definition.media_type,
            )
        except BlenderConnectionError:
            raise
        finally:
            path.unlink(missing_ok=True)
