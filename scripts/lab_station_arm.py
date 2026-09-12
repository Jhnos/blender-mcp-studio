"""Side-mounted elbow teeth connected to links through offset necks."""

from collections.abc import Callable
from typing import Literal

import bmesh
import bpy

from scripts.blender_mesh_primitives import add_cylinder, assign, boolean, cleanup_mesh
from scripts.lab_station_joints import placed_plate
from src.core.domain.lab_station import Point


def connect_serrated_joint(
    upper: bpy.types.Object,
    lower: bpy.types.Object,
    point: Point,
    necks: tuple[Point, Point],
    label: str,
    mat: bpy.types.Material,
    beam: Callable[[str, Point, Point, bpy.types.Material], bpy.types.Object],
    joint: Literal["elbow", "shoulder"] = "elbow",
) -> None:
    x, y, z = point
    for link, neck, sign in ((upper, necks[0], -1), (lower, necks[1], 1)):
        center = (x + sign * (13 if joint == "shoulder" else 14), y, z)
        boolean(link, beam("TOOL_elbow_neck", center, neck, mat), "UNION")
        hub_center = (x + sign * (7 if joint == "shoulder" else 14), y, z)
        boolean(
            link,
            add_cylinder(
                "LS_TOOL_elbow_hub", 14, 5 if joint == "shoulder" else 20, hub_center, "X"
            ),
            "UNION",
        )
        boolean(link, add_cylinder("LS_TOOL_elbow_bore", 2.7, 70, point, "X"), "DIFFERENCE")
        if joint == "shoulder":
            boolean(
                link,
                add_cylinder("LS_TOOL_shoulder_seat", 5.3, 25, (x + sign * 22, y, z), "X"),
                "DIFFERENCE",
            )
            if sign < 0:
                boolean(
                    link,
                    add_cylinder("LS_TOOL_shoulder_head_seat", 8.3, 20, (x - 25.3, y, z), "X"),
                    "DIFFERENCE",
                )
        plate = placed_plate(
            "LS_TOOL_elbow_teeth",
            mat,
            (x + sign * 4.7, y, z),
            -sign,
            2.75,
        )
        boolean(link, plate, "UNION")
        cleanup_mesh(link)
        link[joint + "_integrated"] = True


def joint_hardware(
    point: Point, label: str, mat: bpy.types.Material, joint: Literal["elbow", "shoulder"] = "elbow"
) -> list[bpy.types.Object]:
    x, y, z = point
    compact = joint == "shoulder"
    bolt = add_cylinder(
        f"LS_HW_{label}_{joint}_bolt",
        2.5,
        35 if compact else 60,
        (x + (2 if compact else 4), y, z),
        "X",
    )
    boolean(
        bolt,
        add_cylinder(
            "LS_TOOL_elbow_head",
            8,
            4.2 if compact else 6.2,
            (x - (17.6 if compact else 29), y, z),
            "X",
        ),
        "UNION",
    )
    nut = add_cylinder(
        f"LS_HW_{label}_{joint}_nut", 4.6, 4, (x + (13.5 if compact else 28), y, z), "X", vertices=6
    )
    boolean(
        nut,
        add_cylinder("LS_TOOL_elbow_thread", 2.6, 6, (x + (13.5 if compact else 28), y, z), "X"),
        "DIFFERENCE",
    )
    washers = []
    for offset, name in ((-10.5 if compact else -25, "left"), (10.5 if compact else 25, "right")):
        center = (x + offset, y, z)
        washer = add_cylinder(f"LS_HW_{label}_{joint}_washer_{name}", 5, 1, center, "X")
        boolean(
            washer, add_cylinder("LS_TOOL_elbow_washer_hole", 2.65, 3, center, "X"), "DIFFERENCE"
        )
        washers.append(washer)
    for obj in (bolt, nut, *washers):
        assign(obj, mat)
    return [bolt, nut, *washers]


