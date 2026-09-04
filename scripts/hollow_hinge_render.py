"""Presentation adapter for the short hollow side-hinge chain."""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from src.core.domain.hollow_side_hinge import HollowSideHingeSpec
from src.core.domain.inset_hinge import InsetHingeSpec


def m(value_mm: float) -> float:
    return value_mm / 1000.0


def look_at(obj: bpy.types.Object, target_mm: tuple[float, float, float]) -> None:
    direction = Vector(tuple(m(value) for value in target_mm)) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def face_camera(obj: bpy.types.Object, camera: bpy.types.Object) -> None:
    direction = camera.location - obj.location
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()


def add_text(
    name: str,
    body: str,
    location_mm: tuple[float, float, float],
    material: bpy.types.Material,
    size_mm: float,
) -> bpy.types.Object:
    bpy.ops.object.text_add(location=tuple(m(value) for value in location_mm))
    obj = bpy.context.object
    obj.name = name
    obj.data.body = body
    obj.data.align_x = "CENTER"
    obj.data.size = m(size_mm)
    obj.data.extrude = m(0.12)
    obj.data.materials.append(material)
    obj.hide_viewport = True
    return obj


def setup_render(
    spec: HollowSideHingeSpec | InsetHingeSpec,
    floor_material: bpy.types.Material,
    assign_material: Callable[[bpy.types.Object, bpy.types.Material], None],
) -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1500
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.background_type = "VIEWPORT"
    shading.background_color = (0.008, 0.014, 0.026)
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = "WORLD"
    shading.curvature_ridge_factor = 2.0
    shading.curvature_valley_factor = 1.6

    bpy.ops.mesh.primitive_plane_add(size=m(300.0), location=(0.0, 0.0, m(-25.0)))
    floor = bpy.context.object
    floor.name = "HH_FLOOR"
    assign_material(floor, floor_material)

    midpoint = (spec.assembly_unit_count - 1) * spec.unit_pitch_mm / 2.0
    bpy.ops.object.camera_add(location=(m(145.0), m(-270.0), m(145.0)))
    camera = bpy.context.object
    camera.name = "HH_CAMERA"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = m(226.0)
    look_at(camera, (0.0, 0.0, midpoint))
    scene.camera = camera

    lights: list[bpy.types.Object] = []
    for name, energy, size_mm, location_mm in (
        ("HH_KEY", 30.0, 80.0, (90.0, -100.0, 190.0)),
        ("HH_FILL", 16.0, 70.0, (-90.0, -35.0, 100.0)),
        ("HH_RIM", 24.0, 60.0, (35.0, 95.0, 175.0)),
    ):
        bpy.ops.object.light_add(type="AREA", location=tuple(m(value) for value in location_mm))
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = m(size_mm)
        look_at(light, (0.0, 0.0, midpoint))
        lights.append(light)
    return camera, [floor, *lights]


def duplicate_print_layout(
    master: bpy.types.Object,
    target: bpy.types.Collection,
) -> list[bpy.types.Object]:
    spacing_mm = max(master.dimensions) * 1000.0 + 10.0
    positions = ((-spacing_mm, 0.0), (0.0, 0.0), (spacing_mm, 0.0))
    rotations = (
        Matrix.Rotation(math.pi / 2.0, 4, "X"),
        Matrix.Identity(4),
        Matrix.Rotation(math.pi / 2.0, 4, "Z") @ Matrix.Rotation(math.pi, 4, "X"),
    )
    copies: list[bpy.types.Object] = []
    for index, (position, rotation) in enumerate(zip(positions, rotations, strict=True), start=1):
        copy = master.copy()
        copy.data = master.data
        copy.name = f"HH_LAYOUT_MODULE_{index}"
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


