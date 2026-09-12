"""Use exact straight hardware envelopes to check assembly access, not just hole centres."""

import math

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from scripts.blender_mesh_primitives import add_cylinder
from scripts.lab_station_lift_check import vertices
from scripts.lab_station_motion_check import tree
from src.core.domain.lab_station import LabStationSpec, ProbeClampSpec


def clear_envelope(
    name: str,
    radius: float,
    depth: float,
    point: tuple[float, float, float],
    axis: str,
    parts: dict[str, BVHTree],
    sides: int = 48,
) -> dict[str, object]:
    tool = add_cylinder("LS_DIAG_" + name, radius, depth, point, axis, vertices=sides)
    bpy.context.view_layer.update()
    try:
        swept = tree(tool)
        hits = [name for name, obstacle in parts.items() if swept.overlap(obstacle)]
        if hits:
            raise ValueError(f"Hardware installation path blocked: {name}: {hits}")
        return {
            "operation": name,
            "radius_mm": radius,
            "depth_mm": depth,
            "center_mm": point,
            "axis": axis,
            "intersections": hits,
        }
    finally:
        bpy.data.objects.remove(tool, do_unlink=True)


def verify_clamp_assembly() -> dict[str, object]:
    station, clamp = LabStationSpec(), ProbeClampSpec()
    parts = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        and obj.name.startswith("LS_")
        and not obj.name.startswith(("LS_CHECK_", "LS_DIAG_", "LS_HW_"))
        and not obj.hide_render
    ]
    required_parts = {
        "LS_FIT_" + name
        for name in (
            "chassis",
            "lid",
            "lcd_front",
            "lcd_back",
            "sample_tray",
            "spill_dish",
            "screen_bracket_left",
            "screen_bracket_right",
        )
    }
    required_parts.update(
        f"LS_FIT_{label}_{suffix}"
        for label in ("capillary", "pH_temp")
        for suffix in (
            "clamp_cap",
            "lift_carrier",
            "lift_frame",
            "rod_keeper",
            "shoulder_rotor",
            "liner_0",
            "liner_0_mate",
        )
    )
    required_parts.update({"LS_FIT_pH_temp_liner_1", "LS_FIT_pH_temp_liner_1_mate"})
    required_parts.update(
        f"LS_REF_{label}_{suffix}"
        for label in ("capillary", "pH_temp")
        for suffix in ("guide_rod_-10", "guide_rod_10", "link_0", "link_1")
    )
    required_parts.update(
        "LS_REF_" + name
        for name in (
            "DS18B20",
            "E201C",
            "glass_capillary",
            "lcd_pcb",
            "pH_board_UNCONFIRMED",
            "partition",
            "power_board_UNCONFIRMED",
            "pressure_board_UNCONFIRMED",
            "pump_envelope_UNCONFIRMED",
            "screen_bolt_-1",
            "screen_bolt_1",
            "screen_knob_-1",
            "screen_knob_1",
            "terminal_allowance",
            "touch_glass",
            "vessel_250ml_ENVELOPE",
        )
    )
    missing = required_parts - {o.name for o in parts}
    if missing:
        raise ValueError(f"Incomplete clamp assembly population: {sorted(missing)}")
    part_trees = {o.name: tree(o) for o in parts}
    results = []
    for label, side in (("capillary", -1), ("pH_temp", 1)):
        x, y, pz = station.probe_origin(side)
        z = pz - 28
        cap = bpy.data.objects[f"LS_FIT_{label}_clamp_cap"]
        carrier = bpy.data.objects[f"LS_FIT_{label}_lift_carrier"]
        keeper = bpy.data.objects[f"LS_FIT_{label}_rod_keeper"]
        assert all(obj in parts for obj in (cap, carrier, keeper))
        for dy in clamp.bolt_y_mm:
            # Entire translation union for a 35 mm M3 shaft, then its head.
            results.append(
                clear_envelope(
                    f"{label}_bolt_{dy}", 1.5, 69.4, (x + side * 15.3, y + dy, z), "X", part_trees
                )
            )
            results.append(
                clear_envelope(
                    f"{label}_head_{dy}", 2.75, 35, (x + side * 33.1, y + dy, z), "X", part_trees
                )
            )
            # Hex prism covers nut insertion from outside to the captive seat.
            results.append(
                clear_envelope(
                    f"{label}_nut_{dy}",
                    3.175,
                    18.7,
                    (x - side * 21.85, y + dy, z),
                    "X",
                    part_trees,
                    6,
                )
            )
        for index, (dy, bore) in enumerate(clamp.bores(side > 0)):
            for suffix in ("", "_mate"):
                liner = bpy.data.objects[f"LS_FIT_{label}_liner_{index}{suffix}"]
                points = vertices(liner)
                for direction in (-1, 1):
                    flange = [v for v in points if direction * (v.z * 1000 - z) > 9]
                    assert flange, "No axial liner flange"
                    outer = max(math.hypot(v.x * 1000 - x, v.y * 1000 - y - dy) for v in flange)
                    assert outer >= bore + 0.8, "Liner can slip axially through jaw"
                # Open/closed fits are nominal, before elastic preload is applied.
                assert not tree(liner).overlap(tree(cap)) and not tree(liner).overlap(
                    tree(carrier)
                ), "Uncompressed liner penetrates jaw"
        for dx in (-10, 10):
            rx = x + side * 40 + dx
            top = z + 126
            results.append(
                clear_envelope(
                    f"{label}_keeper_bolt_{dx}", 1.5, 36, (rx, y + 13, top + 7), "Z", part_trees
                )
            )
            results.append(
                clear_envelope(
                    f"{label}_keeper_nut_{dx}",
                    3.175,
                    16,
                    (rx, y + 13, top - 13.5),
                    "Z",
                    part_trees,
                    6,
                )
            )
            rod = bpy.data.objects[f"LS_REF_{label}_guide_rod_{dx}"]
            frame = bpy.data.objects[f"LS_FIT_{label}_lift_frame"]
            for direction, obstruction in ((1, keeper), (-1, frame)):
                values = [v.z for v in vertices(rod)]
                edge = max(values) if direction > 0 else min(values)
                origin = Vector((rx / 1000, y / 1000, edge + direction * 1e-6))
                hit, _, _, distance = tree(obstruction).ray_cast(
                    origin, Vector((0, 0, direction)), 0.001
                )
                assert hit is not None and distance < 0.001, "Rod has no axial retention stop"
    return {
        "assembly_pose": "both slides fully lowered",
        "tested_objects": [o.name for o in parts],
        "hardware_paths": results,
        "hardware": {
            "M3x35_socket_bolt": 4,
            "M3x14_socket_bolt": 4,
            "M3_nut_AF5.5_thickness2.4": 8,
            "M3_washer_OD6.4_thickness0.5": 8,
        },
        "liner_flange_count": 12,
        "rod_stop_count": 8,
        "scope": "Nominal geometry and straight insertion envelopes; no thread, preload, elastic contact or holding-force certification.",
    }


