"""Electrode-holder concept: retained upper hinge, parallel forearm, triangular head carrier."""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import bpy
from mathutils import Matrix

from scripts.blender_mesh_primitives import add_cylinder, assign, boolean, loft_rings
from scripts.lab_electrode_check import (
    verify_clamps,
    verify_forearm_stack,
    verify_head_envelopes,
    verify_platform_geometry,
    verify_pose,
    verify_service_tilt,
)
from scripts.lab_electrode_check import (
    verify_knobs as verify_knobs,
)
from scripts.lab_electrode_check import (
    verify_local as verify_local,
)
from scripts.lab_electrode_check import (
    verify_pins as verify_pins,
)
from scripts.lab_electrode_closure import (
    apply_shoulder_release,
    apply_take_up,
    verify_joint_release,
    verify_joint_teeth,
    verify_pin_service,
    verify_seated,
    verify_take_up,
    verify_wrist_geometry,
)
from scripts.lab_station_arm import finish_arm
from scripts.lab_station_clamp import compact_probe_head
from scripts.lab_station_joints import electrode_joint_teeth, hand_knob_hardware, retained_pivot
from scripts.lab_station_render import configure_electrode_view, render_electrode_details
from scripts.lab_station_rig import set_pose
from scripts.model_lab_simple import link, verify_clearance
from src.core.domain.lab_station import ElectrodeArmSpec
from src.core.domain.lab_station_joints import ElbowClosureSpec

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tmp/lab-station-electrode-slim-wrist"


def bake(obj: bpy.types.Object, side: int) -> None:
    obj.data.transform(obj.matrix_world)
    obj.matrix_world = Matrix.Identity(4)
    if side > 0:
        obj.data.transform(Matrix.Diagonal((-1, 1, 1, 1)))
    finish_arm(obj)


def build(label: str) -> None:
    side = -1 if label == "capillary" else 1
    prefix = "S_" + label + "_"
    mat = bpy.data.objects[prefix + "upper"].data.materials[0]
    for suffix, x in (("upper", 4.2), ("lower", -4.2)):
        bpy.data.objects.remove(bpy.data.objects[prefix + suffix], do_unlink=True)
        obj = link(prefix + suffix, x, mat, radius_mm=11)
        if suffix == "upper":
            boolean(obj, add_cylinder("E_TOOL", 11, 8, (x, 0, 126), "X"), "UNION")
            finish_arm(obj)
            boolean(obj, add_cylinder("E_TOOL", 2.7, 40, (x, 0, 126), "X"), "DIFFERENCE")
            finish_arm(obj)
        if suffix == "upper":
            for z in (0, 150):
                boolean(
                    obj, add_cylinder("E_TOOL", 4.8, 5, (6.6, 0, z), "X", vertices=6), "DIFFERENCE"
                )
                finish_arm(obj)
        bake(obj, side)
    obj = link(prefix + "follower", -4.2, mat, radius_mm=11)
    bake(obj, side)
    spec = ElectrodeArmSpec()
    vertices = ((0, 0), (0, -24), (spec.platform_offset_mm, 0))
    obj = loft_rings(prefix + "platform", [[(x, y, z) for y, z in vertices] for x in (0.2, 8.2)])
    assign(obj, mat)
    for y, z in vertices:
        boolean(
            obj, add_cylinder("E_TOOL", spec.platform_boss_radius_mm, 8, (4.2, y, z), "X"), "UNION"
        )
        finish_arm(obj)
    for y, z in vertices:
        boolean(obj, add_cylinder("E_TOOL", 2.7, 30, (4.2, y, z), "X"), "DIFFERENCE")
        finish_arm(obj)
    boolean(
        obj,
        add_cylinder("E_TOOL", 4.8, 5, (6.6, spec.platform_offset_mm, 0), "X", vertices=6),
        "DIFFERENCE",
    )
    bake(obj, side)
    bpy.data.objects.remove(bpy.data.objects[prefix + "head"], do_unlink=True)
    for obj in compact_probe_head(label, mat):
        bake(obj, side)
    for obj in bpy.data.objects:
        if obj.name.startswith(prefix + "probe_"):
            obj.data.transform(Matrix.Translation(((-24.2 if side < 0 else 24.2) / 1000, 0, 0)))
    for joint in ("proximal", "distal", "carrier"):
        for obj in retained_pivot(
            prefix + joint + "_", mat, axial_float_mm=2 if joint == "carrier" else 0
        ):
            obj.matrix_world = (
                Matrix.Translation((0.0084, 0, 0))
                @ Matrix.Diagonal((-1, 1, 1, 1))
                @ obj.matrix_world
            )
            bake(obj, side)
    for joint in ("shoulder", "elbow", "tip"):
        for suffix in ("bolt", "nut"):
            bpy.data.objects.remove(bpy.data.objects[prefix + joint + "_" + suffix], do_unlink=True)
        for obj in hand_knob_hardware(
            prefix + joint + "_",
            mat,
            bpy.data.materials["S_metal"],
            8.5 if joint == "tip" else 12.5,
            depth_mm=7.5 if joint == "tip" else 10,
        ):
            bake(obj, side)


