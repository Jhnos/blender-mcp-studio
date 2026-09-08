"""Build editable metre-scale game props and orthographic sprites in isolated Blender.

Run: Blender --background --factory-startup --python scripts/model_universal_room.py
Uses the existing namespaced generator wrapper; never touches the live addon scene.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.blender_generator_runner import run_generator  # noqa: E402
from scripts.blender_mesh_primitives import material, move_to_collection  # noqa: E402
from scripts.universal_room_presentation import present_map  # noqa: E402

OUT = ROOT / "models" / "universal-room"
NAMES = (
    "floor",
    "wall",
    "corner",
    "doorframe",
    "door_closed",
    "table",
    "chair",
    "chest_closed",
    "cabinet",
    "shelf",
    "lamp",
    "noticeboard",
    "door_open",
    "chest_open",
    "wall_side",
)
PALETTES = {
    "wood-stone": (
        (0.30, 0.16, 0.075, 1),
        (0.16, 0.21, 0.23, 1),
        (0.65, 0.40, 0.13, 1),
        (0.075, 0.095, 0.105, 1),
    ),
    "metal": (
        (0.16, 0.25, 0.31, 1),
        (0.07, 0.12, 0.17, 1),
        (0.12, 0.68, 0.70, 1),
        (0.035, 0.06, 0.08, 1),
    ),
}


def build_prop(kind: str, palette: str) -> bpy.types.Collection:
    group = bpy.data.collections.new("UR_" + palette + "_" + kind)
    bpy.context.scene.collection.children.link(group)
    colors = PALETTES[palette]
    mats = [
        material("UR_" + palette + str(i), color, 0.55 if palette == "metal" else 0.08)
        for i, color in enumerate(colors)
    ]
    mats.append(material("UR_paper", (0.78, 0.72, 0.50, 1)))

    def box(
        name: str,
        loc: tuple[float, float, float],
        size: tuple[float, float, float],
        mat: int = 0,
        angle: float = 0,
    ) -> bpy.types.Object:
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        o = bpy.context.object
        o.name = "UR_" + palette + "_" + kind + "_" + name
        o.dimensions = size
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        o.rotation_euler.z = angle
        o.data.materials.append(mats[mat])
        bevel = o.modifiers.new("Soft manufactured edges", "BEVEL")
        bevel.width = 0.016
        bevel.segments = 1
        o.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
        move_to_collection(o, group)
        return o

    if kind == "floor":
        box("base", (0, 0, -0.04), (1, 1, 0.08), 1)
        for x in (-0.25, 0.25):
            for y in (-0.25, 0.25):
                box("tile", (x, y, 0.004), (0.485, 0.485, 0.02), 1)
    elif kind in ("wall", "corner", "wall_side"):
        box("wall", (0, 0.36, 0.65), (1, 0.22, 1.3), 1)
        box("cap", (0, 0.36, 1.32), (1.02, 0.26, 0.08), 2)
        for x in (-0.42, 0.42):
            box("post", (x, 0.36, 0.7), (0.075, 0.26, 1.45))
        if kind == "corner":
            box("return", (-0.36, 0, 0.65), (0.22, 1, 1.3), 1)
            box("returncap", (-0.36, 0, 1.32), (0.26, 1, 0.08), 2)
    elif kind == "doorframe":
        for x in (-0.43, 0.43):
            box("jamb", (x, 0, 0.95), (0.14, 0.24, 1.9), 1)
        box("lintel", (0, 0, 1.88), (1, 0.26, 0.18), 2)
    elif kind.startswith("door_"):
        angle = -math.pi / 2 if kind.endswith("open") else 0

        def doorpart(
            name: str,
            loc: tuple[float, float, float],
            size: tuple[float, float, float],
            mat: int = 0,
        ) -> None:
            x, y, z = loc
            x, y = (
                -0.38 + (x + 0.38) * math.cos(angle) - y * math.sin(angle),
                (x + 0.38) * math.sin(angle) + y * math.cos(angle),
            )
            box(name, (x, y, z), size, mat, angle)

        doorpart("leaf", (0, 0, 0.83), (0.76, 0.09, 1.65))
        for z in (0.18, 1.45):
            doorpart("strap", (0, -0.056, z), (0.76, 0.04, 0.07), 2)
        doorpart("handle", (0.25, -0.10, 0.82), (0.075, 0.09, 0.12), 2)
    elif kind in ("table", "chair"):
        chair = kind == "chair"
        width = 0.55 if chair else 0.95
        depth = 0.55 if chair else 0.72
        height = 0.48 if chair else 0.78
        box("top", (0, 0, height), (width, depth, 0.09))
        for x in (-width * 0.37, width * 0.37):
            for y in (-depth * 0.34, depth * 0.34):
                box("leg", (x, y, height / 2), (0.07, 0.07, height), 1)
        if chair:
            box("back", (0, 0.24, 0.8), (0.55, 0.08, 0.6))
            box("backtrim", (0, 0.24, 1.1), (0.57, 0.10, 0.06), 2)
        else:
            box("runner", (0, 0, height + 0.055), (0.34, 0.70, 0.012), 2)
            box("paper", (0.1, -0.12, height + 0.07), (0.24, 0.22, 0.012), 4)
    elif kind.startswith("chest_"):
        box("bottom", (0, 0, 0.12), (0.78, 0.56, 0.10), 1)
        for x in (-0.36, 0.36):
            box("side", (x, 0, 0.31), (0.08, 0.56, 0.38))
        for y in (-0.24, 0.24):
            box("side", (0, y, 0.31), (0.78, 0.08, 0.38))
        box("interior", (0, 0, 0.15), (0.60, 0.40, 0.03), 3)
        opened = kind.endswith("open")
        lid = box("lid", (0, 0.26, 0.72) if opened else (0, 0, 0.54), (0.80, 0.58, 0.10))
        if opened:
            lid.rotation_euler.x = math.radians(-75)
        for x in (-0.24, 0.24):
            box("band", (x, -0.289, 0.32), (0.065, 0.035, 0.38), 2)
        box("latch", (0, -0.31, 0.42), (0.12, 0.035, 0.12), 2)
    elif kind in ("cabinet", "shelf"):
        for x in (-0.38, 0.38):
            box("side", (x, 0, 0.8), (0.08, 0.52, 1.6))
        box("back", (0, 0.24, 0.8), (0.78, 0.06, 1.6), 1)
        for z in (0.08, 0.62, 1.12, 1.62):
            box("shelf", (0, 0, z), (0.82, 0.55, 0.07))
        if kind == "cabinet":
            for x in (-0.19, 0.19):
                box("door", (x, -0.28, 0.85), (0.35, 0.06, 1.4))
                box("knob", (x * 0.3, -0.33, 0.82), (0.05, 0.045, 0.06), 2)
        else:
            for x, z in ((-0.19, 0.8), (0.17, 1.29), (0.23, 0.25)):
                box("parcel", (x, -0.02, z), (0.23, 0.29, 0.26), 2)
    elif kind == "lamp":
        box("foot", (0, 0, 0.045), (0.4, 0.4, 0.09), 1)
        box("stem", (0, 0, 0.64), (0.055, 0.055, 1.2), 2)
        box("lantern", (0, 0, 1.34), (0.30, 0.30, 0.35), 4)
        for z in (1.15, 1.54):
            box("rim", (0, 0, z), (0.38, 0.38, 0.065), 2)
        for x in (-0.15, 0.15):
            for y in (-0.15, 0.15):
                box("cage", (x, y, 1.34), (0.035, 0.035, 0.35), 1)
    elif kind == "noticeboard":
        for x in (-0.28, 0.28):
            box("leg", (x, 0, 0.6), (0.075, 0.10, 1.2), 1)
        box("board", (0, 0, 1.2), (0.9, 0.10, 0.62))
        for x in (-0.43, 0.43):
            box("trim", (x, -0.06, 1.2), (0.045, 0.03, 0.64), 2)
        for x, z in ((-0.20, 1.24), (0.15, 1.15)):
            box("note", (x, -0.066, z), (0.25, 0.012, 0.31), 4)
    if kind == "wall_side":
        for obj in group.objects:
            x, y, z = obj.location
            obj.location = (-y, x, z)
            obj.rotation_euler.z += math.pi / 2
    return group


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 16
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.16, 0.19, 0.23, 1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    scene.view_settings.view_transform = "AgX"
    bpy.ops.object.camera_add(location=(0, -8, 12))
    camera = bpy.context.object
    camera.name = "UR_camera"
    camera.rotation_euler = (
        (Vector((0, 0, 0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    camera.data.type = "ORTHO"
    scene.camera = camera
    for name, loc, power, size in [("key", (-3, -4, 7), 800, 5), ("fill", (4, 2, 5), 500, 4)]:
        bpy.ops.object.light_add(type="AREA", location=loc)
        lamp = bpy.context.object
        lamp.name = "UR_" + name
        lamp.data.energy = power
        lamp.data.shape = "DISK"
        lamp.data.size = size
        lamp.rotation_euler = (-lamp.location).to_track_quat("-Z", "Y").to_euler()
    groups = {(p, k): build_prop(k, p) for p in PALETTES for k in NAMES}
    assets: list[dict[str, object]] = []
    manifest: dict[str, object] = {
        "version": "1.0.0",
        "units": "metres",
        "tile_pixels": 64,
        "frame_size": [128, 192],
        "anchor": [0.5, 0.75],
        "assets": assets,
    }
    for group in groups.values():
        for obj in group.objects:
            obj.hide_render = True
    for (palette, kind), group in groups.items():
        target = OUT / palette
        target.mkdir(exist_ok=True)
        for obj in group.objects:
            obj.hide_render = False
        scene.render.resolution_x = 128
        scene.render.resolution_y = 192
        scene.render.resolution_percentage = 100
        camera.data.ortho_scale = 3
        # Shift target along camera-up so the metre-grid footpoint is pixel (64,144).
        camera.rotation_euler = (
            (Vector((0, 0, 0)) - Vector((0, -8, 12))).to_track_quat("-Z", "Y").to_euler()
        )
        up = camera.rotation_euler.to_matrix() @ Vector((0, 1, 0))
        camera.location = Vector((0, -8, 12)) + up * 0.75
        if kind == "floor":
            camera.location = (0, 0, 10)
            camera.rotation_euler = (0, 0, 0)
            camera.data.ortho_scale = 1
            scene.render.resolution_x = 64
            scene.render.resolution_y = 64
        else:
            camera.rotation_euler = (
                (Vector((0, 0, 0)) - Vector((0, -8, 12))).to_track_quat("-Z", "Y").to_euler()
            )
        scene.render.filepath = str(target / (kind + ".png"))
        bpy.ops.render.render(write_still=True)
        bpy.context.view_layer.update()
        vertices = [
            obj.matrix_world @ Vector(corner) for obj in group.objects for corner in obj.bound_box
        ]
        dimensions = [
            round(max(v[i] for v in vertices) - min(v[i] for v in vertices), 4) for i in range(3)
        ]
        assets.append(
            {
                "id": kind,
                "palette": palette,
                "frame": NAMES.index(kind),
                "dimensions_m": dimensions,
                "collection": group.name,
            }
        )
        for obj in group.objects:
            obj.hide_render = True
    present_map(groups, NAMES, OUT)
    # Editable catalogue arranged by variant; save with clean visible source geometry.
    for (palette, kind), group in groups.items():
        index = NAMES.index(kind)
        offset = Vector(
            ((index % 7) * 2.2, (index // 7) * 3.0 + (0 if palette == "wood-stone" else 7), 0)
        )
        group.instance_offset = offset
        for obj in group.objects:
            obj.location += offset
            obj.hide_render = False
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 900
    scene.render.film_transparent = False
    for palette in PALETTES:
        for (p, _k), group in groups.items():
            for obj in group.objects:
                obj.hide_render = p != palette
        center = Vector((6.5, 1.5 + (0 if palette == "wood-stone" else 7), 0.4))
        for name, delta in [("key", (-3, -4, 7)), ("fill", (4, 2, 5))]:
            lamp = bpy.data.objects["UR_" + name]
            lamp.location = center + Vector(delta)
            lamp.rotation_euler = (center - lamp.location).to_track_quat("-Z", "Y").to_euler()
            lamp.data.energy = 1800
        camera.location = center + Vector((5, -11, 15))
        camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.ortho_scale = 17
        scene.render.filepath = str(OUT / (palette + "-preview.png"))
        bpy.ops.render.render(write_still=True)
    for group in groups.values():
        for obj in group.objects:
            obj.hide_render = False
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    center = Vector((6.5, 5, 0.5))
    camera.location = center + Vector((5, -15, 20))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = 23
    scene.render.filepath = "//library-render.png"
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                view = area.spaces.active.region_3d
                view.view_location = center
                view.view_distance = 23
                view.view_rotation = camera.rotation_euler.to_quaternion()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "universal-room.blend"))


if __name__ == "__main__":
    run_generator(build, prefix="UR_")
