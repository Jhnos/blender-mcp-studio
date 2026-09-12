"""Visible rotary-lift concept; no printable or load-qualified release is claimed."""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import bpy
from mathutils import Vector

from scripts.blender_artifact_export import export_world_mesh_copy_mm
from scripts.blender_mesh_primitives import add_cylinder, assign, boolean, material
from scripts.lab_station_arm import (
    build_shoulder,
    connect_serrated_joint,
    finish_arm,
    joint_hardware,
    rotary_pivot_hardware,
)
from scripts.lab_station_base import build_base_mounts, verify_base_mounts
from scripts.lab_station_clamp import lined_jaw
from scripts.lab_station_joints import block
from scripts.lab_station_motion_check import (
    tree,
    verify_coupled_motion,
    verify_rotary_elbow_assembly,
    verify_rotary_elbow_tools,
    verify_rotary_elbows,
    verify_rotary_screen,
    verify_rotary_support_meshes,
)
from scripts.lab_station_render import render_rotary_views
from scripts.lab_station_rig import (
    attach,
    create_rotary_support_rig,
    driver,
    pivot,
    set_pose,
    verify_rotary_articulation,
)
from scripts.lab_station_wrist import build_wrist, verify_rotary_wrist_interfaces
from src.core.domain.lab_station import LabStationSpec, Point, RotaryLiftSpec

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tmp/lab-station-rotary"
HEAD_OFFSET_MM = 74.0


def beam(name: str, a: Point, b: Point, mat: bpy.types.Material) -> bpy.types.Object:
    direction = Vector(b) - Vector(a)
    center: Point = tuple((a[i] + b[i]) / 2 for i in range(3))  # type: ignore[assignment]
    obj = block(name, (6, 12, direction.length), (0, 0, 0), mat)
    obj.location = tuple(v / 1000 for v in center)
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    return obj


def bar(name: str, a: Point, b: Point, mat: bpy.types.Material) -> bpy.types.Object:
    obj = beam(name, a, b, mat)
    for point in (a, b):
        boolean(obj, add_cylinder("LR_TOOL_ear", 8, 6, point, "X"), "UNION")
        boolean(obj, add_cylinder("LR_TOOL_bore", 4.1, 8, point, "X"), "DIFFERENCE")
    return obj


def offset(a: Point, b: Point) -> Point:
    return a[0] + b[0], a[1] + b[1], a[2] + b[2]


