"""Whole electrode-arm motion scenarios composed from independent geometric guards."""

import math
from collections.abc import Callable

import bpy
from mathutils import Matrix, Vector

from scripts.lab_electrode_check import (
    verify_clamps,
    verify_forearm_stack,
    verify_head_envelopes,
    verify_pins,
    verify_platform_geometry,
    verify_pose,
    verify_service_tilt,
)
from scripts.lab_electrode_closure import (
    apply_shoulder_release,
    apply_take_up,
    closure_spec,
    shoulder_members,
    verify_bearing_chains,
    verify_interference,
    verify_joint_release,
    verify_joint_teeth,
    verify_pin_service,
    verify_seated,
    verify_wrist_geometry,
)
from scripts.lab_station_rig import set_pose
from scripts.model_lab_simple import verify_clearance
from src.core.domain.lab_station import ElectrodeArmSpec


def verify(pose: Callable[..., None]) -> dict[str, object]:
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
            {"label": label, "target": target, **verify_bearing_chains(label)}
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
            closure.append({"label": label, "index": index, **verify_bearing_chains(label)})
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


def verify_shoulder_transfer(
    pose: Callable[..., None], capture: Callable[[str], None] | None = None
) -> dict[str, object]:
    """Sample release, rigid rotation and reseating with the elbow held closed."""
    spec = ElectrodeArmSpec()
    rows = []
    for label in ("capillary", "pH_temp"):
        other = "pH_temp" if label == "capillary" else "capillary"
        fixed = {
            o.name: o.matrix_world.copy()
            for o in bpy.data.objects
            if o.name.startswith(f"S_{other}_")
        }
        base_name = f"S_{label}_base"
        fixed[base_name] = bpy.data.objects[base_name].matrix_world.copy()
        stages = (
            [("unseat", 0.0, 0.0, 0.7 * (14 - i) / 14) for i in range(15)]
            + [("release", 0.0, i / 10, 0.0) for i in range(21)]
            + [("rotate", float(i), 2.0, 0.0) for i in range(16)]
            + [("return", 15.0, (20 - i) / 10, 0.0) for i in range(21)]
            + [("reseat", 15.0, 0.0, 0.7 * i / 14) for i in range(15)]
        )
        try:
            for index, (stage, angle, release, closure) in enumerate(stages):
                pose(label, *spec.indexed_target(1), elbow_release=0, shoulder_release=0)
                apply_take_up(label, closure_spec("elbow").stroke_mm)
                apply_shoulder_release(label, release)
                base = bpy.data.objects[f"S_{label}_base"].matrix_world.copy()
                rotation = base @ Matrix.Rotation(math.radians(angle), 4, "X") @ base.inverted()
                for obj in shoulder_members(label):
                    obj.matrix_world = rotation @ obj.matrix_world
                bpy.context.view_layer.update()
                apply_take_up(label, closure, "shoulder")
                verify_seated(label)
                verify_interference(label, "shoulder")
                verify_pins(label)
                if any(
                    bpy.data.objects[name].matrix_world != matrix for name, matrix in fixed.items()
                ):
                    raise ValueError("Shoulder transfer moved a fixed base or other head")
                target = spec.angular_target(15, angle)
                tip = bpy.data.objects[f"S_{label}_tip_bolt"].matrix_world.translation
                local = base.inverted() @ tip
                if (
                    math.dist(
                        (local.y * 1000, local.z * 1000),
                        (spec.reach_mm + target[0], 72 + target[1]),
                    )
                    > 0.001
                ):
                    raise ValueError("Shoulder transfer does not follow the rigid arc")
                # A radial direction on the head must rotate with the arm, not stay upright.
                head = bpy.data.objects[f"S_{label}_head"].matrix_world
                direction = base.to_3x3().inverted() @ head.to_3x3() @ Vector((0, 0, 1))
                expected = Vector(
                    (0, -math.sin(math.radians(angle)), math.cos(math.radians(angle)))
                )
                if (direction - expected).length > 1e-6:
                    raise ValueError("Shoulder transfer detached probe orientation")
                rows.append(
                    {
                        "label": label,
                        "stage": stage,
                        "angle_deg": angle,
                        "release_mm": release,
                        "closure_mm": closure,
                    }
                )
                if capture and index in (0, 43, len(stages) - 1):
                    capture(
                        ("start" if index == 0 else "mid" if index == 43 else "end") + "-" + label
                    )
            verify_seated(label, "shoulder")
        finally:
            pose(label)
    return {
        "states": rows,
        "sample_count": len(rows),
        "scope": "Rigid sampled path at elbow +15 degrees; no continuous swept-volume, thread or load claim.",
    }
