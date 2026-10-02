"""Printed serration coupons and folding screen supports for the laboratory prototype."""

from __future__ import annotations

import math
from collections.abc import Callable

import bmesh
import bpy
from mathutils import Matrix

from scripts.blender_mesh_primitives import add_cylinder, assign, boolean, cleanup_mesh, loft_rings
from scripts.lab_station_rig import driver, pivot
from src.core.domain.lab_station import ElectrodeArmSpec, Point
from src.core.domain.lab_station_joints import ScreenHingeSpec, SerratedJointSpec


def serrated_plate(
    name: str,
    mat: bpy.types.Material,
    bore_radius_mm: float = 2.7,
    *,
    spec: SerratedJointSpec | None = None,
    consistent_diagonal: bool = False,
) -> bpy.types.Object:
    spec = spec or SerratedJointSpec(bore_radius_mm=bore_radius_mm)
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
    bmesh.ops.triangulate(
        editable,
        faces=list(editable.faces),
        quad_method="FIXED" if consistent_diagonal else "BEAUTY",
    )
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


def hand_knob(name: str, mat: bpy.types.Material, radius_mm: float = 12.5) -> bpy.types.Object:
    """Scalloped knob with an open hex-head pocket and an integral bearing neck."""
    obj = add_cylinder(name, radius_mm, 10, (-13.3, 0, 0), "X")
    for index in range(6):
        angle = index * math.pi / 3
        boolean(
            obj,
            add_cylinder(
                "E_TOOL",
                3,
                12,
                (-13.3, (radius_mm + 1.5) * math.cos(angle), (radius_mm + 1.5) * math.sin(angle)),
                "X",
            ),
            "DIFFERENCE",
        )
    boolean(obj, add_cylinder("E_TOOL", 4.8, 10.4, (-16, 0, 0), "X", vertices=6), "DIFFERENCE")
    boolean(obj, add_cylinder("E_TOOL", 2.7, 20, (-13.3, 0, 0), "X"), "DIFFERENCE")
    assign(obj, mat)
    return obj


def hand_knob_hardware(
    prefix: str, mat: bpy.types.Material, metal: bpy.types.Material, radius_mm: float
) -> tuple[bpy.types.Object, bpy.types.Object, bpy.types.Object]:
    bolt = add_cylinder(prefix + "bolt", 2.5, 20, (-1, 0, 0), "X")
    boolean(bolt, add_cylinder("E_TOOL", 4.6, 4, (-13, 0, 0), "X", vertices=6), "UNION")
    nut = add_cylinder(prefix + "nut", 4.6, 4, (6.3, 0, 0), "X", vertices=6)
    boolean(nut, add_cylinder("E_TOOL", 2.6, 6, (6.3, 0, 0), "X"), "DIFFERENCE")
    for obj in (bolt, nut):
        assign(obj, metal)
        obj["nominal_hardware"] = True
    return bolt, nut, hand_knob(prefix + "knob", mat, radius_mm)


def retained_pivot(
    prefix: str, mat: bpy.types.Material
) -> tuple[bpy.types.Object, bpy.types.Object]:
    pin = add_cylinder(prefix + "pin", 2.4, 22, (8.2, 0, 0), "X")
    boolean(pin, add_cylinder("E_TOOL", 4.5, 2, (18.2, 0, 0), "X"), "UNION")
    ring = add_cylinder("E_TOOL", 3.4, 1.8, (-1.1, 0, 0), "X")
    boolean(ring, add_cylinder("E_TOOL", 1.7, 4, (-1.1, 0, 0), "X"), "DIFFERENCE")
    boolean(pin, ring, "DIFFERENCE")
    pin["printed_pivot"] = True
    clip = add_cylinder(prefix + "clip", 4.5, 1.4, (-1.1, 0, 0), "X")
    boolean(clip, add_cylinder("E_TOOL", 1.9, 4, (-1.1, 0, 0), "X"), "DIFFERENCE")
    boolean(clip, block("E_TOOL", (4, 6, 3), (-1.1, 3, 0), mat), "DIFFERENCE")
    clip["elastic_fit_unqualified"] = True
    for obj in (pin, clip):
        assign(obj, mat)
    return pin, clip


def electrode_elbow_teeth(label: str, finish: Callable[[bpy.types.Object], None]) -> None:
    """Recess matched tooth faces into the existing elbow discs in the working pose."""
    prefix = "S_" + label + "_"
    if label == "pH_temp":
        for suffix in ("upper", "lower"):
            source = bpy.data.objects["S_capillary_" + suffix]
            if source.get("elbow_teeth") != ElectrodeArmSpec.elbow_teeth:
                raise ValueError("Build the canonical toothed arm before its mirrored copy")
            target = bpy.data.objects[prefix + suffix]
            mat = target.data.materials[0]
            previous = target.data
            target.data = source.data.copy()
            target.data.transform(Matrix.Diagonal((-1, 1, 1, 1)))
            target.data.materials.clear()
            target.data.materials.append(mat)
            finish(target)
            target["elbow_teeth"] = ElectrodeArmSpec.elbow_teeth
            if previous.users == 0:
                bpy.data.meshes.remove(previous)
        return
    side = 1
    frame = bpy.data.objects[prefix + "elbow_bolt"].matrix_world @ Matrix.Diagonal((side, 1, 1, 1))
    spec = SerratedJointSpec(radius_mm=11, bore_radius_mm=2.8, teeth=ElectrodeArmSpec.elbow_teeth)
    for suffix, cut_center in (("lower", 0.8), ("upper", -0.8)):
        body = bpy.data.objects[prefix + suffix]
        cutter = add_cylinder("E_TOOL", 11.05, 4, (cut_center, 0, 0), "X")
        cutter.matrix_world = frame @ cutter.matrix_world
        boolean(body, cutter, "DIFFERENCE")
        finish(body)
        teeth = serrated_plate(
            "E_TOOL", body.data.materials[0], spec=spec, consistent_diagonal=True
        )
        if suffix == "upper":
            # Keep the same triangulated front as the lower half, offset by the gap.
            # Flipping an independently triangulated corrugated quad changes its surface.
            for vertex in teeth.data.vertices:
                vertex.co.z = (
                    0.0094 if abs(vertex.co.z) < 1e-8 else vertex.co.z + spec.assembly_gap_mm / 1000
                )
            cleanup_mesh(teeth)
        teeth.matrix_world = (
            frame @ Matrix.Translation((-0.0048, 0, 0)) @ Matrix.Rotation(math.pi / 2, 4, "Y")
        )
        if suffix == "upper":
            pocket = add_cylinder("E_TOOL", 4.8, 5, (side * 6.6, 0, 150), "X", vertices=6)
            pocket.matrix_world = body.matrix_world @ pocket.matrix_world
            boolean(teeth, pocket, "DIFFERENCE")
            finish(teeth)
        boolean(body, teeth, "UNION")
        finish(body)
        body["elbow_teeth"] = spec.teeth
