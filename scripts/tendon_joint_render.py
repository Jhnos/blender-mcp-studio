"""Blender presentation adapter for the tendon-joint concept generator."""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from src.core.domain.tendon_joint import TendonJointSpec


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
    obj.data.materials.clear()
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
    spec: TendonJointSpec,
    floor_material: bpy.types.Material,
    assign_material: Callable[[bpy.types.Object, bpy.types.Material], None],
) -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 1100
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
    shading.background_color = (0.018, 0.026, 0.045)
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = "WORLD"
    shading.curvature_ridge_factor = 1.6
    shading.curvature_valley_factor = 1.2
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    if background is not None:
        background.inputs["Color"].default_value = (0.012, 0.018, 0.03, 1.0)
        background.inputs["Strength"].default_value = 0.08

    bpy.ops.mesh.primitive_plane_add(size=m(260.0), location=(0.0, 0.0, m(-5.0)))
    floor = bpy.context.object
    floor.name = "TJ_FLOOR"
    assign_material(floor, floor_material)

    bpy.ops.object.camera_add(location=(m(115.0), m(-145.0), m(90.0)))
    camera = bpy.context.object
    camera.name = "TJ_CAMERA"
    camera.data.lens = 58
    look_at(camera, (0.0, 0.0, spec.assembled_height_mm * 0.48))
    scene.camera = camera

    lights: list[bpy.types.Object] = []
    for name, energy, size_mm, location_mm in (
        ("TJ_KEY", 24.0, 85.0, (70.0, -80.0, 130.0)),
        ("TJ_FILL", 12.0, 70.0, (-90.0, -20.0, 75.0)),
        ("TJ_RIM", 18.0, 60.0, (35.0, 95.0, 120.0)),
    ):
        bpy.ops.object.light_add(type="AREA", location=tuple(m(value) for value in location_mm))
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = m(size_mm)
        look_at(light, (0.0, 0.0, 35.0))
        lights.append(light)
    return camera, [floor, *lights]


def duplicate_print_layout(
    parts: list[bpy.types.Object],
    target: bpy.types.Collection,
) -> list[bpy.types.Object]:
    positions = (
        (-52.0, -30.0),
        (0.0, -30.0),
        (52.0, -30.0),
        (-25.0, 34.0),
        (25.0, 34.0),
    )
    copies: list[bpy.types.Object] = []
    for source, position in zip(parts, positions, strict=True):
        copy = source.copy()
        copy.data = source.data.copy()
        copy.name = source.name.replace("TJ_PRINTABLE", "TJ_LAYOUT")
        target.objects.link(copy)
        rotation = (
            Matrix.Rotation(math.pi, 4, "X")
            if source.name.endswith("DISC_2_TIP")
            else Matrix.Identity(4)
        )
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
    guides: bpy.types.Collection,
    labels: list[bpy.types.Object],
    layout_objects: list[bpy.types.Object],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene

    for label in labels:
        face_camera(label, camera)
    scene.render.filepath = str(output_dir / "tendon_joint_4dof_assembly.png")
    bpy.ops.render.render(write_still=True)

    for obj in assembly_objects:
        obj.hide_render = True
    for obj in guides.objects:
        obj.hide_render = True
    for obj in labels:
        obj.hide_render = True
    for obj in layout_objects:
        obj.hide_render = False

    camera.location = (0.0, 0.0, m(225.0))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = m(225.0)
    look_at(camera, (0.0, 0.0, 0.0))
    scene.display.shading.show_shadows = False
    scene.render.resolution_x = 1300
    scene.render.resolution_y = 850
    scene.render.filepath = str(output_dir / "tendon_joint_4dof_print_layout.png")
    bpy.ops.render.render(write_still=True)

    for obj in assembly_objects:
        obj.hide_render = False
    for obj in guides.objects:
        obj.hide_render = False
    for obj in labels:
        obj.hide_render = False
    for obj in layout_objects:
        obj.hide_render = True
    scene.display.shading.show_shadows = True