def build_head(label: str, side: int, mat: bpy.types.Material, metal: bpy.types.Material) -> None:
    spec, lift = LabStationSpec(), RotaryLiftSpec()
    px, py, pz = spec.probe_origin(side)
    origin = (px + side * HEAD_OFFSET_MM, py, pz - 10)
    a, b, c, d = [offset(p, origin) for p in lift.joints(0)]
    control = pivot("LR_CTRL_" + label, (0, 0, 0))
    length, half = lift.length_mm, lift.stroke_mm / 2
    reach = math.sqrt(length**2 - half**2)
    control["lift_mm"] = 0.0
    control.id_properties_ui("lift_mm").update(
        min=0.0, max=lift.stroke_mm, description="Rotary four-bar lift, mm; concept only"
    )
    base = block("LR_" + label + "_fixed", (12, 16, 58), offset(a, (0, 0, 20)), mat)
    head = block("LR_" + label + "_head", (12, 16, 68), offset(c, (0, 0, 20)), mat)
    bridge = block("LR_TOOL_bridge", (76, 14, 12), (px + side * 38, py, pz - 28), mat)
    bpy.context.view_layer.update()
    boolean(head, bridge, "UNION")
    cap, liners = lined_jaw(
        head, label, side, (px, py, pz), mat, material("LR_soft", (0.16, 0.18, 0.19, 1))
    )
    for obj in (cap, *liners):
        obj.name = "LR_" + obj.name.removeprefix("LS_FIT_")
    moving = pivot("LR_" + label + "_moving", (0, 0, 0))
    for obj in (head, cap, *liners):
        attach(obj, moving)
    driver(
        moving,
        control,
        "location",
        1,
        f"({reach!r}-sqrt({length**2!r}-(lift_mm-{half!r})**2))*0.001",
        ("lift_mm",),
    )
    driver(moving, control, "location", 2, "lift_mm*0.001", ("lift_mm",))
    for index, (start, end) in enumerate(((a, c), (b, d))):
        for body, point in ((base, start), (head, end)):
            boolean(body, add_cylinder("LR_TOOL_hole", 4.1, 16, point, "X"), "DIFFERENCE")
        shift = (side * 11, 0, 0)
        start, end = offset(start, shift), offset(end, shift)
        link = bar(f"LR_{label}_bar_{index}", start, end, mat)
        bpy.context.view_layer.update()
        for key, point in (("joint_a", start), ("joint_b", end)):
            link[key] = list(link.matrix_world.inverted() @ (Vector(point) / 1000))
        hinge = pivot(f"LR_{label}_hinge_{index}", start)
        attach(link, hinge)
        driver(
            hinge,
            control,
            "rotation_euler",
            0,
            f"-asin((lift_mm-{half!r})/{length!r})+{math.asin(-half / length)!r}",
            ("lift_mm",),
        )
        for name, point, parent in (("base", start, None), ("head", end, moving)):
            hardware = rotary_pivot_hardware(
                f"LR_{label}_pin_{index}_{name}", offset(point, (-side * 11, 0, 0)), side, metal
            )
            if parent is not None:
                for part in hardware:
                    attach(part, parent)
    probe_data = (
        (("glass", 0, 3, 102),) if side < 0 else (("pH", -6, 6, 115), ("temperature", 8, 3, 115))
    )
    for name, dy, radius, length in probe_data:
        obj = add_cylinder(f"LR_{label}_probe_{name}", radius, length, (px, py + dy, pz - 69))
        assign(obj, metal)
        attach(obj, moving)
    # Adjustable support is an envelope here; no hidden claim of assembled pivots.
    root = spec.arm_points(side)[0]
    middle = (root[0] + side * 25, (root[1] + a[1]) / 2, a[2] - 20)
    wrist = offset(a, (0, 82, 0))
    neck = offset(wrist, (0, 0, 26))
    upper_neck = offset(middle, (-14, 30, 0))
    lower_neck = offset(middle, (14, 30, 0))
    shoulder_neck = offset(root, (13, 0, 30))
    upper = beam(f"LR_{label}_support_envelope_0", shoulder_neck, upper_neck, mat)
    turn = (neck[0], lower_neck[1], neck[2] + 25)
    ascent = (lower_neck[0], lower_neck[1], turn[2])
    lower = beam(f"LR_{label}_support_envelope_1", lower_neck, ascent, mat)
    boolean(lower, beam("LR_TOOL_lower_cross", ascent, turn, mat), "UNION")
    boolean(lower, beam("LR_TOOL_lower_return", turn, neck, mat), "UNION")
    boolean(base, block("LR_TOOL_wrist_bridge", (12, 82, 12), offset(a, (0, 41, 0)), mat), "UNION")
    wrist_hardware = build_wrist(base, lower, wrist, label, mat, metal)
    for obj in wrist_hardware:
        obj.name = "LR_" + obj.name.removeprefix("LS_HW_")
    connect_serrated_joint(upper, lower, middle, (upper_neck, lower_neck), label, mat, beam)
    mount, shoulder_hardware = build_shoulder(
        upper, root, shoulder_neck, label, mat, metal, beam, neck_plane_mm=12
    )
    mount.name = f"LR_{label}_mount_envelope"
    for obj in shoulder_hardware:
        obj.name = "LR_" + obj.name.removeprefix("LS_HW_")
    for member in (upper, lower):
        finish_arm(member)
    hardware = joint_hardware(middle, label, metal)
    boolean(
        hardware[0],
        add_cylinder(
            "LR_TOOL_elbow_hex", 2.42, 3.6, offset(middle, (-31.3, 0, 0)), "X", vertices=6
        ),
        "DIFFERENCE",
    )
    for obj in hardware:
        obj.name = "LR_" + obj.name.removeprefix("LS_HW_")
    create_rotary_support_rig(label, root, middle, wrist)
    for obj in wrist_hardware:
        attach(obj, bpy.data.objects[f"LR_PIVOT_{label}_elbow"])
    for obj in shoulder_hardware:
        owner = "yaw" if obj.name.endswith(("bolt", "washer_left")) else "shoulder"
        attach(obj, bpy.data.objects[f"LR_PIVOT_{label}_{owner}"])
    for obj in hardware:
        owner = "shoulder" if obj.name.endswith(("bolt", "washer_left")) else "elbow"
        attach(obj, bpy.data.objects[f"LR_PIVOT_{label}_{owner}"])
    for suffix in ("mount_envelope", "fixed", "head", "bar_0", "bar_1"):
        finish_arm(bpy.data.objects[f"LR_{label}_{suffix}"])
    bpy.context.view_layer.update()


