"""Fork-and-tongue wrist geometry, using existing primitive and Boolean helpers."""

import bpy

from scripts.blender_mesh_primitives import add_cylinder, assign, boolean, cleanup_mesh
from scripts.lab_station_joints import block
from src.core.domain.lab_station import Point


def build_wrist(
    frame: bpy.types.Object,
    link: bpy.types.Object,
    point: Point,
    label: str,
    mat: bpy.types.Material,
    steel: bpy.types.Material,
) -> list[bpy.types.Object]:
    """Integrate tongue into frame and fork into lower link; return nominal axle hardware."""
    x, y, z = point
    tongue = add_cylinder("LS_TOOL_tongue", 12, 12, point, "X")
    assign(tongue, mat)
    boolean(frame, block("LS_TOOL_neck", (12, 20, 12), (x, y - 10, z), mat), "UNION")
    boolean(frame, tongue, "UNION")
    boolean(frame, add_cylinder("LS_TOOL_axle_bore", 2.7, 80, point, "X"), "DIFFERENCE")
    # Join the upper bridge first, then cheeks and round ears. Each Boolean
    # extends an already connected part rather than leaving disconnected islands.
    boolean(link, block("LS_TOOL_bridge", (26, 25, 8), (x, y, z + 26), mat), "UNION")
    for side in (-1, 1):
        rx = x + side * 9.5
        boolean(link, block("LS_TOOL_cheek", (6, 22, 26), (rx, y, z + 12), mat), "UNION")
        boolean(link, add_cylinder("LS_TOOL_ear", 12, 6.2, (rx, y, z), "X"), "UNION")
    boolean(link, add_cylinder("LS_TOOL_fork_bore", 2.7, 40, point, "X"), "DIFFERENCE")
    frame["wrist_tongue"] = True
    link["wrist_fork"] = True
    for part in (frame, link):
        cleanup_mesh(part)
    shaft = add_cylinder(f"LS_HW_{label}_wrist_axle", 2.5, 35, (x + 3.5, y, z), "X")
    boolean(shaft, add_cylinder("LS_TOOL_axle_head", 4.25, 5.2, (x - 16.5, y, z), "X"), "UNION")
    nut = add_cylinder(f"LS_HW_{label}_wrist_nut", 4.6, 4, (x + 16, y, z), "X", vertices=6)
    boolean(nut, add_cylinder("LS_TOOL_thread", 2.6, 6, (x + 16, y, z), "X"), "DIFFERENCE")
    washers = []
    for side in (-1, 1):
        at = (x + side * 13.3, y, z)
        washer = add_cylinder(f"LS_HW_{label}_wrist_washer_{side}", 5, 1, at, "X")
        boolean(washer, add_cylinder("LS_TOOL_washer_hole", 2.65, 3, at, "X"), "DIFFERENCE")
        washers.append(washer)
    for obj in (shaft, nut, *washers):
        assign(obj, steel)
    return [shaft, nut, *washers]


def _verify_wrist_assembly_parked() -> dict[str, object]:
    """Sample the nominal assembly order, before any preload deforms the fork."""
    from scripts.lab_station_motion_check import tree
    from scripts.lab_station_rig import set_pose

    parts = [
        o
        for o in bpy.context.scene.objects
        if o.type == "MESH"
        and o.name.startswith("LS_")
        and not o.hide_render
        and not o.name.startswith(("LS_CHECK_", "LS_DIAG_"))
    ]
    if len(parts) < 50:
        raise ValueError("Incomplete wrist assembly collision population")
    rows = []
    for label in ("capillary", "pH_temp"):
        for name, sign in (("capillary", -1), ("pH_temp", 1)):
            set_pose(
                bpy.data.objects["LS_CTRL_" + name],
                probe_slide_mm=100,
                yaw_deg=0 if name == label else sign * 45,
            )
        prefix = f"LS_HW_{label}_wrist_"
        axle, nut, left, right = [
            bpy.data.objects[prefix + suffix] for suffix in ("axle", "nut", "washer_-1", "washer_1")
        ]
        steps = [([axle, left], -1, [nut, right]), ([right], 1, [nut]), ([nut], 1, [])]
        for moving, direction, not_installed in steps:
            original = {o.name: o.location.copy() for o in moving}
            obstacles = [o for o in parts if o not in moving and o not in not_installed]
            fixed = {o.name: tree(o) for o in obstacles}
            try:
                for offset in range(40, -1, -2):
                    for obj in moving:
                        obj.location.x = original[obj.name].x + direction * offset / 1000
                    bpy.context.view_layer.update()
                    hits = [
                        (o.name, name)
                        for o in moving
                        for name, solid in fixed.items()
                        if tree(o).overlap(solid)
                    ]
                    if hits:
                        raise ValueError(f"Wrist insertion obstructed: {label}, {offset}, {hits}")
                    rows.append(
                        {
                            "head": label,
                            "moving": [o.name for o in moving],
                            "remaining_mm": offset,
                            "intersections": [],
                        }
                    )
            finally:
                for obj in moving:
                    obj.location = original[obj.name]
                bpy.context.view_layer.update()
    return {
        "samples": rows,
        "scope": "Both probes raised, other arm parked outward 45 degrees; 2 mm sampled straight insertion, nominal unthreaded geometry; no preload, wrench envelope or load qualification.",
    }


def verify_wrist_assembly() -> dict[str, object]:
    """Always restore the assembly pose, including when an insertion is obstructed."""
    from scripts.lab_station_rig import set_pose

    try:
        return _verify_wrist_assembly_parked()
    finally:
        for label in ("capillary", "pH_temp"):
            set_pose(bpy.data.objects["LS_CTRL_" + label], probe_slide_mm=0, yaw_deg=0)