def verify_elbow_release() -> dict[str, object]:
    """Probe real integrated arm meshes, including a locked mid-tooth negative control."""
    from scripts.lab_station_motion_check import tree
    from scripts.lab_station_rig import set_pose

    rows = []
    for label in ("capillary", "pH_temp"):
        control = bpy.data.objects["LS_CTRL_" + label]
        if "elbow_release_mm" not in control:
            raise ValueError(f"Elbow release control missing: {label}")
        upper = bpy.data.objects[f"LS_REF_{label}_link_0"]
        lower = bpy.data.objects[f"LS_REF_{label}_link_1"]
        try:
            for angle, release, expected in (
                (0, 0, False),
                (7.5, 0, True),
                (7.5, 2, False),
                (15, 2, False),
                (15, 0, False),
            ):
                set_pose(control, elbow_deg=angle, elbow_release_mm=release)
                pairs = len(tree(upper).overlap(tree(lower)))
                if bool(pairs) != expected:
                    raise ValueError(
                        f"Elbow tooth release failed: {label}, {angle}, {release}, {pairs}"
                    )
                for suffix in ("bolt", "nut", "washer_left", "washer_right"):
                    hardware = bpy.data.objects[f"LS_HW_{label}_elbow_{suffix}"]
                    for part in (upper, lower):
                        if tree(hardware).overlap(tree(part)):
                            raise ValueError(
                                f"Elbow release hardware blocked: {label}, {angle}, {release}, {suffix}, {part.name}"
                            )
                bolt = bpy.data.objects[f"LS_HW_{label}_elbow_bolt"]
                nut = bpy.data.objects[f"LS_HW_{label}_elbow_nut"]
                protrusion = 1000 * (
                    max((bolt.matrix_world @ v.co).x for v in bolt.data.vertices)
                    - max((nut.matrix_world @ v.co).x for v in nut.data.vertices)
                )
                if protrusion < 1.99:
                    raise ValueError(
                        f"Elbow bolt axial coverage insufficient: {label}, {protrusion}"
                    )
                rows.append(
                    {
                        "head": label,
                        "angle_deg": angle,
                        "release_mm": release,
                        "intersection_pairs": pairs,
                        "expected_intersection": expected,
                        "bolt_protrusion_mm": protrusion,
                    }
                )
        finally:
            set_pose(control, elbow_deg=0, elbow_release_mm=0)
    return {
        "samples": rows,
        "scope": "Local integrated elbow meshes; no full arm, cable, load or fastener retention qualification.",
    }


def finish_arm(obj: bpy.types.Object) -> None:
    """Resolve Boolean polygons before cleanup so export cannot create new slivers."""
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    bmesh.ops.triangulate(mesh, faces=list(mesh.faces))
    bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=0.00001)
    bmesh.ops.dissolve_degenerate(mesh, edges=list(mesh.edges), dist=0.000005)
    mesh.to_mesh(obj.data)
    mesh.free()
    cleanup_mesh(obj)


def verify_elbow_assembly(
    scene_prefixes: tuple[str, ...] = ("LS_",), hardware_prefix: str = "LS_HW_"
) -> dict[str, object]:
    """Nominal rigid insertion sequence; the frame must be supported during assembly."""
    from scripts.lab_station_motion_check import tree

    parts = [
        o
        for o in bpy.context.scene.objects
        if o.type == "MESH"
        and o.name.startswith(scene_prefixes)
        and not o.hide_render
        and not o.name.startswith(("LS_CHECK_", "LS_DIAG_"))
    ]
    if len(parts) < 50:
        raise ValueError("Elbow assembly population incomplete")
    rows = []
    for label in ("capillary", "pH_temp"):
        names = [
            f"{hardware_prefix}{label}_elbow_{suffix}"
            for suffix in ("bolt", "nut", "washer_left", "washer_right")
        ]
        if any(name not in bpy.data.objects for name in names):
            raise ValueError(f"Elbow assembly hardware incomplete: {label}")
        bolt, nut, left, right = [bpy.data.objects[name] for name in names]
        for moving, sign, absent in (
            ([bolt, left], -1, [nut, right]),
            ([right], 1, [nut]),
            ([nut], 1, []),
        ):
            original = {o.name: o.location.copy() for o in moving}
            fixed = {o.name: tree(o) for o in parts if o not in moving and o not in absent}
            try:
                for distance in range(70, -1, -2):
                    for obj in moving:
                        obj.location.x = original[obj.name].x + sign * distance / 1000
                    bpy.context.view_layer.update()
                    hits = [
                        (o.name, name)
                        for o in moving
                        for name, solid in fixed.items()
                        if tree(o).overlap(solid)
                    ]
                    if hits:
                        raise ValueError(f"Elbow insertion obstructed: {label}, {distance}, {hits}")
                    rows.append(
                        {
                            "head": label,
                            "moving": [o.name for o in moving],
                            "remaining_mm": distance,
                        }
                    )
            finally:
                for obj in moving:
                    obj.location = original[obj.name]
                bpy.context.view_layer.update()
    return {
        "samples": rows,
        "scope": "2 mm sampled rigid insertion only; no thread, preload or load qualification.",
    }