def verify() -> dict[str, object]:
    rows = []
    spec = LabStationSpec()
    cup = bpy.data.objects["LS_REF_vessel_250ml_ENVELOPE"]
    for label, side in (("capillary", -1), ("pH_temp", 1)):
        control = bpy.data.objects["LR_CTRL_" + label]
        other = "pH_temp" if side < 0 else "capillary"
        other_head = bpy.data.objects[f"LR_{other}_head"]
        baseline = other_head.matrix_world.copy()
        head = bpy.data.objects[f"LR_{label}_head"]
        probes = [o for o in bpy.data.objects if o.name.startswith(f"LR_{label}_probe_")]
        if len(probes) != (1 if side < 0 else 2):
            raise ValueError("Missing rotary probes")
        try:
            for amount in range(101):
                set_pose(control, lift_mm=amount)
                drift = max(
                    abs(other_head.matrix_world[r][c] - baseline[r][c])
                    for r in range(4)
                    for c in range(4)
                )
                if drift > 1e-8 or head.matrix_world.to_quaternion().angle > 1e-6:
                    raise ValueError("Rotary head independence/orientation failed")
                hits = [o.name for o in probes if tree(o).overlap(tree(cup))]
                if hits:
                    raise ValueError(f"Probe hit vessel at {amount}: {hits}")
                origin = offset(spec.probe_origin(side), (side * HEAD_OFFSET_MM, 0, -10))
                expected = [
                    Vector(offset(p, origin)) / 1000 for p in RotaryLiftSpec().joints(amount)
                ]
                for i in (0, 1):
                    link = bpy.data.objects[f"LR_{label}_bar_{i}"]
                    for key, target in (("joint_a", expected[i]), ("joint_b", expected[i + 2])):
                        actual_joint = link.matrix_world @ Vector(link[key])
                        target = target + Vector((side * 11 / 1000, 0, 0))
                        if (actual_joint - target).length > 1e-6:
                            raise ValueError("Rotating link does not close at its physical pivot")
                    pin = bpy.data.objects[f"LR_{label}_pin_{i}_head"]
                    # Pin centres are offset from the bar's plane, by design.
                    actual = pin.matrix_world.translation - Vector((side * 8 / 1000, 0, 0))
                    if (actual - expected[i + 2]).length > 1e-6:
                        raise ValueError("Four-bar head pivot did not follow the analytical path")
                rows.append({"head": label, "lift_mm": amount, "vessel_intersections": hits})
        finally:
            set_pose(control, lift_mm=0)
    return {
        "samples": rows,
        "scope": "202 sampled probe/vessel checks and independent vertical heads; supports, all-link collision, retention and loads are not qualified.",
    }


