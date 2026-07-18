"""Rewrite high-level modeling tool calls into `execute_code` (bpy Python).

The LLM is offered structured tools (create_object, delete_object,
modify_object, apply_material), but the ahujasid socket addon only implements
`execute_code` (+ read tools) — it has NO handler for those names, so sending
them raises "Unknown command type" and the scene never changes.

This lives in the adapters layer, next to BlenderMCPAdapter, because it encodes
one specific backend's limitation and emits that backend's dialect (bpy Python)
— knowledge the use cases must not carry. BlenderMCPAdapter applies `translate`
at the single point every socket dispatch funnels through, and BlenderMCPClient
rejects any translatable tool that still reaches the socket, so "the addon only
sees execute_code" is *enforced* rather than merely intended. (It used to be
claimed here as "the single choke point" while a second dispatch path bypassed
it — see docs/LESSONS_LEARNED.md 2026-07-18.)

Values are injected via json.dumps so a crafted string argument becomes a Python
literal, not code (the sandbox is a 2nd layer). The generated string runs in
Blender; there is no bpy import here.
"""

from __future__ import annotations

import json

from src.core.domain.command import Command

# Tools the addon cannot handle directly → must be expressed as bpy code.
_TRANSLATABLE = {"create_object", "delete_object", "modify_object", "apply_material"}


def is_translatable(tool_name: str) -> bool:
    """True if this tool has no addon handler and must be rewritten to execute_code."""
    return tool_name in _TRANSLATABLE


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
    return "\n".join(
        [
            "import bpy",
            f"o = bpy.data.objects.get({_lit(a.get('name'))})",
            "if o:",
            "    deleted_name = o.name",
            "    bpy.data.objects.remove(o, do_unlink=True)",
            "    print('deleted', deleted_name)",
            "else: print('not found')",
        ]
    )


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
    if isinstance(color, (list, tuple)) and color:  # narrow-ok: elements coerced by float()
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