def verify_jaw_service() -> dict[str, object]:
    """Withdraw bolts, park the other head, lower this slide, then open jaw/liner halves."""
    from scripts.lab_station_lift_check import owned_by
    from scripts.lab_station_rig import set_pose

    parts = [
        o
        for o in bpy.context.scene.objects
        if o.type == "MESH"
        and o.name.startswith("LS_")
        and not o.name.startswith(("LS_CHECK_", "LS_DIAG_", "LS_HW_"))
        and not o.hide_render
    ]
    controls = {label: bpy.data.objects["LS_CTRL_" + label] for label in ("capillary", "pH_temp")}
    rows = []

    def check(
        phase: str, value: float, moving: list[bpy.types.Object], fixed: dict[str, BVHTree]
    ) -> None:
        assert moving and fixed
        moving_trees = {o.name: tree(o) for o in moving}
        hits = [
            (name, other)
            for name, shape in moving_trees.items()
            for other, obstacle in fixed.items()
            if shape.overlap(obstacle)
        ]
        if hits:
            raise ValueError(f"Jaw service blocked: {phase} {value}: {hits}")
        rows.append({"phase": phase, "value": value, "intersections": hits})

    for label, side, other in (("capillary", -1, "pH_temp"), ("pH_temp", 1, "capillary")):
        cap = bpy.data.objects[f"LS_FIT_{label}_clamp_cap"]
        suffix = "_mate" if side > 0 else ""
        halves = [
            bpy.data.objects[f"LS_FIT_{label}_liner_{i}{suffix}"]
            for i in range(2 if side > 0 else 1)
        ]
        removable = [cap, *halves]
        saved = {o.name: o.location.copy() for o in removable}
        try:
            for control in controls.values():
                set_pose(control, probe_slide_mm=100)
            parked = [o for o in parts if owned_by(o, controls[other])]
            obstacles = {
                o.name: tree(o)
                for o in parts
                if o not in parked and o.name != f"LS_REF_{other}_root"
            }
            for angle in range(0, 46, 3):
                set_pose(controls[other], yaw_deg=-side * angle)
                check(label + ":park_other", angle, parked, obstacles)
            slide = bpy.data.objects[f"LS_PIVOT_{label}_slide"]
            moving = [o for o in parts if owned_by(o, slide)]
            obstacles = {o.name: tree(o) for o in parts if o not in moving}
            for height in range(100, -1, -5):
                set_pose(controls[label], probe_slide_mm=height)
                check(label + ":lower", height, moving, obstacles)
            obstacles = {o.name: tree(o) for o in parts if o not in removable}
            for distance in range(26):
                for obj in removable:
                    obj.location.x = saved[obj.name].x - side * distance / 1000
                bpy.context.view_layer.update()
                check(label + ":open", distance, removable, obstacles)
        finally:
            for obj in removable:
                obj.location = saved[obj.name]
            for control in controls.values():
                set_pose(control, probe_slide_mm=0, yaw_deg=0)
    return {
        "steps": rows,
        "scope": "Sampled service sequence with clamp bolts withdrawn; park the other head instead of removing its probe. No elastic or load test.",
    }
