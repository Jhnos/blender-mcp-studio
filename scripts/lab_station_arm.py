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
    for obj in (bolt, nut):
        assign(obj, mat)
    return [bolt, nut]


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
                for suffix in ("bolt", "nut"):
                    hardware = bpy.data.objects[f"LS_HW_{label}_elbow_{suffix}"]
                    for part in (upper, lower):
                        if tree(hardware).overlap(tree(part)):
                            raise ValueError(
                                f"Elbow release hardware blocked: {label}, {angle}, {release}, {suffix}, {part.name}"
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
