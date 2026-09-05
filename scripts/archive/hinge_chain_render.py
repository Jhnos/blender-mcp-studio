"""Blender presentation adapter for the bearing-ready hinge-chain concept."""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from src.core.domain.hinge_chain import HingePhalanxSpec


def m(value_mm: float) -> float:
    return value_mm / 1000.0


def add_text(
    name: str,
    body: str,
    location_mm: tuple[float, float, float],
    text_material: bpy.types.Material,
    size_mm: float = 4.0,
) -> bpy.types.Object:
    bpy.ops.object.text_add(location=tuple(m(value) for value in location_mm))
    obj = bpy.context.object
    obj.name = name
    obj.data.body = body
    obj.data.align_x = "CENTER"
    obj.data.size = m(size_mm)
    obj.data.extrude = m(0.15)
    obj.data.materials.append(text_material)
    obj.hide_viewport = True
    return obj


def look_at(obj: bpy.types.Object, target_mm: tuple[float, float, float]) -> None:
    direction = Vector(tuple(m(value) for value in target_mm)) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def face_camera(obj: bpy.types.Object, camera: bpy.types.Object) -> None:
    direction = camera.location - obj.location
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()


def setup_render(
    spec: HingePhalanxSpec,
    floor_material: bpy.types.Material,
    assign_material: Callable[[bpy.types.Object, bpy.types.Material], None],
) -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 1300
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.background_type = "VIEWPORT"
    shading.background_color = (0.012, 0.018, 0.032)
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = "WORLD"
    shading.curvature_ridge_factor = 1.8
    shading.curvature_valley_factor = 1.4

    bpy.ops.mesh.primitive_plane_add(size=m(360.0), location=(0.0, 0.0, m(-32.0)))
    floor = bpy.context.object
    floor.name = "HJ_FLOOR"
    assign_material(floor, floor_material)

    assembly_midpoint = (spec.assembly_unit_count - 1) * spec.unit_pitch_mm / 2.0
    bpy.ops.object.camera_add(location=(m(190.0), m(-335.0), m(205.0)))
    camera = bpy.context.object
    camera.name = "HJ_CAMERA"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = m(285.0)
    look_at(camera, (0.0, 0.0, assembly_midpoint))
    scene.camera = camera

    lights: list[bpy.types.Object] = []
    for name, energy, size_mm, location_mm in (
        ("HJ_KEY", 28.0, 90.0, (85.0, -110.0, 230.0)),
        ("HJ_FILL", 14.0, 75.0, (-105.0, -30.0, 130.0)),
        ("HJ_RIM", 22.0, 65.0, (45.0, 105.0, 205.0)),
    ):
        bpy.ops.object.light_add(type="AREA", location=tuple(m(value) for value in location_mm))
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = m(size_mm)
        look_at(light, (0.0, 0.0, assembly_midpoint))
        lights.append(light)
    return camera, [floor, *lights]


def duplicate_print_layout(
    master: bpy.types.Object,
    target: bpy.types.Collection,
) -> list[bpy.types.Object]:
    positions = ((-46.0, 0.0), (0.0, 0.0), (46.0, 0.0))
    rotations = (
        Matrix.Rotation(math.pi / 2.0, 4, "X"),
        Matrix.Identity(4),
        Matrix.Rotation(math.pi / 2.0, 4, "Z") @ Matrix.Rotation(math.pi, 4, "X"),
    )
    copies: list[bpy.types.Object] = []
    for index, (position, rotation) in enumerate(zip(positions, rotations, strict=True), start=1):
        copy = master.copy()
        copy.data = master.data
        copy.name = f"HJ_LAYOUT_PHALANX_{index}"
        target.objects.link(copy)
        rotated_z = [(rotation @ vertex.co).z for vertex in copy.data.vertices]
        bed_z = -min(rotated_z)
        copy.matrix_world = (
            Matrix.Translation(Vector((m(position[0]), m(position[1]), bed_z))) @ rotation
        )
        copy.hide_render = True
        copy.hide_viewport = True
        copies.append(copy)
    bpy.context.view_layer.update()
    return copies


def render_views(
    output_dir: Path,
    camera: bpy.types.Object,
    assembly_objects: list[bpy.types.Object],
    hardware: bpy.types.Collection,
    labels: list[bpy.types.Object],
    layout_objects: list[bpy.types.Object],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene

    for label in labels:
        face_camera(label, camera)
    scene.render.filepath = str(output_dir / "hinge_chain_assembly.png")
    bpy.ops.render.render(write_still=True)

    for obj in assembly_objects:
        obj.hide_render = True
    for obj in hardware.objects:
        obj.hide_render = True
    for obj in labels:
        obj.hide_render = True
    for obj in layout_objects:
        obj.hide_render = False

    camera.location = (0.0, m(-205.0), m(145.0))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = m(125.0)
    look_at(camera, (0.0, 0.0, 22.0))
    scene.display.shading.show_shadows = False
    scene.render.resolution_x = 1300
    scene.render.resolution_y = 850
    scene.render.filepath = str(output_dir / "hinge_chain_print_layout.png")
    bpy.ops.render.render(write_still=True)

    for obj in assembly_objects:
        obj.hide_render = False
    for obj in hardware.objects:
        obj.hide_render = False
    for obj in labels:
        obj.hide_render = False
    for obj in layout_objects:
        obj.hide_render = True
    scene.display.shading.show_shadows = True
