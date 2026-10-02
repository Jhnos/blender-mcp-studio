"""Removable probe jaws and rod keepers, built with existing mesh primitives."""

import math

import bpy
from mathutils import Matrix

from scripts.blender_mesh_primitives import add_cylinder, assign, boolean, cleanup_mesh, material
from scripts.lab_station_joints import block
from src.core.domain.lab_station import Point, ProbeClampSpec


def lined_jaw(
    carrier: bpy.types.Object,
    label: str,
    side: int,
    probe: Point,
    mat: bpy.types.Material,
    soft: bpy.types.Material,
    *,
    spec: ProbeClampSpec | None = None,
    rounded: bool = False,
    dual: bool | None = None,
) -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    spec = spec or ProbeClampSpec()
    x, y, pz = probe
    z = pz - 28
    half_width = (spec.jaw_width_mm - spec.split_gap_mm) / 2
    center = (spec.jaw_width_mm + spec.split_gap_mm) / 4
    fixed = block(
        "LS_TOOL_jaw", (half_width, spec.jaw_depth_mm, 18), (x + side * center, y, z), mat
    )
    cap = block(
        f"LS_FIT_{label}_clamp_cap",
        (half_width, spec.jaw_depth_mm, 18),
        (x - side * center, y, z),
        mat,
    )
    if rounded:
        for part in (fixed, cap):
            bevel = part.modifiers.new("Rounded jaw edges", "BEVEL")
            bevel.width, bevel.segments = 0.004, 6
            bpy.context.view_layer.objects.active = part
            bpy.ops.object.modifier_apply(modifier=bevel.name)
    boolean(carrier, fixed, "UNION")
    boolean(
        carrier, block("LS_TOOL_split", (spec.split_gap_mm, 48, 22), (x, y, z), mat), "DIFFERENCE"
    )
    liners = []
    for index, (dy, bore) in enumerate(spec.bores(side > 0 if dual is None else dual)):
        for part in (carrier, cap):
            boolean(part, add_cylinder("LS_TOOL_probe", bore, 24, (x, y + dy, z)), "DIFFERENCE")
            if rounded:
                for dz in (-9.7, 9.7):
                    boolean(
                        part,
                        add_cylinder(
                            "LS_TOOL_flange_clearance", bore + 1.1, 1.6, (x, y + dy, z + dz)
                        ),
                        "DIFFERENCE",
                    )
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
                "LS_TOOL_clamp_nut",
                3.3,
                2.8,
                (x - side * (spec.jaw_width_mm / 2 - 1.3), y + dy, z),
                "X",
                vertices=6,
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
    # Released M4x12 thumb screw: flat tip 0.5 mm clear of the outer guide rod.
    lock_x = x + side * 50
    screw = add_cylinder(f"LS_HW_{label}_slide_lock_screw", 2, 12, (lock_x, y - 10.5, z), "Y")
    boolean(
        screw,
        add_cylinder("LS_TOOL_thumb", 7, 4.2, (lock_x, y - 18.5, z), "Y"),
        "UNION",
    )
    nut = add_cylinder(
        f"LS_HW_{label}_slide_lock_nut", 4.04, 3.2, (lock_x, y - 8.4, z), "Y", vertices=6
    )
    boolean(nut, add_cylinder("LS_TOOL_m4_thread", 2.1, 5, (lock_x, y - 8.4, z), "Y"), "DIFFERENCE")
    for obj in (screw, nut):
        assign(obj, mat)
        moving.append(obj)
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


def compact_probe_head(label: str, mat: bpy.types.Material) -> list[bpy.types.Object]:
    """Reuse split liners in a narrower, rounded jaw attached behind the wrist disc."""
    dual = label == "pH_temp"
    offset = -21 if dual else -20
    z = -38 if dual else -20
    prefix = "S_" + label + "_"
    spec = ProbeClampSpec(
        jaw_width_mm=20,
        jaw_depth_mm=46 if dual else 30,
        bolt_y_mm=(-18, 18) if dual else (-10, 10),
    )
    ring_y = -4.2 - offset
    head = add_cylinder(prefix + "head", 11, 8, (0, ring_y, 0), "Y")
    assign(head, mat)
    boolean(head, add_cylinder("E_TOOL", 2.7, 20, (0, ring_y, 0), "Y"), "DIFFERENCE")
    boolean(head, block("E_TOOL", (8, 8, -z - 8), (4.4, ring_y, (z - 4) / 2), mat), "UNION")
    boolean(
        head,
        block("E_TOOL_cap_clearance", (20, spec.jaw_depth_mm + 0.4, 18.4), (-10.2, 0, z), mat),
        "DIFFERENCE",
    )
    cap, liners = lined_jaw(
        head,
        label,
        1,
        (0, 0, z + 28),
        mat,
        material("S_soft_liner", (0.12, 0.14, 0.15, 1)),
        spec=spec,
        rounded=True,
        dual=dual,
    )
    cap.name = prefix + "clamp_cap"
    for index, liner in enumerate(liners):
        liner.name = prefix + f"clamp_liner_{index}"
    parts = [head, cap, *liners]
    for index, y in enumerate(spec.bolt_y_mm):
        bolt, washer, nut = hardware_set(
            prefix + f"clamp_{index}",
            "X",
            (10.2, y, z),
            -1,
            20,
            (-8.6, y, z),
            bpy.data.materials["S_metal"],
        )
        bpy.data.objects.remove(washer, do_unlink=True)
        boolean(bolt, add_cylinder("E_TOOL", 1.3, 2.2, (12.6, y, z), "X", vertices=6), "DIFFERENCE")
        for part in (bolt, nut):
            part["nominal_hardware"] = True
        parts.extend((bolt, nut))
    frame = Matrix.Translation((offset / 1000, 0, 0)) @ Matrix.Rotation(-math.pi / 2, 4, "Z")
    for part in parts:
        part.data.transform(frame @ part.matrix_world)
        part.matrix_world = Matrix.Identity(4)
        part["compact_head_part"] = True
    return parts
