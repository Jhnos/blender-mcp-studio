"""Nine editable low-poly event badges, rendered without external fonts."""

from __future__ import annotations

import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.blender_generator_runner import run_generator  # noqa: E402
from scripts.blender_mesh_primitives import material  # noqa: E402

OUT = ROOT / "models/living-actors"


def build() -> None:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 16
    scene.render.resolution_x = scene.render.resolution_y = 64
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.world.color = (0.3, 0.3, 0.3)
    bpy.ops.object.camera_add(location=(0, 0, 6))
    camera = bpy.context.object
    camera.name = "LM_camera"
    camera.data.type, camera.data.ortho_scale = "ORTHO", 1.3
    scene.camera = camera
    bpy.ops.object.light_add(type="AREA", location=(-2, 1, 5))
    lamp = bpy.context.object
    lamp.name = "LM_light"
    lamp.data.energy, lamp.data.size = 300, 4
    lamp.rotation_euler = (-lamp.location).to_track_quat("-Z", "Y").to_euler()
    ink = material("LM_ink", (0.96, 0.91, 0.73, 1))
    colors = ((0.11, 0.14, 0.17, 1), (0.045, 0.31, 0.39, 1), (0.12, 0.34, 0.18, 1))
    all_groups = []
    for kind_index, kind in enumerate(("talk", "quest", "deliver")):
        for state in range(3):
            group = bpy.data.collections.new(f"LM_{kind}_{state}")
            scene.collection.children.link(group)
            objects: list[bpy.types.Object] = []

            def mesh(
                name: str,
                loc: tuple[float, float, float],
                dims: tuple[float, float, float],
                mat: bpy.types.Material,
                round_shape: bool = False,
                kind: str = kind,
                state: int = state,
                group: bpy.types.Collection = group,
                objects: list[bpy.types.Object] = objects,
            ) -> bpy.types.Object:
                if round_shape:
                    bpy.ops.mesh.primitive_uv_sphere_add(
                        segments=16, ring_count=8, radius=1, location=loc
                    )
                else:
                    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
                obj = bpy.context.object
                obj.name = f"LM_{kind}_{state}_{name}"
                obj.scale = dims
                obj.data.materials.append(mat)
                for old in list(obj.users_collection):
                    old.objects.unlink(obj)
                group.objects.link(obj)
                objects.append(obj)
                return obj

            mesh(
                "badge",
                (0, 0, 0),
                (0.52, 0.52, 0.09),
                material(f"LM_state{state}", colors[state]),
                True,
            )
            if kind == "talk":
                mesh("bubble", (0, 0.025, 0.105), (0.65, 0.38, 0.08), ink)
                mesh("tail", (-0.19, -0.20, 0.11), (0.12, 0.18, 0.07), ink)
                dark = material("LM_dark", (0.035, 0.065, 0.07, 1))
                for x in (-0.18, 0, 0.18):
                    mesh("dot", (x, 0.035, 0.16), (0.045, 0.045, 0.025), dark, True)
            elif kind == "quest":
                mesh("stem", (0, 0.12, 0.11), (0.14, 0.42, 0.08), ink)
                mesh("dot", (0, -0.25, 0.12), (0.10, 0.10, 0.06), ink, True)
            else:
                mesh("parcel", (0, 0, 0.11), (0.59, 0.44, 0.08), ink)
                mesh(
                    "ribbon-v",
                    (0, 0, 0.17),
                    (0.065, 0.47, 0.03),
                    material("LM_ribbon", (0.25, 0.13, 0.03, 1)),
                )
                mesh("ribbon-h", (0, 0, 0.17), (0.62, 0.065, 0.03), bpy.data.materials["LM_ribbon"])
            # State is encoded by both shape and color: dot/diamond/check in the corner.
            if state == 0:
                mesh("unavailable", (0.34, -0.34, 0.22), (0.22, 0.045, 0.035), ink)
            elif state == 1:
                dot = mesh("available", (0.34, -0.34, 0.22), (0.13, 0.13, 0.035), ink)
                dot.rotation_euler.z = 0.7854
            else:
                tick = mesh("check-short", (0.29, -0.36, 0.22), (0.06, 0.16, 0.035), ink)
                tick.rotation_euler.z = 0.7
                tick = mesh("check-long", (0.39, -0.33, 0.22), (0.06, 0.27, 0.035), ink)
                tick.rotation_euler.z = -0.6
            scene.render.filepath = str(OUT / "markers" / f"{kind_index * 3 + state:02d}.png")
            bpy.ops.render.render(write_still=True)
            for obj in objects:
                obj.hide_render = True
            all_groups.append(group)
    for i, group in enumerate(all_groups):
        for obj in group.objects:
            obj.location += Vector(((i % 3) * 1.5, (i // 3) * 1.5, 0))
            obj.hide_render = False
    camera.location = Vector((1.5, 1.5, 6))
    camera.data.ortho_scale = 5
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.filepath = str(OUT / "markers-preview.png")
    bpy.ops.render.render(write_still=True)
    scene.render.filepath = "//markers-preview.png"
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "living-markers.blend"))
    print("LIVING_MARKERS_GENERATED", 9)


if __name__ == "__main__":
    run_generator(build, prefix="LM_")
