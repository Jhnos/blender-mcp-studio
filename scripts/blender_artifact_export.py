"""Reusable Blender-only artifact export, preserving scene selection and visibility.

Three visibility flags matter here and every one of them has to be cleared, because
the STL exporter honours all three and says nothing when it writes an empty file:

* `hide_viewport` — drops the object out of the depsgraph entirely,
* `hide_set()`    — the per-view-layer eye,
* `hide_render`   — **the one this module used to miss.**

Measured on Blender 5.2.1, 2026-09-06, everything else held constant: exporting one
876-face body with `hide_render = True` wrote 84 bytes — a valid STL containing zero
triangles — and with it clear wrote 168,984. Generators hide their master bodies
before exporting them, so `arm_body_mm.stl`, `arm_tip_mm.stl` and `test_coupon_mm.stl`
all came out empty, from V1's unmodified generator as much as V2's. The files shipped
in `models/octopus-hand-v1/` were made on a Blender that did not do this.

That is the same failure class this project has already booked three times — a hidden
object turning an operation into a silent no-op — so the guard is at the chokepoint
rather than in the callers: an export that writes no triangles raises.
"""

import struct
from pathlib import Path

import bpy

#: A binary STL is an 80-byte header then a little-endian triangle count.
_STL_HEADER_BYTES = 80


def export_stl_mm(objects: list[bpy.types.Object], path: Path) -> None:
    """Export only the explicit printable meshes; metre-based geometry becomes millimetres."""
    if not objects or any(obj.type != "MESH" for obj in objects):
        raise ValueError("STL export requires an explicit non-empty mesh list")
    path.parent.mkdir(parents=True, exist_ok=True)
    selected = list(bpy.context.selected_objects)
    active = bpy.context.view_layer.objects.active
    visibility = [(obj, obj.hide_viewport, obj.hide_get(), obj.hide_render) for obj in objects]
    try:
        for obj in selected:
            obj.select_set(False)
        for obj, _, _, _ in visibility:
            obj.hide_viewport = False
            obj.hide_set(False)
            obj.hide_render = False
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
        for obj, hidden_viewport, hidden_layer, hidden_render in visibility:
            obj.select_set(False)
            obj.hide_viewport = hidden_viewport
            obj.hide_set(hidden_layer)
            obj.hide_render = hidden_render
        for obj in selected:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = active

    payload = path.read_bytes()
    triangles = (
        struct.unpack_from("<I", payload, _STL_HEADER_BYTES)[0]
        if len(payload) >= _STL_HEADER_BYTES + 4
        else 0
    )
    if triangles == 0:
        raise RuntimeError(
            f"{path.name} was written with no triangles from "
            f"{len(objects)} mesh(es) totalling "
            f"{sum(len(obj.data.polygons) for obj in objects)} faces — the export was "
            "silently skipped. Check every visibility flag on those objects."
        )
