"""Trusted local fit prototype; mechanical load and bought-part fit remain unqualified."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.blender_artifact_export import export_stl_mm  # noqa: E402
from scripts.blender_generator_runner import run_generator  # noqa: E402
from scripts.blender_mesh_primitives import (  # noqa: E402
    add_cylinder,
    apply_transform,
    assign,
    boolean,
    cleanup_mesh,
    material,
)
from scripts.hollow_hinge_render import m  # noqa: E402
from scripts.lab_station_arm import (  # noqa: E402
    build_shoulder,
    connect_serrated_joint,
    finish_arm,
    joint_hardware,
    verify_elbow_assembly,
    verify_elbow_release,
    verify_shoulder_release,
)
from scripts.lab_station_clamp import clamp_hardware, lined_jaw, rod_keeper  # noqa: E402
from scripts.lab_station_clamp_check import verify_clamp_assembly, verify_jaw_service  # noqa: E402
from scripts.lab_station_joints import (  # noqa: E402
    add_screen_ears,
    screen_bracket,
    screen_control,
    serrated_plate,
)
from scripts.lab_station_lift import build_lift  # noqa: E402
from scripts.lab_station_lift_check import (  # noqa: E402
    verify_lifts,
    verify_parking,
    verify_screen_at_lift_extremes,
)
from scripts.lab_station_render import render_views  # noqa: E402
from scripts.lab_station_rig import create_arm_rig, verify_independence  # noqa: E402
from scripts.lab_station_wrist import build_wrist, verify_wrist_assembly  # noqa: E402
from src.core.domain.lab_station import LabStationSpec, Point  # noqa: E402

OUTPUT = PROJECT_ROOT / "tmp" / "lab-station-v10"


def box(name: str, size: Point, at: Point, mat: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1, location=tuple(m(v) for v in at))
    obj = bpy.context.object
    obj.name = "LS_" + name
    obj.scale = tuple(m(v) for v in size)
    apply_transform(obj)
    assign(obj, mat)
    return obj


def cylinder(
    name: str, radius: float, depth: float, at: Point, mat: bpy.types.Material, axis: str = "Z"
) -> bpy.types.Object:
    obj = add_cylinder("LS_" + name, radius, depth, at, axis, vertices=48)
    assign(obj, mat)
    return obj


def hole(obj: bpy.types.Object, at: Point, radius: float, depth: float, axis: str = "Z") -> None:
    boolean(obj, add_cylinder("LS_CUT", radius, depth, at, axis), "DIFFERENCE")


def beam(name: str, start: Point, end: Point, mat: bpy.types.Material) -> bpy.types.Object:
    midpoint: Point = tuple((a + b) / 2 for a, b in zip(start, end, strict=True))  # type: ignore[assignment]
    direction = Vector(end) - Vector(start)
    obj = box(name, (14.0, 22.0, direction.length), midpoint, mat)
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    return obj


def export_prototype(obj: bpy.types.Object, name: str) -> dict[str, object]:
    """Export at a local print origin before assembly placement, with an explicit scope label."""
    bpy.context.view_layer.update()
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    bottom = min(point.z for point in points)
    saved = obj.location.copy()
    obj.location.z -= bottom
    bpy.context.view_layer.update()
    path = OUTPUT / "fit-prototypes" / (name + "_mm.stl")
    export_stl_mm([obj], path)
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    bad_edges = sum(not edge.is_manifold for edge in mesh.edges)
    volume = abs(mesh.calc_volume()) * 1e9
    mesh.free()
    dimensions = [round(float(v) * 1000, 3) for v in obj.dimensions]
    check = obj.copy()
    check.data = obj.data.copy()
    group = (
        "clamp_"
        if any(tag in name for tag in ("_clamp_", "_liner_", "_rod_keeper"))
        else ("arm_" if "_arm_" in name else ("lift_" if "_lift_" in name else "fit_"))
    )
    check.name = "LS_CHECK_" + group + name
    bpy.context.collection.objects.link(check)
    check.location.x = m(260 * len([o for o in scene_objects() if o.name.startswith("LS_CHECK_")]))
    check.location.y = m(450)
    bpy.context.view_layer.update()
    check.hide_render = True
    check.hide_viewport = True
    obj.location = saved
    if bad_edges or volume <= 0 or any(dimension > 240 for dimension in dimensions[:2]):
        raise RuntimeError(f"Prototype geometry failed: {name}, {dimensions}, {bad_edges}")
    return {
        "file": str(path.relative_to(OUTPUT)),
        "dimensions_mm": dimensions,
        "non_manifold_edges": bad_edges,
        "volume_mm3": round(volume, 3),
        "use": "fit prototype only; assembly, retention and loads not validated",
    }


def scene_objects() -> list[bpy.types.Object]:
    return list(bpy.context.scene.objects)


def build() -> None:
    spec = LabStationSpec()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.unit_settings.scale_length = 1.0
    white = material("LS_WHITE", (0.76, 0.82, 0.85, 1))
    dark = material("LS_DARK", (0.07, 0.105, 0.13, 1))
    teal = material("LS_TEAL", (0.04, 0.51, 0.53, 1))
    amber = material("LS_AMBER", (0.95, 0.47, 0.10, 1))
    steel = material("LS_STEEL", (0.55, 0.63, 0.69, 1), 0.6)
    soft = material("LS_SOFT", (0.22, 0.22, 0.24, 1))
    blue = material("LS_BLUE", (0.10, 0.30, 0.49, 1))
    parts: list[dict[str, object]] = []

    # Rear chassis and front sample platform share an assembly seam, not a 300 mm print.
    chassis = box("FIT_chassis", (230, 150, 76), (0, 0, 38), white)
    wall = spec.wall_mm
    boolean(
        chassis,
        box("CUT", (230 - 2 * wall, 150 - 2 * wall, 78), (0, 0, 39 + 2 * wall), white),
        "DIFFERENCE",
    )
    for x in (-100.0, 100.0):
        for y in (-60.0, 60.0):
            boss = cylinder("BOSS", 6, 70.2, (x, y, 40.9), white)
            boolean(chassis, boss, "UNION")
            hole(chassis, (x, y, 72), 1.6, 12)
    # Removable-connector-panel opening; actual connectors are not frozen yet.
    boolean(chassis, box("CUT", (80, 10, 22), (0, 74, 36), white), "DIFFERENCE")
    parts.append(export_prototype(chassis, "chassis"))
    lid = box("FIT_lid", (230, 150, 4), (0, 0, 2), white)
    for x in (-100.0, 100.0):
        for y in (-60.0, 60.0):
            hole(lid, (x, y, 2), 1.8, 8)
    for x in (-93.0, 93.0):
        for y in (-64.0, -34.0):
            hole(lid, (x, y, 2), 1.8, 8)
    parts.append(export_prototype(lid, "lid"))
    lid.location.z += m(76)
    tray = box("FIT_sample_tray", spec.base_panel_mm, (0, 0, 3), teal)
    parts.append(export_prototype(tray, "sample_platform"))
    tray.location.y = m(-150)
    # Removable spill dish; its size is an assumed container envelope, not 250 ml geometry.
    dish = cylinder("FIT_spill_dish", 51, 9, (0, 0, 4.5), white)
    boolean(dish, cylinder("CUT", 48, 10, (0, 0, 8), white), "DIFFERENCE")
    parts.append(export_prototype(dish, "spill_dish"))
    dish.location = (0, m(-145), m(10.5))

    # Tilted HMI: the front panel uses the official glass outline with a 0.4 mm side allowance.
    frame = box("FIT_lcd_front", (150, 110, 6), (0, 0, 3), dark)
    pocket_x, pocket_y = spec.lcd_pocket_mm
    boolean(frame, box("CUT", (pocket_x, pocket_y, 6), (0, 0, 1), dark), "DIFFERENCE")
    boolean(frame, box("CUT", (*spec.lcd_window_mm, 12), (0, 0, 3), dark), "DIFFERENCE")
    for x in (-69.0, 69.0):
        for y in (-49.0, 49.0):
            hole(frame, (x, y, 3), 1.8, 12)
    for side in (-1, 1):
        boolean(frame, cylinder("CUT", 2.8, 25, (side * 79, -55, 0), dark, "X"), "DIFFERENCE")
    cleanup_mesh(frame)
    parts.append(export_prototype(frame, "lcd_front"))
    back = box("FIT_lcd_back", (150, 110, 36), (0, 0, -18), white)
    boolean(back, box("CUT", (144, 104, 38), (0, 0, -13), white), "DIFFERENCE")
    for x in (-69.0, 69.0):
        for y in (-49.0, 49.0):
            boolean(back, cylinder("BOSS", 4, 31, (x, y, -16.5), white), "UNION")
            hole(back, (x, y, -5), 1.6, 12)
    boolean(back, box("CUT", (50, 10, 18), (0, -54, -16), white), "DIFFERENCE")
    add_screen_ears(back, white)
    parts.append(export_prototype(back, "lcd_back"))
    # Reference hardware is deliberately absent from the STL allowlist.
    screen = box("REF_touch_glass", (127.7, 87.45, 1.4), (0, 0, 2), blue)
    pcb = box("REF_lcd_pcb", (120.5, 75.5, 1.6), (0, 0, -8), teal)
    terminals = box("REF_terminal_allowance", (98, 14, 15), (0, -29, -18), teal)
    bpy.ops.object.empty_add()
    hmi = bpy.context.object
    hmi.name = "LS_REF_HMI_mount"
    for obj in (frame, back, screen, pcb, terminals):
        obj.parent = hmi
    screen_pivot = screen_control(hmi)
    for side in (-1, 1):
        bracket = screen_bracket(side, dark)
        parts.append(
            export_prototype(bracket, "screen_bracket_" + ("left" if side < 0 else "right"))
        )
        cylinder(f"REF_screen_bolt_{side}", 2.5, 28, (side * 91, -49, 128), steel, "X")
        cylinder(
            f"REF_screen_knob_{side}", 11 if side < 0 else 5, 8, (side * 107, -49, 128), teal, "X"
        )
    coupon = serrated_plate("LS_FIT_serrated_coupon", amber)
    parts.append(export_prototype(coupon, "serrated_coupon_print_two"))
    coupon.hide_render = True
    coupon.hide_viewport = True

    # Two separated circuit envelopes and pump envelope, visible in the service view.
    internals = [
        box("REF_pump_envelope_UNCONFIRMED", (60, 35, 35), (-61, 22, 27.5), amber),
        box("REF_pressure_board_UNCONFIRMED", (55, 35, 15), (-62, -34, 17.5), teal),
        box("REF_pH_board_UNCONFIRMED", (65, 45, 15), (53, -26, 17.5), teal),
        box("REF_power_board_UNCONFIRMED", (60, 28, 15), (52, 33, 17.5), dark),
        box("REF_partition", (3, 120, 46), (-8, 0, 29), white),
    ]
    # Assumed 70 mm body / 95 mm height. Open top permits inspection of all three probes.
    cup = cylinder("REF_vessel_250ml_ENVELOPE", 35, 95, (0, -145, 62.5), steel)
    boolean(cup, cylinder("CUT", 33, 100, (0, -145, 68), steel), "DIFFERENCE")
    arms = []
    for side, color, label in ((-1, amber, "capillary"), (1, teal, "pH_temp")):
        root, elbow, wrist = spec.arm_points(side)
        necks = spec.elbow_necks(side)
        groups: list[list[bpy.types.Object]] = [[], [], [], []]
        bases: list[bpy.types.Object] = []
        for index, b in enumerate((elbow, wrist)):
            end = (b[0], b[1], b[2] + 26) if index == 1 else b
            start = spec.shoulder_neck(side) if index == 0 else necks[1]
            end = necks[0] if index == 0 else end
            link = beam(f"REF_{label}_link_{index}", start, end, color)
            arms.append(link)
            groups[index].append(link)
        connect_serrated_joint(groups[0][0], groups[1][0], elbow, necks, label, color, beam)
        rotor, shoulder_hardware = build_shoulder(
            groups[0][0], root, spec.shoulder_neck(side), label, color, steel, beam
        )
        bolt, nut, left, right = shoulder_hardware
        bases.extend([rotor, bolt, left])
        groups[0].extend([nut, right])
        apply_transform(rotor)
        parts.append(export_prototype(rotor, label + "_arm_shoulder_rotor"))
        finish_arm(groups[0][0])
        apply_transform(groups[0][0])
        parts.append(export_prototype(groups[0][0], label + "_arm_upper"))
        elbow_bolt, elbow_nut, elbow_left, elbow_right = joint_hardware(elbow, label, steel)
        groups[0].extend([elbow_bolt, elbow_left])
        groups[1].extend([elbow_nut, elbow_right])
        probe = spec.probe_origin(side)
        frame_lift, carrier_lift, rods = build_lift(label, side, probe, color, steel)
        wrist_hardware = build_wrist(frame_lift, groups[1][0], wrist, label, color, steel)
        groups[2].extend(wrist_hardware)
        finish_arm(groups[1][0])
        apply_transform(groups[1][0])
        parts.append(export_prototype(groups[1][0], label + "_arm_lower"))
        cap, liners = lined_jaw(carrier_lift, label, side, probe, color, soft)
        keeper = rod_keeper(frame_lift, label, side, probe, color)
        for obj in [cap, keeper, *liners]:
            parts.append(export_prototype(obj, obj.name.removeprefix("LS_FIT_")))
        parts.append(export_prototype(frame_lift, label + "_lift_frame"))
        parts.append(export_prototype(carrier_lift, label + "_lift_carrier"))
        moving_hardware, fixed_hardware = clamp_hardware(label, side, probe, steel)
        groups[2].extend([frame_lift, keeper, *rods, *fixed_hardware])
        groups[3].extend([carrier_lift, cap, *liners, *moving_hardware])
        if side == -1:
            groups[3].append(
                cylinder("REF_glass_capillary", 3, 102, (probe[0], probe[1], probe[2] - 69), steel)
            )
        else:
            for dy, radius, name in ((-6.0, 6.0, "E201C"), (8.0, 3.0, "DS18B20")):
                y = probe[1] + dy
                groups[3].append(
                    cylinder("REF_" + name, radius, 115, (probe[0], y, probe[2] - 69), steel)
                )
        create_arm_rig(
            label, (root, elbow, wrist), groups[0], groups[1], groups[2], groups[3], bases
        )

    (OUTPUT / "shoulder-release.json").write_text(json.dumps(verify_shoulder_release(), indent=2))
    (OUTPUT / "clamp-assembly.json").write_text(
        json.dumps(verify_clamp_assembly(), indent=2) + "\n"
    )
    (OUTPUT / "jaw-service.json").write_text(json.dumps(verify_jaw_service(), indent=2) + "\n")
    (OUTPUT / "wrist-assembly.json").write_text(
        json.dumps(verify_wrist_assembly(), indent=2) + "\n"
    )
    (OUTPUT / "elbow-assembly.json").write_text(
        json.dumps(verify_elbow_assembly(), indent=2) + "\n"
    )
    (OUTPUT / "elbow-release.json").write_text(json.dumps(verify_elbow_release(), indent=2) + "\n")
    (OUTPUT / "probe-lift.json").write_text(json.dumps(verify_lifts(), indent=2) + "\n")
    (OUTPUT / "probe-parking.json").write_text(json.dumps(verify_parking(), indent=2) + "\n")
    (OUTPUT / "joint-motion.json").write_text(
        json.dumps(verify_screen_at_lift_extremes(), indent=2) + "\n"
    )
    independence = verify_independence(("capillary", "pH_temp"))
    (OUTPUT / "independent-motion.json").write_text(json.dumps(independence, indent=2) + "\n")

    camera = render_views(OUTPUT, lid, screen_pivot, chassis, cup, coupon)
    scene["LS_PARTS"] = sorted(
        obj.name for obj in scene_objects() if obj.name.startswith("LS_CHECK_")
    )
    # Hide presentation furniture; the model alone opens at a useful scale.
    camera.hide_set(True)
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            area.spaces.active.region_3d.view_distance = 0.65
            area.spaces.active.region_3d.view_location = (0, -0.075, 0.095)
            area.spaces.active.clip_start = 0.0001
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "lab_station_v10.blend"))
    manifest = {
        "stage": "straight-extraction-and-fit-prototype",
        "project_version": (PROJECT_ROOT / "VERSION").read_text().strip(),
        "manufacturing_release": False,
        "units": "mm",
        "parts": parts,
        "arm_points_mm": {str(side): spec.arm_points(side) for side in (-1, 1)},
        "nominal_link_centers_mm": spec.link_mm,
        "unconfirmed": ["vessel dimensions", "probe sizes", "pump", "circuit boards", "material"],
        "not_validated": [
            "locking",
            "glass clamping",
            "tip stability",
            "assembly fasteners",
            "continuous full-arm and cable collision sweep",
        ],
        "reference_objects": [obj.name for obj in [*internals, *arms]],
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (OUTPUT / "README.md").write_text(
        (PROJECT_ROOT / "docs/verification/lab-station/10-model.md").read_text()
    )
    print("LAB_STATION_PROTOTYPE_READY", str(OUTPUT))


def main() -> None:
    run_generator(build, prefix="LS_")


if __name__ == "__main__":
    main()