def create_bent_preview(
    master: bpy.types.Object,
    target: bpy.types.Collection,
    spec: HollowSideHingeSpec | InsetHingeSpec,
    primary_material: bpy.types.Material,
    alternate_material: bpy.types.Material,
    cable_material: bpy.types.Material,
) -> tuple[list[bpy.types.Object], bpy.types.Object, tuple[float, float, float]]:
    orientation = Matrix.Identity(3)
    center = Vector((0.0, 0.0, 0.0))
    centers: list[Vector] = []
    orientations: list[Matrix] = []
    copies: list[bpy.types.Object] = []
    bend_radians = math.radians(spec.maximum_articulation_deg * 0.62)

    for index in range(spec.assembly_unit_count):
        copy = master.copy()
        copy.data = master.data
        copy.name = f"HH_BENT_MODULE_{index + 1}"
        target.objects.link(copy)
        copy.matrix_world = Matrix.Translation(center) @ orientation.to_4x4()
        copy.material_slots[0].link = "OBJECT"
        copy.material_slots[0].material = alternate_material if index % 2 else primary_material
        copy.hide_render = True
        copy.hide_viewport = True
        copies.append(copy)
        centers.append(center.copy())
        orientations.append(orientation.copy())
        if index == spec.joint_count:
            continue
        joint = center + orientation @ Vector((0.0, 0.0, m(spec.joint_center_offset_mm)))
        twist = math.pi / 2.0 if index % 2 == 0 else -math.pi / 2.0
        orientation = (
            orientation @ Matrix.Rotation(bend_radians, 3, "X") @ Matrix.Rotation(twist, 3, "Z")
        )
        center = joint + orientation @ Vector((0.0, 0.0, m(spec.joint_center_offset_mm)))

    cable_points = [
        centers[0] - orientations[0] @ Vector((0.0, 0.0, m(spec.joint_center_offset_mm + 4.0))),
        *centers,
        centers[-1] + orientations[-1] @ Vector((0.0, 0.0, m(spec.joint_center_offset_mm + 4.0))),
    ]
    curve_data = bpy.data.curves.new("HH_BENT_SENSOR_CABLE_DATA", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 2
    curve_data.bevel_depth = m(1.35)
    curve_data.bevel_resolution = 4
    spline = curve_data.splines.new("POLY")
    spline.points.add(len(cable_points) - 1)
    for point, coordinate in zip(spline.points, cable_points, strict=True):
        point.co = (*coordinate, 1.0)
    cable = bpy.data.objects.new("HH_BENT_SENSOR_CABLE", curve_data)
    target.objects.link(cable)
    curve_data.materials.append(cable_material)
    cable.show_in_front = True
    cable.hide_render = True
    cable.hide_viewport = True

    midpoint = sum(centers, Vector()) / len(centers)
    target_mm = tuple(value * 1000.0 for value in midpoint)
    return copies, cable, target_mm


def render_views(
    output_dir: Path,
    camera: bpy.types.Object,
    assembly_objects: list[bpy.types.Object],
    hardware: bpy.types.Collection,
    labels: list[bpy.types.Object],
    layout_objects: list[bpy.types.Object],
    bent_objects: list[bpy.types.Object],
    bent_cable: bpy.types.Object,
    bent_target_mm: tuple[float, float, float],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    assembly_camera_location = tuple(camera.location)
    assembly_camera_rotation = tuple(camera.rotation_euler)
    assembly_camera_scale = camera.data.ortho_scale
    assembly_resolution = (scene.render.resolution_x, scene.render.resolution_y)
    for label in labels:
        face_camera(label, camera)
    scene.render.filepath = str(output_dir / "hollow_side_hinge_assembly.png")
    bpy.ops.render.render(write_still=True)

    for obj in assembly_objects:
        obj.hide_render = True
    for obj in hardware.objects:
        obj.hide_render = True
    for obj in labels:
        obj.hide_render = True

    for obj in bent_objects:
        obj.hide_render = False
    bent_cable.hide_render = False
    camera.location = (m(145.0), m(-235.0), m(125.0))
    camera.data.ortho_scale = m(170.0)
    look_at(camera, bent_target_mm)
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1200
    scene.render.filepath = str(output_dir / "hollow_side_hinge_bent.png")
    bpy.ops.render.render(write_still=True)

    for obj in bent_objects:
        obj.hide_render = True
    bent_cable.hide_render = True
    for obj in layout_objects:
        obj.hide_render = False

    camera.location = (0.0, m(-175.0), m(115.0))
    camera.data.ortho_scale = m(160.0)
    look_at(camera, (0.0, 0.0, 15.0))
    scene.display.shading.show_shadows = False
    scene.render.resolution_x = 1300
    scene.render.resolution_y = 850
    scene.render.filepath = str(output_dir / "hollow_side_hinge_print_layout.png")
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
    camera.location = assembly_camera_location
    camera.rotation_euler = assembly_camera_rotation
    camera.data.ortho_scale = assembly_camera_scale
    scene.render.resolution_x, scene.render.resolution_y = assembly_resolution
    scene.render.filepath = str(output_dir / "hollow_side_hinge_assembly.png")