def pose(
    label: str,
    forward: float = 0,
    lift: float = 0,
    *,
    elbow_release: float | None = None,
    shoulder_release: float | None = None,
) -> None:
    root, a, b, c, d, tip = ElectrodeArmSpec().joints(forward, lift)
    side = -1 if label == "capillary" else 1
    world = Matrix.Translation((side * 0.098, 0.045, 0.108)) @ Matrix.Rotation(
        math.atan2(side * 80, -190)
        + math.atan2(math.hypot(80, 190), -side * 4.2)
        - math.atan2(ElectrodeArmSpec().reach_mm, side * 20),
        4,
        "Z",
    )

    def at(point: tuple[float, float]) -> Matrix:
        return world @ Matrix.Translation((0, point[0] / 1000, point[1] / 1000))

    upper_angle = -math.atan2(a[0], a[1])
    lower_angle = -math.atan2(c[0] - a[0], c[1] - a[1])
    prefix = "S_" + label + "_"
    for suffix, matrix in (
        ("base", world),
        ("upper", at(root) @ Matrix.Rotation(upper_angle, 4, "X")),
        ("lower", at(a) @ Matrix.Rotation(lower_angle, 4, "X")),
        ("follower", at(b) @ Matrix.Rotation(lower_angle, 4, "X")),
        ("platform", at(c) @ Matrix.Rotation(upper_angle, 4, "X")),
        ("head", at(tip)),
        ("proximal_pin", at(b)),
        ("distal_pin", at(d)),
        ("proximal_clip", at(b)),
        ("distal_clip", at(d)),
        ("carrier_pin", at(c)),
        ("carrier_clip", at(c)),
    ):
        bpy.data.objects[prefix + suffix].matrix_world = matrix
    for joint, point in (
        ("shoulder", root),
        ("elbow", a),
        ("tip", tip),
        ("yaw", root),
    ):
        for suffix in ("bolt", "nut"):
            bpy.data.objects[prefix + joint + "_" + suffix].matrix_world = at(point)
    for joint, point in (("shoulder", root), ("elbow", a), ("tip", tip)):
        bpy.data.objects[prefix + joint + "_knob"].matrix_world = at(point)
        bpy.data.objects[prefix + joint + "_nut"].matrix_world = at(point) @ Matrix.Rotation(
            upper_angle, 4, "X"
        )
    for obj in bpy.data.objects:
        if obj.name.startswith(prefix) and (
            obj.name.startswith(prefix + "probe_") or obj.get("compact_head_part")
        ):
            obj.matrix_world = at(tip)
    release = (0 if forward == 0 and lift == 0 else 2) if elbow_release is None else elbow_release
    if not math.isfinite(release) or not 0 <= release <= 2:
        raise ValueError("Elbow release must lie within 0–2 mm")
    for suffix in ("lower", "elbow_bolt", "elbow_knob"):
        obj = bpy.data.objects[prefix + suffix]
        obj.matrix_world = obj.matrix_world @ Matrix.Translation((side * release / 1000, 0, 0))
    bpy.data.objects[prefix + "lower"]["elbow_release_mm"] = release
    shoulder = (0 if release == 0 else 2) if shoulder_release is None else shoulder_release
    apply_shoulder_release(label, shoulder)
    bpy.context.view_layer.update()


