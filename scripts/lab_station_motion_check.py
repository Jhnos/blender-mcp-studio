"""Actual mesh regression probes; sampled clearances are not physical load tests."""

import math

import bpy
from mathutils import Matrix
from mathutils.bvhtree import BVHTree

from scripts.lab_station_joints import placed_plate
from scripts.lab_station_rig import set_pose


def tree(obj: bpy.types.Object) -> BVHTree:
    return BVHTree.FromPolygons(
        [obj.matrix_world @ vertex.co for vertex in obj.data.vertices],
        [list(face.vertices) for face in obj.data.polygons],
    )


def verify_motion() -> dict[str, object]:
    control = bpy.data.objects["LS_SCREEN_CONTROL"]
    moving = [bpy.data.objects[name] for name in ("LS_FIT_lcd_front", "LS_FIT_lcd_back")]
    fixed = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and (
            obj.name.startswith(
                (
                    "LS_REF_capillary",
                    "LS_REF_pH_temp",
                    "LS_FIT_capillary",
                    "LS_FIT_pH_temp",
                    "LS_HW_capillary",
                    "LS_HW_pH_temp",
                )
            )
            or obj.name
            in (
                "LS_FIT_chassis",
                "LS_FIT_lid",
                "LS_FIT_screen_bracket_left",
                "LS_FIT_screen_bracket_right",
            )
        )
    ]
    samples = []
    try:
        for angle in range(0, 76, 5):
            set_pose(control, tilt_step=angle / 15, release_mm=2.0)
            hits = [(a.name, b.name) for a in moving for b in fixed if tree(a).overlap(tree(b))]
            minimum = min(
                (obj.matrix_world @ v.co).z * 1000 for obj in moving for v in obj.data.vertices
            )
            samples.append(
                {"angle_deg": angle, "surface_intersections": hits, "minimum_z_mm": minimum}
            )
            if hits or minimum < 86:
                raise ValueError(f"Screen sweep failed: {samples[-1]}")
    finally:
        set_pose(control, tilt_step=4, release_mm=0.0)
    mat = moving[0].data.materials[0]
    a = placed_plate("LS_DIAG_fixed", mat, (-4.7, 0, 0), 1)
    b = placed_plate("LS_DIAG_moving", mat, (4.7, 0, 0), -1)
    orientation = b.rotation_euler.to_matrix().to_4x4()
    coupon = []
    try:
        for coupon_angle, release, expected in (
            (0, 0, False),
            (15, 0, False),
            (7.5, 0, True),
            (7.5, 2, False),
        ):
            b.rotation_euler = (
                Matrix.Rotation(math.radians(coupon_angle), 4, "X") @ orientation
            ).to_euler()
            b.location.x = (4.7 + release) / 1000
            bpy.context.view_layer.update()
            pair_count = len(tree(a).overlap(tree(b)))
            coupon.append(
                {"angle_deg": coupon_angle, "release_mm": release, "intersection_pairs": pair_count}
            )
            if bool(pair_count) != expected:
                raise ValueError(f"Tooth engagement regression: {coupon[-1]}")
    finally:
        for obj in (a, b):
            bpy.data.objects.remove(obj, do_unlink=True)
    return {
        "screen_sweep": samples,
        "coupon_engagement": coupon,
        "scope": "Sampled surface intersections only; no force, cable, containment or full arm sweep acceptance.",
    }
