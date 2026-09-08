"""Generate world-kit source, sprites and assembled examples with real Blender."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.blender_generator_runner import run_generator  # noqa: E402
from scripts.model_universal_room import PALETTES  # noqa: E402
from scripts.model_universal_room import build_prop as room_prop  # noqa: E402
from scripts.world_kit_geometry import FAMILIES, LABELS, STATE_PAIRS, build_prop  # noqa: E402

OUT = ROOT / "models/world-kit"


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "AgX"
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.16, 0.19, 0.23, 1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    bpy.ops.object.camera_add(location=(0, -8, 12))
    camera = bpy.context.object
    camera.name = "WK_camera"
    camera.data.type = "ORTHO"
    scene.camera = camera
    lights = []
    for name, loc, power in [("key", (-3, -4, 7), 800), ("fill", (4, 2, 5), 500)]:
        bpy.ops.object.light_add(type="AREA", location=loc)
        lamp = bpy.context.object
        lamp.name = "WK_" + name
        lamp.data.energy = power
        lamp.data.size = 5
        lamp.rotation_euler = (-lamp.location).to_track_quat("-Z", "Y").to_euler()
        lights.append(lamp)
    groups = {
        (p, k): build_prop(k, p) for p in PALETTES for names in FAMILIES.values() for k in names
    }
    floors = {p: room_prop("floor", p) for p in PALETTES}
    for g in [*groups.values(), *floors.values()]:
        for o in g.objects:
            o.hide_render = True
    assets = []
    for (palette, kind), group in groups.items():
        category = next(f for f, names in FAMILIES.items() if kind in names)
        target = OUT / palette
        target.mkdir(exist_ok=True)
        camera.rotation_euler = Vector((0, 8, -12)).to_track_quat("-Z", "Y").to_euler()
        up = camera.rotation_euler.to_matrix() @ Vector((0, 1, 0))
        camera.location = Vector((0, -8, 12)) + up * 0.75
        camera.data.ortho_scale = 3
        scene.render.resolution_x = 128
        scene.render.resolution_y = 192
        scene.render.film_transparent = True
        for o in group.objects:
            o.hide_render = False
        scene.render.filepath = str(target / (kind + ".png"))
        bpy.ops.render.render(write_still=True)
        bpy.context.view_layer.update()
        vertices = [o.matrix_world @ Vector(v) for o in group.objects for v in o.bound_box]
        dims = [
            round(max(v[i] for v in vertices) - min(v[i] for v in vertices), 4) for i in range(3)
        ]
        assets.append(
            {
                "id": kind,
                "label": LABELS[kind],
                "palette": palette,
                "family": category,
                "frame": FAMILIES[category].index(kind) + 1,
                "collection": group.name,
                "dimensions_m": dims,
                "anchor": [0.5, 0.75],
            }
        )
        for o in group.objects:
            o.hide_render = True
    # Each family is assembled around a clear central walkway; alternate states sit to the right.
    sprite_camera = camera.copy()
    sprite_camera.data = camera.data.copy()
    sprite_camera.name = "WK_sprite_camera"
    scene.collection.objects.link(sprite_camera)
    layouts = {}
    for palette in PALETTES:
        for category, names in FAMILIES.items():
            assembly = bpy.data.collections.new("WK_scene_" + palette + "_" + category)
            scene.collection.children.link(assembly)
            placements: list[tuple[str, tuple[float, float, float]]] = [
                ("floor", (x, y, 0)) for x in range(6) for y in range(6)
            ]
            positions = [
                (0.6, 4.5, 0),
                (2.5, 4.5, 0),
                (4.5, 4.5, 0),
                (0.6, 2.5, 0),
                (4.5, 2.5, 0),
                (0.6, 0.5, 0),
                (2.5, 0.5, 0),
                (4.5, 0.5, 0),
                (4.5, 1.5, 0),
            ]
            placements += list(zip(names, positions, strict=False))
            layouts[category] = [
                {"id": k, "position_m": list(pos)} for k, pos in placements if k != "floor"
            ]
            for i, (kind, pos) in enumerate(placements):
                source = floors[palette] if kind == "floor" else groups[(palette, kind)]
                for original in source.objects:
                    obj = original.copy()
                    obj.name = f"WK_scene_{i}_{kind}"
                    obj.location += Vector(pos)
                    obj.hide_render = False
                    assembly.objects.link(obj)
            center = Vector((2.5, 2.5, 0.45))
            camera.location = center + Vector((5, -9, 12))
            camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
            camera.data.ortho_scale = 9.5
            scene.render.resolution_x = 1200
            scene.render.resolution_y = 1000
            scene.render.film_transparent = False
            for lamp, delta in zip(lights, [(-3, -4, 7), (4, 2, 5)], strict=True):
                lamp.location = center + Vector(delta)
                lamp.rotation_euler = (center - lamp.location).to_track_quat("-Z", "Y").to_euler()
                lamp.data.energy = 1300
            scene.render.filepath = str(OUT / f"{palette}-{category}.png")
            bpy.ops.render.render(write_still=True)
            scene.render.filepath = f"//{palette}-{category}.png"
            for source in [*groups.values(), *floors.values()]:
                for obj in source.objects:
                    obj.hide_viewport = True
            bpy.ops.wm.save_as_mainfile(filepath=str(OUT / f"{palette}-{category}.blend"))
            for source in [*groups.values(), *floors.values()]:
                for obj in source.objects:
                    obj.hide_viewport = False
            for obj in list(assembly.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(assembly)
    for group in floors.values():
        for obj in list(group.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(group)
    for palette_index, palette in enumerate(PALETTES):
        for i, asset in enumerate(a for a in assets if a["palette"] == palette):
            offset = Vector(((i % 8) * 2, (i // 8) * 2.5 + palette_index * 9, 0))
            group = groups[(palette, asset["id"])]
            group.instance_offset = offset
            asset["catalog_offset_m"] = list(offset)
            for obj in group.objects:
                obj.location += offset
                obj.hide_render = False
    center = Vector((7, 7, 0))
    camera.location = center + Vector((5, -15, 22))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = 25
    scene.render.filepath = "//world-kit.png"
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                view = area.spaces.active.region_3d
                view.view_location = center
                view.view_distance = 25
                view.view_rotation = camera.rotation_euler.to_quaternion()
    manifest = {
        "version": "1.0.0",
        "units": "metres",
        "tile_pixels": 64,
        "frame_size": [128, 192],
        "anchor": [0.5, 0.75],
        "model_count": 18,
        "families": FAMILIES,
        "state_pairs": STATE_PAIRS,
        "assets": assets,
        "layouts": layouts,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "world-kit.blend"))
    print("WORLD_KIT_GENERATED", len(assets))


if __name__ == "__main__":
    run_generator(build, prefix="WK_")