def inspect_assembly_motion() -> dict[str, object]:
    """Report unresolved full-scene collisions without presenting them as acceptance."""
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH" and not o.hide_render]
    hits = []
    static_hits = []
    contacts = []
    for obj in meshes:
        if not obj.name.startswith("LR_") or not (
            obj.name.endswith("_base")
            or any(tag in obj.name for tag in ("_fixed", "support_envelope", "mount_envelope"))
        ):
            continue
        for other in meshes:
            if not other.name.startswith("LS_") or not tree(obj).overlap(tree(other)):
                continue
            minimum = min((obj.matrix_world @ v.co).z for v in obj.data.vertices) * 1000
            if (
                "mount_envelope" in obj.name
                and other.name == "LS_FIT_lid"
                and (minimum >= 79.99 or obj.get("yaw_spigot"))
            ):
                contacts.append({"mount": obj.name, "bottom_mm": minimum})
            else:
                static_hits.append((obj.name, other.name))
    for label in ("capillary", "pH_temp"):
        control = bpy.data.objects["LR_CTRL_" + label]
        moving = [
            o
            for o in meshes
            if o.name.startswith("LR_" + label + "_")
            and not any(tag in o.name for tag in ("support_envelope", "mount_envelope", "_fixed"))
            and not o.name.endswith("_base")
        ]
        obstacles = {o.name: tree(o) for o in meshes if o not in moving}
        try:
            for amount in range(0, 101, 5):
                set_pose(control, lift_mm=amount)
                for obj in moving:
                    mesh = tree(obj)
                    for name, obstacle in obstacles.items():
                        if mesh.overlap(obstacle):
                            hits.append(
                                {
                                    "head": label,
                                    "lift_mm": amount,
                                    "moving": obj.name,
                                    "obstacle": name,
                                }
                            )
        finally:
            set_pose(control, lift_mm=0)
    return {
        "unresolved_surface_collisions": hits,
        "unresolved_static_collisions": static_hits,
        "nominal_mount_contacts": contacts,
        "scope": "Each head at 21 poses against other stationary meshes; not continuous or simultaneous motion, no containment or load qualification.",
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    baseline = OUTPUT / "baseline.blend"
    shutil.copyfile(ROOT / "tmp/lab-station-v10/lab_station_v10.blend", baseline)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    with bpy.data.libraries.load(str(baseline), link=False) as (source, target):
        target.objects = source.objects
    for obj in target.objects:
        if obj is not None:
            bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.update()
    bpy.context.scene.camera = bpy.data.objects["LS_VIEW_camera"]
    prefixes = (
        "LS_CHECK_",
        "LS_CTRL_",
        "LS_PIVOT_",
        "LS_REF_capillary",
        "LS_REF_pH_temp",
        "LS_FIT_capillary",
        "LS_FIT_pH_temp",
        "LS_HW_capillary",
        "LS_HW_pH_temp",
        "LR_",
    )
    names = {"LS_REF_glass_capillary", "LS_REF_E201C", "LS_REF_DS18B20", "LS_FIT_serrated_coupon"}
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefixes) or obj.name in names:
            bpy.data.objects.remove(obj, do_unlink=True)
    metal = material("LR_metal", (0.46, 0.5, 0.53, 1))
    for label, side, color in (
        ("capillary", -1, (0.95, 0.52, 0.12, 1)),
        ("pH_temp", 1, (0.05, 0.6, 0.64, 1)),
    ):
        build_head(label, side, material("LR_" + label, color), metal)
    build_base_mounts(metal)
    (OUTPUT / "base-retention.json").write_text(json.dumps(verify_base_mounts(), indent=2))
    (OUTPUT / "wrist-interface.json").write_text(
        json.dumps(verify_rotary_wrist_interfaces(), indent=2)
    )
    (OUTPUT / "support-mesh.json").write_text(json.dumps(verify_rotary_support_meshes(), indent=2))
    (OUTPUT / "elbow-assembly.json").write_text(
        json.dumps(verify_rotary_elbow_assembly(), indent=2)
    )
    (OUTPUT / "elbow-tools.json").write_text(json.dumps(verify_rotary_elbow_tools(), indent=2))
    (OUTPUT / "shoulder-release.json").write_text(
        json.dumps(verify_rotary_elbows("shoulder"), indent=2)
    )
    (OUTPUT / "elbow-release.json").write_text(json.dumps(verify_rotary_elbows(), indent=2))
    (OUTPUT / "articulation.json").write_text(json.dumps(verify_rotary_articulation(), indent=2))
    (OUTPUT / "motion.json").write_text(json.dumps(verify(), indent=2))
    (OUTPUT / "coupled-motion.json").write_text(json.dumps(verify_coupled_motion(), indent=2))
    (OUTPUT / "screen-motion.json").write_text(json.dumps(verify_rotary_screen(), indent=2))
    assembly = inspect_assembly_motion()
    (OUTPUT / "assembly-motion.json").write_text(json.dumps(assembly, indent=2))
    if assembly["unresolved_surface_collisions"] or assembly["unresolved_static_collisions"]:
        raise ValueError("Rotary concept has unresolved assembly collisions")
    render_rotary_views(OUTPUT)
    scene = bpy.context.scene
    checks: list[str] = []
    for label in ("capillary", "pH_temp"):
        for index in (0, 1):
            name = f"LR_CHECK_{label}_{index}"
            export_world_mesh_copy_mm(
                bpy.data.objects[f"LR_{label}_support_envelope_{index}"],
                OUTPUT / "fit-prototypes" / (name + "_mm.stl"),
                name,
                260 * len(checks),
            )
            checks.append(name)
    scene["LR_PARTS"] = checks
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "rotary-concept.blend"))


if __name__ == "__main__":
    main()
