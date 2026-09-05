"""Blender dialect for per-object rename, selection and asset import."""

from __future__ import annotations

from src.adapters.blender_scripts.runner import ScriptOutcome, quote, run_script
from src.core.ports.blender_port import BlenderPort

_SELECT_CODE = """\
import bpy
bpy.ops.object.select_all(action='DESELECT')
obj = bpy.data.objects.get('{name}')
if obj is None:
    raise ValueError('Object not found: {name}')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
print(f'selected:{{obj.name}}')
"""


async def update_object(
    blender: BlenderPort,
    name: str,
    *,
    new_name: str | None = None,
    selected: bool | None = None,
) -> ScriptOutcome:
    """Rename and/or change the selection state of one object."""
    ops: list[str] = ["import bpy"]
    ops.append(f"obj = bpy.data.objects.get('{quote(name)}')")
    ops.append("if obj is None: raise ValueError(f'Object not found: {repr(obj)}')")

    if selected is not None:
        if not selected:
            ops.append("bpy.ops.object.select_all(action='DESELECT')")
        ops.append(f"obj.select_set({selected})")
        if selected:
            ops.append("bpy.context.view_layer.objects.active = obj")

    if new_name:
        ops.append(f"obj.name = '{quote(new_name)}'")

    ops.append("print('updated')")
    return await run_script(blender, "\n".join(ops))


async def select_object(blender: BlenderPort, name: str) -> ScriptOutcome:
    """Select one object and make it active, deselecting everything else."""
    return await run_script(blender, _SELECT_CODE.format(name=quote(name)))


async def import_gltf(blender: BlenderPort, path: str) -> ScriptOutcome:
    """Import a glTF/GLB file into the current scene."""
    code = f"bpy.ops.import_scene.gltf(filepath='{quote(path)}')"
    return await run_script(blender, code)