def build_shoulder(
    upper: bpy.types.Object,
    point: Point,
    neck: Point,
    label: str,
    mat: bpy.types.Material,
    metal: bpy.types.Material,
    beam: Callable[[str, Point, Point, bpy.types.Material], bpy.types.Object],
) -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    """Serrated rotor and upper arm; chassis bearing/retention remains a separate interface."""
    x, y, z = point
    rotor = add_cylinder(f"LS_FIT_{label}_shoulder_rotor", 26, 5, (x, y, 82.5))
    assign(rotor, mat)
    fixed_neck = (x - 13, y, 84)
    connect_serrated_joint(rotor, upper, point, (fixed_neck, neck), label, mat, beam, "shoulder")
    finish_arm(rotor)
    return rotor, joint_hardware(point, label, metal, "shoulder")


def verify_shoulder_release() -> dict[str, object]:
    from scripts.lab_station_motion_check import tree
    from scripts.lab_station_rig import set_pose

    rows = []
    for label in ("capillary", "pH_temp"):
        control = bpy.data.objects["LS_CTRL_" + label]
        upper = bpy.data.objects[f"LS_REF_{label}_link_0"]
        rotor = bpy.data.objects.get(f"LS_FIT_{label}_shoulder_rotor")
        if rotor is None or not upper.get("shoulder_integrated"):
            raise ValueError(f"Shoulder reference is not an assembled interface: {label}")
        try:
            for angle, release, expected in (
                (0, 0, False),
                (7.5, 0, True),
                (7.5, 2, False),
                (15, 2, False),
                (15, 0, False),
            ):
                set_pose(control, shoulder_deg=angle, shoulder_release_mm=release)
                pairs = len(tree(rotor).overlap(tree(upper)))
                if bool(pairs) != expected:
                    raise ValueError(
                        f"Shoulder tooth release failed: {label}, {angle}, {release}, {pairs}"
                    )
                for suffix in ("bolt", "nut", "washer_left", "washer_right"):
                    hardware = bpy.data.objects[f"LS_HW_{label}_shoulder_{suffix}"]
                    for part in (rotor, upper):
                        if tree(hardware).overlap(tree(part)):
                            raise ValueError(
                                f"Shoulder hardware obstructed: {label}, {angle}, {release}, {suffix}"
                            )
                rows.append(
                    {
                        "head": label,
                        "angle_deg": angle,
                        "release_mm": release,
                        "intersection_pairs": pairs,
                        "expected_intersection": expected,
                    }
                )
        finally:
            set_pose(control, shoulder_deg=0, shoulder_release_mm=0)
    return {
        "samples": rows,
        "scope": "Local shoulder meshes only; chassis bearing, load and retention unqualified.",
    }


def rotary_pivot_hardware(
    name: str, point: Point, side: int, mat: bpy.types.Material
) -> list[bpy.types.Object]:
    """Nominal M5x35 shoulder-less bolt, three washers and nut; no thread qualification."""
    x, y, z = point
    bolt = add_cylinder(name, 2.5, 35, (x + side * 8, y, z), "X")
    boolean(bolt, add_cylinder("LR_TOOL_head", 4.25, 5, (x - side * 12, y, z), "X"), "UNION")
    boolean(
        bolt,
        add_cylinder("LR_TOOL_hex", 2.42, 3.6, (x - side * 13.7, y, z), "X", vertices=6),
        "DIFFERENCE",
    )
    nut = add_cylinder(
        name.replace("_pin_", "_nut_"), 4.6, 4, (x + side * 17.7, y, z), "X", vertices=6
    )
    boolean(nut, add_cylinder("LR_TOOL_thread", 2.6, 6, (x + side * 17.7, y, z), "X"), "DIFFERENCE")
    parts = [bolt, nut]
    for label, distance in (("inner", -7), ("spacer", 7), ("outer", 15)):
        center = (x + side * distance, y, z)
        washer = add_cylinder(name.replace("_pin_", "_washer_" + label + "_"), 5, 1, center, "X")
        boolean(washer, add_cylinder("LR_TOOL_washer", 2.65, 3, center, "X"), "DIFFERENCE")
        parts.append(washer)
    for label, distance, depth in (("frame", 0, 12), ("link", 11, 6)):
        center = (x + side * distance, y, z)
        sleeve = add_cylinder(
            name.replace("_pin_", "_sleeve_" + label + "_"), 4, depth, center, "X"
        )
        boolean(sleeve, add_cylinder("LR_TOOL_sleeve", 2.6, depth + 2, center, "X"), "DIFFERENCE")
        parts.append(sleeve)
    for part in parts:
        assign(part, mat)
    return parts
