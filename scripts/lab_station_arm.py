"""Side-mounted elbow teeth connected to links through offset necks."""

from collections.abc import Callable

import bmesh
import bpy

from scripts.blender_mesh_primitives import add_cylinder, assign, boolean, cleanup_mesh
from scripts.lab_station_joints import placed_plate
from src.core.domain.lab_station import Point


def connect_elbow(
    upper: bpy.types.Object,
    lower: bpy.types.Object,
    point: Point,
    necks: tuple[Point, Point],
    label: str,
    mat: bpy.types.Material,
    beam: Callable[[str, Point, Point, bpy.types.Material], bpy.types.Object],
) -> None:
    x, y, z = point
    for link, neck, sign in ((upper, necks[0], -1), (lower, necks[1], 1)):
        center = (x + sign * 14, y, z)
        boolean(link, beam("TOOL_elbow_neck", center, neck, mat), "UNION")
        boolean(link, add_cylinder("LS_TOOL_elbow_hub", 14, 20, center, "X"), "UNION")
        boolean(link, add_cylinder("LS_TOOL_elbow_bore", 2.7, 70, point, "X"), "DIFFERENCE")
        plate = placed_plate("LS_TOOL_elbow_teeth", mat, (x + sign * 4.7, y, z), -sign)
        boolean(link, plate, "UNION")
        cleanup_mesh(link)
        link["elbow_integrated"] = True


def elbow_hardware(point: Point, label: str, mat: bpy.types.Material) -> list[bpy.types.Object]:
    x, y, z = point
    bolt = add_cylinder(f"LS_HW_{label}_elbow_bolt", 2.5, 60, (x + 4, y, z), "X")
    boolean(bolt, add_cylinder("LS_TOOL_elbow_head", 8, 6.2, (x - 29, y, z), "X"), "UNION")
    nut = add_cylinder(f"LS_HW_{label}_elbow_nut", 4.6, 4, (x + 28, y, z), "X", vertices=6)
    boolean(nut, add_cylinder("LS_TOOL_elbow_thread", 2.6, 6, (x + 28, y, z), "X"), "DIFFERENCE")
    washers = []
    for offset, name in ((-25, "left"), (25, "right")):
        center = (x + offset, y, z)
        washer = add_cylinder(f"LS_HW_{label}_elbow_washer_{name}", 5, 1, center, "X")
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


def verify_elbow_assembly() -> dict[str, object]:
    """Nominal rigid insertion sequence; the frame must be supported during assembly."""
    from scripts.lab_station_motion_check import tree

    parts = [
        o
        for o in bpy.context.scene.objects
        if o.type == "MESH"
        and o.name.startswith("LS_")
        and not o.hide_render
        and not o.name.startswith(("LS_CHECK_", "LS_DIAG_"))
    ]
    if len(parts) < 50:
        raise ValueError("Elbow assembly population incomplete")
    rows = []
    for label in ("capillary", "pH_temp"):
        names = [
            f"LS_HW_{label}_elbow_{suffix}"
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
