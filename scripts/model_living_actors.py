"""Render the first actor slice using the delivered World Kit orthographic camera."""

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
from scripts.living_actor_geometry import build_actor  # noqa: E402
from scripts.living_asset_contract import CLIPS, DIRECTIONS, actor_spec  # noqa: E402

OUT = ROOT / "models/living-actors"


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "AgX"
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.16, 0.19, 0.23, 1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    # Append the actual delivered camera, not an approximation reconstructed from a name.
    with bpy.data.libraries.load(str(ROOT / "models/world-kit/world-kit.blend")) as (_, target):
        target.objects = ["WK_sprite_camera"]
    camera = target.objects[0]
    scene.collection.objects.link(camera)
    camera.name = "LW_sprite_camera"
    scene.camera = camera
    portrait_camera = camera.copy()
    portrait_camera.data = camera.data.copy()
    portrait_camera.name = "LW_portrait_camera"
    scene.collection.objects.link(portrait_camera)
    portrait_camera.location = Vector((0, 0, 1.37)) + Vector((0, -8, 12))
    portrait_camera.data.ortho_scale = 1.55
    for name, pos, energy in (("key", (-3, -4, 7), 800), ("fill", (4, 2, 5), 500)):
        bpy.ops.object.light_add(type="AREA", location=pos)
        obj = bpy.context.object
        obj.name = "LW_" + name
        obj.data.energy, obj.data.size = energy, 5
        obj.rotation_euler = (-obj.location).to_track_quat("-Z", "Y").to_euler()
    actors = {role: build_actor(role) for role in ("traveler", "guide")}
    specs = []
    for role, (rig, group) in actors.items():
        for _, other in actors.values():
            for obj in other.objects:
                obj.hide_render = other != group
        scene.render.resolution_x, scene.render.resolution_y = 128, 192
        for di, _direction in enumerate(DIRECTIONS):
            rig.rotation_euler.z = (0, -math.pi / 2, math.pi / 2, math.pi)[di]
            offset = di * 12
            for clip, (count, fps) in CLIPS.items():
                rig.animation_data.action = bpy.data.actions[f"LW_{role}_{clip}"]
                scene.render.fps = fps
                for frame in range(1, count + 1):
                    scene.frame_set(frame)
                    scene.render.filepath = str(OUT / role / f"{offset + frame - 1:02d}.png")
                    bpy.ops.render.render(write_still=True)
                offset += count
        rig.rotation_euler.z = 0
        rig.animation_data.action = bpy.data.actions[f"LW_{role}_idle"]
        scene.frame_set(1)
        scene.camera = portrait_camera
        scene.render.resolution_x = scene.render.resolution_y = 256
        scene.render.filepath = str(OUT / (role + "-portrait.png"))
        bpy.ops.render.render(write_still=True)
        scene.camera = camera
        specs.append(actor_spec(role, "旅人" if role == "traveler" else "嚮導"))
    for _rig, group in actors.values():
        for obj in group.objects:
            obj.hide_render = False
    # Catalog presentation uses translated roots; source frames always use origin zero.
    actors["traveler"][0].location.x = -0.55
    actors["guide"][0].location.x = 0.55
    scene.render.resolution_x, scene.render.resolution_y = 768, 768
    camera.data.ortho_scale = 3.5
    scene.render.filepath = str(OUT / "actors-preview.png")
    bpy.ops.render.render(write_still=True)
    camera.data.ortho_scale = 3
    scene.render.resolution_x, scene.render.resolution_y = 128, 192
    scene.render.filepath = "//actors-preview.png"
    scene.frame_start, scene.frame_end = 1, 6
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                view = area.spaces.active.region_3d
                view.view_location = Vector((0, 0, 0.9))
                view.view_distance = 4
                view.view_rotation = camera.rotation_euler.to_quaternion()
    (OUT / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "content_version": "1.0.0",
                "tile_pixels": 64,
                "camera_source": "world-kit.blend:WK_sprite_camera",
                "actors": specs,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "living-actors.blend"))
    print("LIVING_ACTORS_GENERATED", len(specs) * 48)


if __name__ == "__main__":
    run_generator(build, prefix="LW_")
