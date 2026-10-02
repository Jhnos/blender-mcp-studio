"""Deterministic editable mesh effects; eight frames per one-shot, no particle simulation."""

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
from scripts.living_asset_contract import EFFECT_KINDS, feedback_catalog  # noqa: E402

OUT = ROOT / "models/living-effects"


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_percentage = 100
    scene.render.resolution_x = scene.render.resolution_y = 128
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.render.fps = 12
    scene.frame_start, scene.frame_end = 1, 8
    scene.view_settings.view_transform = "AgX"
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5
    with bpy.data.libraries.load(str(ROOT / "models/world-kit/world-kit.blend")) as (_, target):
        target.objects = ["WK_sprite_camera"]
    camera = target.objects[0]
    camera.name = "LF_camera"
    camera.data.ortho_scale = 2.1
    camera.location = Vector((0, 0, 0.25)) + camera.rotation_euler.to_matrix() @ Vector((0, 0, 10))
    scene.collection.objects.link(camera)
    scene.camera = camera
    bpy.ops.object.light_add(type="AREA", location=(-2, -3, 6))
    lamp = bpy.context.object
    lamp.name = "LF_light"
    lamp.data.energy, lamp.data.size = 500, 4
    lamp.rotation_euler = (-lamp.location).to_track_quat("-Z", "Y").to_euler()
    colors = (
        (0.95, 0.55, 0.06, 1),
        (0.03, 0.65, 0.42, 1),
        (0.90, 0.65, 0.10, 1),
        (0.40, 0.26, 0.12, 1),
        (0.45, 0.08, 0.8, 1),
        (0.8, 0.04, 0.07, 1),
    )
    for kind, color in zip(EFFECT_KINDS, colors, strict=True):
        group = bpy.data.collections.new("LF_" + kind)
        scene.collection.children.link(group)
        root = bpy.data.objects.new("LF_" + kind + "_root", None)
        root["asset_id"] = kind
        group.objects.link(root)
        mat = material("LF_" + kind, color)
        shader = mat.node_tree.nodes["Principled BSDF"]
        shader.inputs["Emission Color"].default_value = color
        shader.inputs["Emission Strength"].default_value = 0.35 if kind == "footsteps" else 0.8
        count = {
            "pickup": 7,
            "unlock": 5,
            "complete": 10,
            "footsteps": 6,
            "teleport": 10,
            "blocked": 6,
        }[kind]
        for index in range(count):
            ring = (kind == "unlock" and index == 0) or (kind == "teleport" and index < 2)
            if ring:
                bpy.ops.mesh.primitive_torus_add(
                    major_segments=24, minor_segments=6, major_radius=0.4, minor_radius=0.028
                )
            elif kind in ("pickup", "teleport"):
                bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1)
            elif kind == "footsteps":
                bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1)
            else:
                bpy.ops.mesh.primitive_cube_add(size=1)
            obj = bpy.context.object
            obj.name = f"LF_{kind}_{index:02d}"
            obj.parent = root
            obj.data.materials.append(mat)
            move_to_collection(obj, group)
            angle = index * math.tau / count
            for frame in range(1, 9):
                t = (frame - 1) / 7
                obj.rotation_euler = (0, 0, angle)
                if kind == "pickup":
                    theta = angle + t * 0.9
                    radius = 0.19 + t * 0.17
                    obj.location = (
                        math.cos(theta) * radius,
                        math.sin(theta) * radius,
                        0.06 + t * 0.65,
                    )
                    obj.scale = (0.09 * (1 - t * 0.65),) * 3
                elif kind == "unlock":
                    if ring:
                        obj.location = (0, 0, 0.05)
                        obj.scale = (0.45 + t * 0.9,) * 3
                    else:
                        theta = (index - 1) * math.pi / 2
                        radius = 0.24 + t * 0.35
                        obj.location = (math.cos(theta) * radius, math.sin(theta) * radius, 0.09)
                        obj.scale = (0.09, 0.09, 0.055)
                        obj.rotation_euler.z = theta + math.pi / 4
                elif kind == "complete":
                    if index < 2:
                        growth = 0.5 + 0.5 * t
                        start, end = (
                            ((-0.18, 0), (-0.05, -0.12))
                            if index == 0
                            else ((-0.05, -0.12), (0.2, 0.2))
                        )
                        dx, dy = end[0] - start[0], end[1] - start[1]
                        obj.location = (
                            (start[0] + end[0]) * 0.5 * growth,
                            (start[1] + end[1]) * 0.5 * growth,
                            0.1 + index * 0.01,
                        )
                        obj.rotation_euler.z = math.atan2(-dx, dy)
                        obj.scale = (0.055 * growth, math.hypot(dx, dy) * growth, 0.04)
                    else:
                        theta = (index - 2) * math.tau / 8
                        radius = 0.32 + t * 0.28
                        obj.location = (math.cos(theta) * radius, math.sin(theta) * radius, 0.07)
                        obj.rotation_euler.z = theta
                        obj.scale = (0.13 * (1 - t * 0.4), 0.032, 0.04)
                elif kind == "footsteps":
                    obj.location = (
                        (index % 3 - 1) * (0.18 + t * 0.12),
                        (index // 3 - 0.5) * (0.16 + t * 0.12),
                        0.055 + t * 0.045,
                    )
                    obj.scale = (0.08 + t * 0.055, 0.06 + t * 0.03, 0.035 + t * 0.02)
                elif kind == "teleport":
                    if ring:
                        obj.location = (0, 0, 0.05 + index * 0.3)
                        obj.scale = (0.65 + t * 0.45,) * 3
                    else:
                        theta = angle + t * math.tau * 0.75
                        obj.location = (
                            math.cos(theta) * 0.43,
                            math.sin(theta) * 0.43,
                            0.08 + (index - 2) * 0.06 + t * 0.1,
                        )
                        obj.scale = (0.045 + t * 0.015,) * 3
                else:
                    if index < 2:
                        obj.location = (0, 0, 0.08 + index * 0.009)
                        obj.rotation_euler.z = (-1 if index == 0 else 1) * math.pi / 4
                        pulse = 0.5 + 0.35 * math.sin(math.pi * (0.1 + 0.7 * t))
                        obj.scale = (0.7 * pulse, 0.105 * pulse, 0.045)
                    else:
                        theta = (index - 2) * math.pi / 2
                        radius = 0.35 + 0.18 * t
                        obj.location = (math.cos(theta) * radius, math.sin(theta) * radius, 0.09)
                        obj.rotation_euler.z = theta
                        obj.scale = (0.10, 0.035, 0.04)
                for path in ("location", "scale", "rotation_euler"):
                    obj.keyframe_insert(data_path=path, frame=frame)
            obj.animation_data.action.name = obj.name + "_oneshot"
            obj.animation_data.action.use_fake_user = True
            obj.hide_render = True
    for kind in EFFECT_KINDS:
        for other in EFFECT_KINDS:
            for obj in bpy.data.collections["LF_" + other].objects:
                obj.hide_render = other != kind
        for frame in range(1, 9):
            scene.frame_set(frame)
            scene.render.filepath = str(OUT / kind / f"{frame - 1:02d}.png")
            bpy.ops.render.render(write_still=True)
    preview = camera.copy()
    preview.data = camera.data.copy()
    preview.name = "LF_preview_camera"
    preview.data.ortho_scale = 13.5
    scene.collection.objects.link(preview)
    for index, kind in enumerate(EFFECT_KINDS):
        bpy.data.objects[f"LF_{kind}_root"].location.x = (index - 2.5) * 2.1
        for obj in bpy.data.collections["LF_" + kind].objects:
            obj.hide_render = False
    scene.frame_set(5)
    scene.camera = preview
    scene.render.resolution_x, scene.render.resolution_y = 1536, 512
    scene.render.filepath = str(OUT / "effects-preview.png")
    bpy.ops.render.render(write_still=True)
    scene.render.filepath = "//effects-preview.png"
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "living-effects.blend"))
    (OUT / "effects.json").write_text(
        json.dumps({"schema_version": 1, "effects": feedback_catalog()["effects"]}, indent=2) + "\n"
    )
    print("LIVING_EFFECTS_GENERATED", 48)


if __name__ == "__main__":
    run_generator(build, prefix="LF_")
