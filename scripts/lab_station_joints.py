"""Printed serration coupons and folding screen supports for the laboratory prototype."""

from __future__ import annotations

import math

import bmesh
import bpy
from mathutils import Matrix

from scripts.blender_mesh_primitives import add_cylinder, assign, boolean, cleanup_mesh, loft_rings
from scripts.lab_station_rig import driver, pivot
from src.core.domain.lab_station import Point
from src.core.domain.lab_station_joints import ScreenHingeSpec, SerratedJointSpec


def serrated_plate(
    name: str, mat: bpy.types.Material, bore_radius_mm: float = 2.7
) -> bpy.types.Object:
    spec = SerratedJointSpec(bore_radius_mm=bore_radius_mm)
    count = spec.teeth * 8
    radii = (spec.bore_radius_mm, spec.tooth_inner_radius_mm, spec.radius_mm)
    vertices = []
    for top in (False, True):
        for ring, radius in enumerate(radii):
            for index in range(count):
                angle = index * 2 * math.pi / count
                z = (
                    (spec.base_mm + (spec.profile(math.degrees(angle)) if ring else 0))
                    if top
                    else 0
                )
                vertices.append(
                    (radius * math.cos(angle) / 1000, radius * math.sin(angle) / 1000, z / 1000)
                )
    faces = []
    for i in range(count):
        j = (i + 1) % count
        for r in (0, 1):
            a, b = r * count, (r + 1) * count
            faces.append((a + j, b + j, b + i, a + i))
            faces.append(
                (a + i + 3 * count, b + i + 3 * count, b + j + 3 * count, a + j + 3 * count)
            )
        faces.append((i, i + 3 * count, j + 3 * count, j))
        faces.append((i + 2 * count, j + 2 * count, j + 5 * count, i + 5 * count))
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    cleanup_mesh(obj)
    editable = bmesh.new()
    editable.from_mesh(obj.data)
    bmesh.ops.triangulate(editable, faces=list(editable.faces))
    editable.to_mesh(obj.data)
    editable.free()
    assign(obj, mat)
    return obj


def placed_plate(
    name: str, mat: bpy.types.Material, point: Point, facing: int, bore_radius_mm: float = 2.7
) -> bpy.types.Object:
    obj = serrated_plate(name, mat, bore_radius_mm)
    orientation = Matrix.Rotation(facing * math.pi / 2, 4, "Y")
    if facing < 0:
        orientation @= Matrix.Rotation(math.pi / 24, 4, "Z")
    obj.rotation_euler = orientation.to_euler()
    obj.location = tuple(v / 1000 for v in point)
    return obj


def block(name: str, size: Point, center: Point, mat: bpy.types.Material) -> bpy.types.Object:
    x, y, z = (v / 2 for v in size)
    cx, cy, cz = center
    obj = loft_rings(
        name,
        [
            [
                (cx - x, cy - y, cz + level),
                (cx + x, cy - y, cz + level),
                (cx + x, cy + y, cz + level),
                (cx - x, cy + y, cz + level),
            ]
            for level in (-z, z)
        ],
    )
    assign(obj, mat)
    return obj


def add_screen_ears(back: bpy.types.Object, mat: bpy.types.Material) -> None:
    for side in (-1, 1):
        ear = add_cylinder("LS_TOOL_ear", 14, 8, (side * 76, -55, 0), "X")
        boolean(back, ear, "UNION")
        boolean(
            back,
            add_cylinder("LS_TOOL_bore", 2.8, 9, (side * 76, -55, 0), "X", vertices=192),
            "DIFFERENCE",
        )
    teeth = placed_plate("LS_TOOL_teeth", mat, (-79.8, -55, 0), -1, 2.8)
    boolean(back, teeth, "UNION")
    cleanup_mesh(back)


def screen_bracket(side: int, mat: bpy.types.Material) -> bpy.types.Object:
    hinge = ScreenHingeSpec()
    _, y, z = hinge.pivot_mm
    name = "LS_FIT_screen_bracket_" + ("left" if side < 0 else "right")
    foot = block(name, (18, 38, 6), (side * 93, y, 83), mat)
    boolean(
        foot,
        block("LS_TOOL_web", (9, 18, z + 2.3 - 84), (side * 93, y, (z + 2.3 + 84) / 2), mat),
        "UNION",
    )
    if side > 0:
        boolean(foot, add_cylinder("LS_TOOL_guide", 14, 10, (88, y, z), "X"), "UNION")
    for dy in (-15, 15):
        boolean(foot, add_cylinder("LS_TOOL_mount", 1.8, 12, (side * 93, y + dy, 83)), "DIFFERENCE")
    boolean(
        foot,
        add_cylinder("LS_TOOL_bolt", 2.8, 30, (side * 93, y, z), "X", vertices=192),
        "DIFFERENCE",
    )
    if side < 0:
        boolean(foot, placed_plate("LS_TOOL_fixed_teeth", mat, (-89.2, y, z), 1, 2.8), "UNION")
    cleanup_mesh(foot)
    editable = bmesh.new()
    editable.from_mesh(foot.data)
    bmesh.ops.triangulate(editable, faces=list(editable.faces))
    editable.to_mesh(foot.data)
    editable.free()
    cleanup_mesh(foot)
    return foot


def screen_control(hmi: bpy.types.Object) -> bpy.types.Object:
    spec = ScreenHingeSpec()
    control = pivot("LS_SCREEN_CONTROL", spec.pivot_mm)
    control["tilt_step"] = spec.default_step
    control.id_properties_ui("tilt_step").update(
        min=0,
        max=5,
        description="0 = folded; each step = 15 degrees. Disengage teeth before moving real hardware.",
    )
    control["release_mm"] = 0.0
    control.id_properties_ui("release_mm").update(min=0.0, max=2.0)
    hmi.parent = control
    hmi.location = (0, 0.055, 0)
    hmi.rotation_euler = (0, 0, 0)
    driver(
        control,
        control,
        "rotation_euler",
        0,
        "min(5,max(0,tilt_step))*0.2617993877991494",
        ("tilt_step",),
    )
    driver(hmi, control, "location", 0, "release_mm*0.001", ("release_mm",))
    bpy.context.view_layer.update()
    return control
