"""Removable probe jaws and rod keepers, built with existing mesh primitives."""

import bpy

from scripts.blender_mesh_primitives import add_cylinder, assign, boolean, cleanup_mesh
from scripts.lab_station_joints import block
from src.core.domain.lab_station import Point, ProbeClampSpec


def lined_jaw(
    carrier: bpy.types.Object,
    label: str,
    side: int,
    probe: Point,
    mat: bpy.types.Material,
    soft: bpy.types.Material,
) -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    spec = ProbeClampSpec()
    x, y, pz = probe
    z = pz - 28
    half_width = (30 - spec.split_gap_mm) / 2
    center = (30 + spec.split_gap_mm) / 4
    fixed = block(
        "LS_TOOL_jaw", (half_width, spec.jaw_depth_mm, 18), (x + side * center, y, z), mat
    )
    cap = block(
        f"LS_FIT_{label}_clamp_cap",
        (half_width, spec.jaw_depth_mm, 18),
        (x - side * center, y, z),
        mat,
    )
    boolean(carrier, fixed, "UNION")
    boolean(
        carrier, block("LS_TOOL_split", (spec.split_gap_mm, 48, 22), (x, y, z), mat), "DIFFERENCE"
    )
    liners = []
    for index, (dy, bore) in enumerate(spec.bores(side > 0)):
        for part in (carrier, cap):
            boolean(part, add_cylinder("LS_TOOL_probe", bore, 24, (x, y + dy, z)), "DIFFERENCE")
        liner = add_cylinder(
            f"LS_FIT_{label}_liner_{index}", spec.liner_outer_radius(bore), 18.4, (x, y + dy, z)
        )
        for dz in (-9.7, 9.7):
            boolean(
                liner,
                add_cylinder(
                    "LS_TOOL_flange", spec.liner_flange_radius(bore), 1.2, (x, y + dy, z + dz)
                ),
                "UNION",
            )
        boolean(
            liner,
            add_cylinder("LS_TOOL_liner_bore", spec.liner_inner_radius(bore), 24, (x, y + dy, z)),
            "DIFFERENCE",
        )
        mate = liner.copy()
        mate.data = liner.data.copy()
        mate.name = liner.name + "_mate"
        bpy.context.collection.objects.link(mate)
        for half, sign in ((liner, 1), (mate, -1)):
            boolean(
                half,
                block("LS_TOOL_liner_half", (20, 24, 24), (x - sign * 9.9, y + dy, z), mat),
                "DIFFERENCE",
            )
            assign(half, soft)
            cleanup_mesh(half)
            liners.append(half)
    for dy in spec.bolt_y_mm:
        for part in (carrier, cap):
            boolean(
                part, add_cylinder("LS_TOOL_clamp_bolt", 1.7, 36, (x, y + dy, z), "X"), "DIFFERENCE"
            )
        boolean(
            cap,
            add_cylinder(
                "LS_TOOL_clamp_nut", 3.3, 2.8, (x - side * 13.7, y + dy, z), "X", vertices=6
            ),
            "DIFFERENCE",
        )
    cleanup_mesh(carrier)
    cleanup_mesh(cap)
    return cap, liners


def rod_keeper(
    frame: bpy.types.Object, label: str, side: int, probe: Point, mat: bpy.types.Material
) -> bpy.types.Object:
    x, y, pz = probe
    x += side * 40
    z = pz - 28 + 126
    keeper = block(f"LS_FIT_{label}_rod_keeper", (36, 28, 4), (x, y + 6, z + 2.2), mat)
    for dx in (-10, 10):
        point = (x + dx, y + 13, z)
        for part in (frame, keeper):
            boolean(part, add_cylinder("LS_TOOL_keeper_bolt", 1.7, 24, point), "DIFFERENCE")
        boolean(
            frame,
            add_cylinder("LS_TOOL_keeper_nut", 3.3, 2.8, (point[0], point[1], z - 6.7), vertices=6),
            "DIFFERENCE",
        )
    cleanup_mesh(frame)
    cleanup_mesh(keeper)
    return keeper


def hardware_set(
    name: str,
    axis: str,
    entry: Point,
    direction: int,
    length: float,
    nut_center: Point,
    mat: bpy.types.Material,
) -> list[bpy.types.Object]:
    """Nominal M3 visual/clearance geometry; threads deliberately not represented."""
    index = 0 if axis == "X" else 2
    center = list(entry)
    center[index] += direction * length / 2
    bolt = add_cylinder(name + "_bolt", 1.5, length, (center[0], center[1], center[2]), axis)
    head = list(entry)
    head[index] -= direction * 1.5
    boolean(
        bolt, add_cylinder("LS_TOOL_head", 2.75, 3.2, (head[0], head[1], head[2]), axis), "UNION"
    )
    washer_at = list(entry)
    washer_at[index] += direction * 0.3
    washer = add_cylinder(
        name + "_washer", 3.2, 0.5, (washer_at[0], washer_at[1], washer_at[2]), axis
    )
    boolean(
        washer,
        add_cylinder(
            "LS_TOOL_washer_bore", 1.6, 2, (washer_at[0], washer_at[1], washer_at[2]), axis
        ),
        "DIFFERENCE",
    )
    nut = add_cylinder(name + "_nut", 3.175, 2.4, nut_center, axis, vertices=6)
    boolean(nut, add_cylinder("LS_TOOL_nut_bore", 1.6, 4, nut_center, axis), "DIFFERENCE")
    for obj in (bolt, washer, nut):
        assign(obj, mat)
    return [bolt, washer, nut]


def clamp_hardware(
    label: str, side: int, probe: Point, mat: bpy.types.Material
) -> tuple[list[bpy.types.Object], list[bpy.types.Object]]:
    x, y, pz = probe
    z = pz - 28
    moving, fixed = [], []
    for dy in ProbeClampSpec().bolt_y_mm:
        moving.extend(
            hardware_set(
                f"LS_HW_{label}_jaw_{dy}",
                "X",
                (x + side * 15.6, y + dy, z),
                -side,
                35,
                (x - side * 13.7, y + dy, z),
                mat,
            )
        )
    for dx in (-10, 10):
        rx = x + side * 40 + dx
        fixed.extend(
            hardware_set(
                f"LS_HW_{label}_keeper_{dx}",
                "Z",
                (rx, y + 13, z + 130.8),
                -1,
                14,
                (rx, y + 13, z + 119.3),
                mat,
            )
        )
    return moving, fixed
