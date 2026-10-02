"""Six editable low-poly props, using the delivered ground camera and shared materials."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.blender_generator_runner import run_generator  # noqa: E402
from scripts.blender_mesh_primitives import material, move_to_collection  # noqa: E402
from scripts.living_asset_contract import ITEM_KINDS, feedback_catalog  # noqa: E402

OUT = ROOT / "models/living-items"


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "AgX"
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5
    with bpy.data.libraries.load(str(ROOT / "models/world-kit/world-kit.blend")) as (_, target):
        target.objects = ["WK_sprite_camera"]
    ground = target.objects[0]
    ground.name = "LI_ground_camera"
    scene.collection.objects.link(ground)
    inventory = ground.copy()
    inventory.data = ground.data.copy()
    inventory.name = "LI_inventory_camera"
    inventory.data.ortho_scale = 1.0
    inventory.location = Vector((0, 0, 0.25)) + inventory.rotation_euler.to_matrix() @ Vector(
        (0, 0, 10)
    )
    scene.collection.objects.link(inventory)
    for label, location, energy in [("key", (-3, -4, 6), 700), ("fill", (3, 1, 5), 400)]:
        bpy.ops.object.light_add(type="AREA", location=location)
        lamp = bpy.context.object
        lamp.name = "LI_" + label + "_light"
        lamp.data.energy, lamp.data.size = energy, 4
        lamp.rotation_euler = (-lamp.location).to_track_quat("-Z", "Y").to_euler()
    mats = {
        "gold": material("LI_gold", (0.72, 0.40, 0.065, 1), 0.65),
        "paper": material("LI_paper", (0.85, 0.73, 0.47, 1)),
        "red": material("LI_red", (0.45, 0.025, 0.04, 1)),
        "blue": material("LI_blue", (0.025, 0.25, 0.44, 1)),
        "wood": material("LI_wood", (0.30, 0.12, 0.04, 1)),
        "leather": material("LI_leather", (0.20, 0.075, 0.035, 1)),
        "iron": material("LI_iron", (0.22, 0.30, 0.36, 1), 0.7),
        "string": material("LI_string", (0.62, 0.48, 0.27, 1)),
    }
    roots = {}
    for kind in ITEM_KINDS:
        group = bpy.data.collections.new("LI_" + kind)
        scene.collection.children.link(group)
        root = bpy.data.objects.new("LI_" + kind + "_root", None)
        group.objects.link(root)
        root["asset_id"] = kind
        roots[kind] = root

        def part(
            name: str,
            location: tuple[float, float, float],
            dimensions: tuple[float, float, float],
            mat: str,
            shape: str = "box",
            kind: str = kind,
            group: bpy.types.Collection = group,
            root: bpy.types.Object = root,
        ) -> bpy.types.Object:
            if shape == "sphere":
                bpy.ops.mesh.primitive_uv_sphere_add(
                    segments=12, ring_count=6, radius=0.5, location=location
                )
            elif shape == "cylinder":
                bpy.ops.mesh.primitive_cylinder_add(
                    vertices=12, radius=0.5, depth=1, location=location
                )
            elif shape == "ring":
                bpy.ops.mesh.primitive_torus_add(
                    major_segments=16,
                    minor_segments=6,
                    major_radius=0.12,
                    minor_radius=0.028,
                    location=location,
                )
            else:
                bpy.ops.mesh.primitive_cube_add(size=1, location=location)
            obj = bpy.context.object
            obj.name = f"LI_{kind}_{name}"
            if shape != "ring":
                obj.scale = dimensions
            obj.data.materials.append(mats[mat])
            obj.parent = root
            move_to_collection(obj, group)
            return obj

        if kind == "key":
            part("bow", (-0.22, 0, 0.03), (1, 1, 1), "gold", "ring")
            part("shaft", (0.04, 0, 0.03), (0.38, 0.055, 0.055), "gold")
            for i, x in enumerate((0.14, 0.22)):
                part("tooth" + str(i), (x, -0.065, 0.03), (0.04, 0.12, 0.055), "gold")
        elif kind == "letter":
            part("envelope", (0, 0, 0.025), (0.62, 0.42, 0.05), "paper")
            for x, angle in ((-0.13, -0.62), (0.13, 0.62)):
                fold = part("fold", (x, 0.05, 0.053), (0.33, 0.012, 0.006), "string")
                fold.rotation_euler.z = angle
            part("seal", (0, -0.03, 0.064), (0.10, 0.10, 0.025), "red", "cylinder")
        elif kind == "potion":
            part("bottle", (0, 0, 0.21), (0.36, 0.36, 0.42), "blue", "sphere")
            part("neck", (0, 0, 0.43), (0.15, 0.15, 0.16), "blue", "cylinder")
            part("cork", (0, 0, 0.535), (0.14, 0.14, 0.08), "wood", "cylinder")
            part("label", (0, -0.159, 0.22), (0.14, 0.035, 0.16), "paper")
            part("cross-v", (0, -0.18, 0.22), (0.026, 0.012, 0.11), "red")
            part("cross-h", (0, -0.18, 0.22), (0.085, 0.012, 0.026), "red")
        elif kind == "purse":
            part("bag", (0, 0, 0.18), (0.42, 0.34, 0.36), "leather", "sphere")
            part("neck", (0, 0, 0.36), (0.16, 0.14, 0.15), "leather", "cylinder")
            part("tie", (0, -0.02, 0.35), (0.23, 0.18, 0.055), "string", "cylinder")
            for x in (-0.05, 0.05):
                tie = part("tail", (x, -0.10, 0.27), (0.025, 0.025, 0.19), "string")
                tie.rotation_euler.y = x * 4
            part("coin", (0.06, -0.166, 0.18), (0.12, 0.025, 0.12), "gold", "sphere")
        elif kind == "tool":
            part("handle", (0, 0, 0.25), (0.085, 0.085, 0.50), "wood", "cylinder")
            part("head", (0, 0, 0.51), (0.49, 0.18, 0.18), "iron")
            part("grip", (0, 0, 0.10), (0.095, 0.095, 0.15), "leather", "cylinder")
        else:
            part("box", (0, 0, 0.21), (0.55, 0.42, 0.42), "paper")
            part("ribbon", (0, 0, 0.212), (0.055, 0.43, 0.425), "red")
            part("ribbon-cross", (0, 0, 0.216), (0.56, 0.05, 0.425), "red")
            part("tag", (0.12, -0.06, 0.44), (0.15, 0.10, 0.012), "string")
        for obj in group.objects:
            obj.hide_render = True
    for kind in ITEM_KINDS:
        for other in ITEM_KINDS:
            for obj in bpy.data.collections["LI_" + other].objects:
                obj.hide_render = other != kind
        for view, camera, size in [
            ("ground", ground, (128, 192)),
            ("inventory", inventory, (64, 64)),
        ]:
            scene.camera = camera
            scene.render.resolution_x, scene.render.resolution_y = size
            scene.render.filepath = str(OUT / f"{kind}-{view}.png")
            bpy.ops.render.render(write_still=True)
    preview = inventory.copy()
    preview.data = inventory.data.copy()
    preview.name = "LI_preview_camera"
    preview.data.ortho_scale = 6.2
    scene.collection.objects.link(preview)
    for index, (kind, root) in enumerate(roots.items()):
        root.location.x = (index - 2.5) * 0.95
        for obj in bpy.data.collections["LI_" + kind].objects:
            obj.hide_render = False
    scene.camera = preview
    scene.render.resolution_x, scene.render.resolution_y = 1536, 512
    scene.render.filepath = str(OUT / "items-preview.png")
    bpy.ops.render.render(write_still=True)
    scene.render.filepath = "//items-preview.png"
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "living-items.blend"))
    (OUT / "items.json").write_text(
        json.dumps({"schema_version": 1, "items": feedback_catalog()["items"]}, indent=2) + "\n"
    )
    print("LIVING_ITEMS_GENERATED", len(ITEM_KINDS))


if __name__ == "__main__":
    run_generator(build, prefix="LI_")
