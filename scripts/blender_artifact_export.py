"""Reusable Blender-only artifact export, preserving scene selection and visibility."""

from pathlib import Path

import bpy


def export_stl_mm(objects: list[bpy.types.Object], path: Path) -> None:
    """Export only the explicit printable meshes; metre-based geometry becomes millimetres."""
    if not objects or any(obj.type != "MESH" for obj in objects):
        raise ValueError("STL export requires an explicit non-empty mesh list")
    path.parent.mkdir(parents=True, exist_ok=True)
    selected = list(bpy.context.selected_objects)
    active = bpy.context.view_layer.objects.active
    visibility = [(obj, obj.hide_viewport, obj.hide_get()) for obj in objects]
    try:
        for obj in selected:
            obj.select_set(False)
        for obj, _, _ in visibility:
            obj.hide_viewport = False
            obj.hide_set(False)
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.wm.stl_export(
            filepath=str(path),
            check_existing=False,
            export_selected_objects=True,
            apply_modifiers=True,
            global_scale=1000.0,
            ascii_format=False,
        )
    finally:
        for obj, hidden_viewport, hidden_layer in visibility:
            obj.select_set(False)
            obj.hide_viewport = hidden_viewport
            obj.hide_set(hidden_layer)
        for obj in selected:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = active
