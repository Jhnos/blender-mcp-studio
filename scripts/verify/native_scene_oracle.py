"""Independent raw Blender-state observer shared by isolated native fixtures.

This deliberately does not import the production session/restoration implementation.
"""

from __future__ import annotations

import hashlib
import json

import bpy


def mesh_geometry(obj: bpy.types.Object) -> str | None:
    if obj.type != "MESH":
        return None
    values = [
        [tuple(vertex.co) for vertex in obj.data.vertices],
        [tuple(edge.vertices) for edge in obj.data.edges],
        [tuple(face.vertices) for face in obj.data.polygons],
    ]
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()


def oracle_property(value: object) -> object:
    convert = getattr(value, "to_dict", None) or getattr(value, "to_list", None)
    if callable(convert):
        return convert()
    if isinstance(value, bpy.types.ID):
        return {"type": value.bl_rna.identifier, "name": value.name}
    raise TypeError("unsupported fixture property")


def oracle_ui(obj: bpy.types.ID) -> dict[str, object]:
    values = {}
    keys = obj.keys()
    for key in keys:
        try:
            values[key] = obj.id_properties_ui(key).as_dict()
        except TypeError:
            values[key] = None
    return values


def relations(obj: bpy.types.Object) -> dict[str, object]:
    animation = obj.animation_data
    return {
        "parent": obj.parent.name if obj.parent else None,
        "data": obj.data.name if obj.data else None,
        "drivers": [
            [
                curve.data_path,
                curve.array_index,
                curve.driver.type,
                curve.driver.expression,
                [
                    [
                        v.name,
                        v.type,
                        [[t.id.name if t.id else None, t.data_path] for t in v.targets],
                    ]
                    for v in curve.driver.variables
                ],
            ]
            for curve in animation.drivers
        ]
        if animation
        else [],
    }


def original_state() -> str:
    """Independent observer: raw originals, not the session's own report."""
    rows = {
        obj.name: {
            "pointer": obj.as_pointer(),
            "parent": obj.parent.name if obj.parent else None,
            "basis": [tuple(row) for row in obj.matrix_basis],
            "props": dict(obj.items()),
            "ui": oracle_ui(obj),
            "geometry": mesh_geometry(obj),
            "drivers": [
                (curve.data_path, curve.array_index, curve.driver.expression)
                for curve in obj.animation_data.drivers
            ]
            if obj.animation_data
            else [],
            "selected": obj.select_get(),
            "hidden": obj.hide_viewport,
        }
        for obj in bpy.data.objects
    }
    value = {
        "ids": sorted(
            (item.bl_rna.identifier, item.name, item.as_pointer()) for item in bpy.data.user_map()
        ),
        "objects": rows,
        "scene": bpy.context.scene.name,
        "active": bpy.context.view_layer.objects.active.name
        if bpy.context.view_layer.objects.active
        else None,
        "file": bpy.data.filepath,
    }
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=oracle_property).encode()
    ).hexdigest()


def portable_native_state(source_sha256: str) -> dict[str, object]:
    """Compare an isolated file load with an explicit maintenance reset across processes."""
    bpy.context.view_layer.update()
    objects = {}
    for obj in bpy.data.objects:
        state = {
            "basis": [tuple(row) for row in obj.matrix_basis],
            "parent_inverse": [tuple(row) for row in obj.matrix_parent_inverse],
            "relations": relations(obj),
            "properties": dict(obj.items()),
            "ui": oracle_ui(obj),
            "visibility": [obj.hide_render, obj.hide_viewport, obj.hide_get()],
            "selected": obj.select_get(),
            "materials": [
                slot.material.name if slot.material else None for slot in obj.material_slots
            ],
            "units": [
                bpy.context.scene.unit_settings.system,
                bpy.context.scene.unit_settings.scale_length,
            ],
            "frame": [bpy.context.scene.frame_current, bpy.context.scene.frame_subframe],
        }
        objects[obj.name] = {
            "type": obj.type,
            "geometry": mesh_geometry(obj),
            "state_sha256": hashlib.sha256(
                json.dumps(state, sort_keys=True, default=oracle_property, allow_nan=False).encode()
            ).hexdigest(),
        }
    return {
        "source_sha256": source_sha256,
        "objects": objects,
        "active_objects": sorted(bpy.context.scene.objects.keys()),
        "external_libraries": len(bpy.data.libraries),
    }