def verify() -> dict[str, object]:
    tooth_samples = sum(verify_joint_teeth(label) for label in ("capillary", "pH_temp"))
    release_samples = sum(verify_joint_release(label) for label in ("capillary", "pH_temp"))
    shoulder_samples = sum(
        verify_joint_teeth(label, "shoulder") for label in ("capillary", "pH_temp")
    )
    shoulder_release_samples = sum(
        verify_joint_release(label, "shoulder") for label in ("capillary", "pH_temp")
    )
    shoulder_positions = []
    for label in ("capillary", "pH_temp"):
        target = ElectrodeArmSpec().indexed_target(1, shoulder_step=1)
        pose(label, *target, elbow_release=0)
        verify_pose(label)
        shoulder_samples += verify_joint_teeth(label, "shoulder")
        shoulder_release_samples += verify_joint_release(label, "shoulder")
        shoulder_positions.append(
            {"label": label, "target": target, "elbow_closure": verify_take_up(label)}
        )
        pose(label)
    rows = []
    pin_samples = 0
    indexed = []
    closure = []
    transition_samples = 0
    for label in ("capillary", "pH_temp"):
        other = "pH_temp" if label == "capillary" else "capillary"
        saved = bpy.data.objects[f"S_{other}_head"].matrix_world.copy()
        for forward in (-20, 0, 20):
            for lift in range(0 if forward == 0 else 100, 101, 5):
                pose(label, forward, lift)
                pin_samples += verify_pose(label)
                if bpy.data.objects[f"S_{other}_head"].matrix_world != saved:
                    raise ValueError("Other head moved")
                rows.append((label, forward, lift))
        previous = (0.0, 0.0)
        for index in range(4):
            target = ElectrodeArmSpec().indexed_target(index)
            if index:
                for fraction in range(1, 11):
                    point = tuple(
                        a + (b - a) * fraction / 10 for a, b in zip(previous, target, strict=True)
                    )
                    pose(label, *point, elbow_release=2)
                    verify_pose(label)
                    transition_samples += 1
            pose(label, *target, elbow_release=0)
            verify_pose(label)
            verify_joint_teeth(label)
            verify_joint_release(label)
            if bpy.data.objects[f"S_{other}_head"].matrix_world != saved:
                raise ValueError("Indexed pose moved the other head")
            closure.append({"label": label, "index": index, "closure": verify_take_up(label)})
            indexed.append((label, index, *target))
            previous = target
        pose(label)
    screen = bpy.data.objects["LS_SCREEN_CONTROL"]
    for label in ("capillary", "pH_temp"):
        pose(label, 0, 100)
    for step in range(16):
        set_pose(screen, tilt_step=step / 3, release_mm=0)
        verify_clearance()
    set_pose(screen, tilt_step=4, release_mm=0)
    service_tilt_samples = verify_service_tilt()
    pin_service_samples = verify_pin_service()
    clamp_checks = verify_clamps()
    for forward in range(0, 21, 2):
        for label in ("capillary", "pH_temp"):
            pose(label, forward, 100)
        verify_clearance()
    for label in ("capillary", "pH_temp"):
        pose(label)
    actual_metal = sum(
        bool(o.get("nominal_hardware") or o.get("screen_hardware")) for o in bpy.data.objects
    )
    if actual_metal != 28:
        raise ValueError("Electrode hardware budget changed")
    return {
        "indexed_positions": indexed,
        "elbow_closure": closure,
        "indexed_transition_samples": transition_samples,
        "elbow_local_tooth_samples": tooth_samples,
        "shoulder_local_tooth_samples": shoulder_samples,
        "shoulder_axial_release_samples": shoulder_release_samples,
        "shoulder_indexed_positions": shoulder_positions,
        "free_motion_poses_shoulder_released_mm": 2,
        "vessel_center_x_mm": bpy.data.objects["LS_REF_vessel_250ml_ENVELOPE"].location.x * 1000,
        "elbow_axial_release_samples": release_samples,
        "free_motion_poses_elbow_released_mm": 2,
        "clamp_checks": clamp_checks,
        "service_wrist_tilt_deg": 15,
        "service_wrist_tilt_samples": service_tilt_samples,
        "full_scene_pin_service_samples": pin_service_samples,
        "clamp_service_lift_mm": 100,
        "both_heads_forward_samples": 11,
        "samples": rows,
        "sample_count": len(rows),
        "screen_samples_with_raised_heads": 16,
        "metal_screws": 14,
        "metal_nuts": 14,
        "removable_probe_caps": 2,
        "soft_liner_halves": 6,
        "head_depth_below_wrist_mm": verify_head_envelopes(),
        "platform_material_samples": verify_platform_geometry(),
        "forearm_body_stack_mm": verify_forearm_stack(),
        "wrist_geometry": verify_wrist_geometry(),
        "printed_hand_knobs": 6,
        "knob_bolt_length_mm": 20,
        "knob_bolt_exposure_budget_mm": [0, 1.5],
        "bearing_take_up_budgets_mm": [0.3, 0.2, 0.5, 0.3],
        "printed_pivots": 6,
        "printed_retaining_clips": 6,
        "pin_samples": pin_samples,
        "scope": "Sampled manual coordinated motion, not automatic vertical guidance. Rigid axial stops and pin insertion sampled. Elastic clip fit, locks, load and printing remain unqualified.",
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    baseline = OUTPUT / "baseline.blend"
    shutil.copyfile(ROOT / "tmp/lab-station-simple/simple-concept.blend", baseline)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    with bpy.data.libraries.load(str(baseline), link=False) as (source, loaded):
        loaded.objects = source.objects
    for obj in loaded.objects:
        if obj is not None:
            bpy.context.collection.objects.link(obj)
    for name in ("LS_FIT_spill_dish", "LS_REF_vessel_250ml_ENVELOPE"):
        bpy.data.objects[name].location.x += 0.0035
    bpy.context.view_layer.update()
    for label in ("capillary", "pH_temp"):
        build(label)
        pose(label)
    for joint in ("elbow", "shoulder"):
        for label in ("capillary", "pH_temp"):
            electrode_joint_teeth(label, finish_arm, joint)
    report = verify()
    (OUTPUT / "verification.json").write_text(json.dumps(report, indent=2))
    scene = configure_electrode_view()
    for name, forward, lift in (
        ("working", 0, 0),
        ("raised", 0, 100),
        ("extended", 20, 100),
        ("screen_folded", 0, 100),
        ("indexed-raised", *ElectrodeArmSpec().indexed_target(3)),
        ("indexed-shoulder-raised", *ElectrodeArmSpec().indexed_target(1, shoulder_step=1)),
    ):
        for label in ("capillary", "pH_temp"):
            pose(label, forward, lift, elbow_release=0 if name.startswith("indexed-") else None)
        set_pose(
            bpy.data.objects["LS_SCREEN_CONTROL"],
            tilt_step=0 if name == "screen_folded" else 4,
            release_mm=0,
        )
        verify_clearance()
        scene.render.filepath = str(OUTPUT / (name + ".png"))
        bpy.ops.render.render(write_still=True)
    for label in ("capillary", "pH_temp"):
        pose(label)
    set_pose(bpy.data.objects["LS_SCREEN_CONTROL"], tilt_step=4, release_mm=0)
    render_electrode_details(OUTPUT, pose)
    for label in ("capillary", "pH_temp"):
        apply_take_up(label, ElbowClosureSpec().stroke_mm)
        verify_seated(label)
    scene.render.filepath = str(OUTPUT / "elbow-seated.png")
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "elbow-seated.blend"))
    for label in ("capillary", "pH_temp"):
        pose(label)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "electrode-concept.blend"))


if __name__ == "__main__":
    main()
