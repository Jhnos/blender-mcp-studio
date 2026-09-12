"""Two-rod extraction stage; geometry uses the shared primitive/Boolean ports."""

import bpy

from scripts.blender_mesh_primitives import add_cylinder, assign, boolean, cleanup_mesh
from scripts.lab_station_joints import block
from src.core.domain.lab_station import Point


def build_lift(
    label: str, side: int, probe: Point, mat: bpy.types.Material, steel: bpy.types.Material
) -> tuple[bpy.types.Object, bpy.types.Object, list[bpy.types.Object]]:
    """Return fixed frame, moving carrier and reference Ø8 rods at the low position."""
    px, y, pz = probe
    x, z = px + side * 40, pz - 28
    frame = block(f"LS_FIT_{label}_lift_frame", (36, 8, 144), (x, y + 28, z + 50), mat)
    for level in (-22, 122):
        boolean(frame, block("LS_TOOL_end", (36, 42, 8), (x, y + 11, z + level), mat), "UNION")
    # A rear mounting pad stays behind the complete moving-carrier sweep.
    boolean(frame, block("LS_TOOL_mount", (58, 20, 12), ((px + x) / 2, y + 36, pz), mat), "UNION")
    for hole_x in (px - 6, px + 6):
        boolean(
            frame,
            add_cylinder("LS_TOOL_mount_hole", 1.8, 24, (hole_x, y + 36, pz), "Y"),
            "DIFFERENCE",
        )
    carrier = block(f"LS_FIT_{label}_lift_carrier", (36, 20, 32), (x, y, z), mat)
    boolean(carrier, block("LS_TOOL_reach", (40, 12, 12), ((x + px) / 2, y - 4, z), mat), "UNION")
    rods = []
    for dx in (-10, 10):
        rx = x + dx
        boolean(frame, add_cylinder("LS_TOOL_rod_seat", 4.2, 151, (rx, y, z + 53)), "DIFFERENCE")
        boolean(carrier, add_cylinder("LS_TOOL_slide_bore", 4.2, 36, (rx, y, z)), "DIFFERENCE")
        rod = add_cylinder(f"LS_REF_{label}_guide_rod_{dx}", 4, 148, (rx, y, z + 52))
        assign(rod, steel)
        rods.append(rod)
    # Front-access M4 nut pocket, shaft hole and rod-contact locking point.
    boolean(
        carrier,
        add_cylinder("LS_TOOL_lock_bore", 2.2, 12, (x + side * 10, y - 6, z), "Y"),
        "DIFFERENCE",
    )
    boolean(
        carrier,
        add_cylinder("LS_TOOL_lock_nut", 4.2, 3.4, (x + side * 10, y - 8.4, z), "Y", vertices=6),
        "DIFFERENCE",
    )
    cleanup_mesh(frame)
    cleanup_mesh(carrier)
    return frame, carrier, rods
