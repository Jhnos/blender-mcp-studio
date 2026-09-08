"""Assemble a saved map snapshot from the same editable module collections."""

from __future__ import annotations

import json
from pathlib import Path

import bpy
from mathutils import Vector


def present_map(
    groups: dict[tuple[str, str], bpy.types.Collection], names: tuple[str, ...], output: Path
) -> None:
    data = json.loads((output / "layout.tmj").read_text())
    scene = bpy.context.scene
    camera = scene.camera
    floor = next(layer["data"] for layer in data["layers"] if layer["name"] == "ground")
    placements = [
        ("floor", (i % data["width"], i // data["width"])) for i, value in enumerate(floor) if value
    ]
    for layer in data["layers"]:
        if layer["name"] == "decorations":
            for obj in layer["objects"]:
                frame = next(prop["value"] for prop in obj["properties"] if prop["name"] == "frame")
                placements.append((names[frame], (obj["x"] / 64 - 0.5, obj["y"] / 64 - 0.5)))
    assembly = bpy.data.collections.new("UR_warehouse")
    scene.collection.children.link(assembly)
    for index, (kind, (col, row)) in enumerate(placements):
        for source in groups[("wood-stone", kind)].objects:
            obj = source.copy()
            obj.name = f"UR_map_{index}_{kind}"
            obj.location += Vector((col, -row, 0))
            obj.hide_render = False
            assembly.objects.link(obj)
    center = Vector((9.5, -5.5, 0))
    camera.location = center + Vector((0, -12, 20))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = 24
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1050
    scene.render.film_transparent = False
    for name, delta in [("key", (-4, -3, 10)), ("fill", (6, 4, 8))]:
        lamp = bpy.data.objects["UR_" + name]
        lamp.location = center + Vector(delta)
        lamp.rotation_euler = (center - lamp.location).to_track_quat("-Z", "Y").to_euler()
        lamp.data.energy = 2500
        lamp.data.size = 10
    scene.render.filepath = str(output / "warehouse-preview.png")
    bpy.ops.render.render(write_still=True)
    scene.render.filepath = "//warehouse-preview.png"
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "warehouse.blend"))
    for obj in list(assembly.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(assembly)
