"""Translate high-level modeling tool calls into `execute_code` (bpy Python).

The LLM is offered structured tools (create_object, delete_object,
modify_object, apply_material), but the BlenderMCP addon only implements
`execute_code` (+ read tools) — it has NO handler for those names, so sending
them raised "Unknown command type" and the scene never changed.

This module is the single choke point that rewrites such a Command into an
equivalent `execute_code` Command, matching the addon's design (all mutation
goes through Python). Values are injected via json.dumps so a crafted string
argument becomes a Python literal, not code (the api sandbox is a 2nd layer).

Pure function — no I/O, no bpy import here (the code string runs in Blender).
"""

from __future__ import annotations

import json

from src.core.domain.command import Command

# Tools the addon cannot handle directly → must be expressed as bpy code.
_TRANSLATABLE = {"create_object", "delete_object", "modify_object", "apply_material"}


def _lit(value: object) -> str:
    """A Python literal for a JSON-ish value (safe: no code injection)."""
    return json.dumps(value)


def _create_object(a: dict[str, object]) -> str:
    obj_type = str(a.get("type", "MESH")).upper()
    name = a.get("name")
    location = a.get("location") or [0, 0, 0]
    scale = a.get("scale")
    adder = {
        "MESH": "bpy.ops.mesh.primitive_cube_add",
        "LIGHT": "bpy.ops.object.light_add",
        "CAMERA": "bpy.ops.object.camera_add",
        "CURVE": "bpy.ops.curve.primitive_bezier_curve_add",
    }.get(obj_type, "bpy.ops.mesh.primitive_cube_add")
    lines = [
        "import bpy",
        f"{adder}(location=tuple({_lit(location)}))",
        "obj = bpy.context.active_object",
    ]
    if name:
        lines.append(f"obj.name = {_lit(name)}")
    if scale:
        lines.append(f"obj.scale = tuple({_lit(scale)})")
    lines.append("print('created', obj.name)")
    return "\n".join(lines)


def _delete_object(a: dict[str, object]) -> str:
    return "\n".join([
        "import bpy",
        f"o = bpy.data.objects.get({_lit(a.get('name'))})",
        "if o: bpy.data.objects.remove(o, do_unlink=True); print('deleted', o.name)",
        "else: print('not found')",
    ])


def _modify_object(a: dict[str, object]) -> str:
    lines = ["import bpy", f"o = bpy.data.objects.get({_lit(a.get('name'))})", "if o:"]
    if a.get("location") is not None:
        lines.append(f"    o.location = tuple({_lit(a['location'])})")
    if a.get("rotation") is not None:
        lines.append(f"    o.rotation_euler = tuple({_lit(a['rotation'])})")
    if a.get("scale") is not None:
        lines.append(f"    o.scale = tuple({_lit(a['scale'])})")
    if a.get("visible") is not None:
        lines.append(f"    o.hide_viewport = not {_lit(bool(a['visible']))}")
    lines.append("    print('modified', o.name)")
    lines.append("else: print('not found')")
    return "\n".join(lines)


def _apply_material(a: dict[str, object]) -> str:
    color = a.get("color")
    lines = [
        "import bpy",
        f"o = bpy.data.objects.get({_lit(a.get('object_name'))})",
        "if o:",
        f"    name = {_lit(a.get('material_name', 'Material'))}",
        "    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)",
        "    mat.use_nodes = True",
        "    b = mat.node_tree.nodes.get('Principled BSDF')",
        "    if b:",
    ]
    if isinstance(color, (list, tuple)) and color:
        c = [float(x) for x in color]
        rgba = c + [1.0] * (4 - len(c)) if len(c) < 4 else c[:4]
        lines.append(f"        b.inputs['Base Color'].default_value = tuple({_lit(rgba)})")
    if a.get("metallic") is not None:
        lines.append(f"        b.inputs['Metallic'].default_value = {_lit(a['metallic'])}")
    if a.get("roughness") is not None:
        lines.append(f"        b.inputs['Roughness'].default_value = {_lit(a['roughness'])}")
    lines += [
        "    if o.data.materials: o.data.materials[0] = mat",
        "    else: o.data.materials.append(mat)",
        "    print('applied', name, 'to', o.name)",
        "else: print('not found')",
    ]
    return "\n".join(lines)


_CODEGEN = {
    "create_object": _create_object,
    "delete_object": _delete_object,
    "modify_object": _modify_object,
    "apply_material": _apply_material,
}


def translate(command: Command) -> Command:
    """Rewrite an unhandled modeling tool into an equivalent execute_code Command.

    Non-translatable commands (execute_code, get_scene_info, …) pass through.
    """
    if command.tool_name not in _TRANSLATABLE:
        return command
    code = _CODEGEN[command.tool_name](command.arguments)
    return Command(tool_name="execute_code", arguments={"code": code})
