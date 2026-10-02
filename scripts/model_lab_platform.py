"""Electrode-holder concept: retained upper hinge, parallel forearm, triangular head carrier."""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from scripts.blender_mesh_primitives import add_cylinder, assign, boolean, loft_rings
from scripts.hollow_hinge_render import look_at
from scripts.lab_electrode_check import (
    verify_clamps,
    verify_elbow_release,
    verify_elbow_teeth,
    verify_knobs,
    verify_local,
    verify_pins,
)
from scripts.lab_station_arm import finish_arm
from scripts.lab_station_clamp import compact_probe_head
from scripts.lab_station_joints import electrode_elbow_teeth, hand_knob_hardware, retained_pivot
from scripts.lab_station_motion_check import tree
from scripts.lab_station_rig import set_pose
from scripts.model_lab_simple import hardware, link, verify_clearance
from src.core.domain.lab_station import ElectrodeArmSpec

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tmp/lab-station-electrode-teeth"


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
    obj = link(prefix + "follower", 12.6, mat, radius_mm=11)
    bake(obj, side)
    vertices = ((0, 0), (0, -24), (28, 0))
    obj = loft_rings(prefix + "platform", [[(x, y, z) for y, z in vertices] for x in (0.2, 8.2)])
    assign(obj, mat)
    for y, z in vertices:
        boolean(obj, add_cylinder("E_TOOL", 11, 8, (4.2, y, z), "X"), "UNION")
    for y, z in vertices:
        boolean(obj, add_cylinder("E_TOOL", 2.7, 30, (4.2, y, z), "X"), "DIFFERENCE")
    boolean(obj, add_cylinder("E_TOOL", 4.8, 5, (6.6, 28, 0), "X", vertices=6), "DIFFERENCE")
    bake(obj, side)
    bpy.data.objects.remove(bpy.data.objects[prefix + "head"], do_unlink=True)
    for obj in compact_probe_head(label, mat):
        bake(obj, side)
    for obj in bpy.data.objects:
        if obj.name.startswith(prefix + "probe_"):
            obj.data.transform(Matrix.Translation(((-24.2 if side < 0 else 24.2) / 1000, 0, 0)))
    hardware(prefix + "carrier_", bpy.data.materials["S_metal"])
    for suffix in ("bolt", "nut"):
        bake(bpy.data.objects[prefix + "carrier_" + suffix], side)
    for joint in ("proximal", "distal"):
        for obj in retained_pivot(prefix + joint + "_", mat):
            bake(obj, side)
    for joint in ("shoulder", "elbow", "tip"):
        for suffix in ("bolt", "nut"):
            bpy.data.objects.remove(bpy.data.objects[prefix + joint + "_" + suffix], do_unlink=True)
        for obj in hand_knob_hardware(
            prefix + joint + "_",
            mat,
            bpy.data.materials["S_metal"],
            8.5 if joint == "tip" else 12.5,
        ):
            bake(obj, side)


def pose(label: str, forward: float = 0, lift: float = 0) -> None:
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
    ):
        bpy.data.objects[prefix + suffix].matrix_world = matrix
    for joint, point in (
        ("shoulder", root),
        ("elbow", a),
        ("carrier", c),
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
    release = 0 if forward == 0 and lift == 0 else 2
    for suffix in ("lower", "elbow_bolt", "elbow_knob"):
        obj = bpy.data.objects[prefix + suffix]
        obj.matrix_world = obj.matrix_world @ Matrix.Translation((side * release / 1000, 0, 0))
    bpy.data.objects[prefix + "lower"]["elbow_release_mm"] = release
    bpy.context.view_layer.update()


def verify() -> dict[str, object]:
    tooth_samples = sum(verify_elbow_teeth(label) for label in ("capillary", "pH_temp"))
    release_samples = sum(verify_elbow_release(label) for label in ("capillary", "pH_temp"))
    rows = []
    pin_samples = 0
    vessel = bpy.data.objects["LS_REF_vessel_250ml_ENVELOPE"]
    for label in ("capillary", "pH_temp"):
        other = "pH_temp" if label == "capillary" else "capillary"
        saved = bpy.data.objects[f"S_{other}_head"].matrix_world.copy()
        for forward in (-20, 0, 20):
            for lift in range(0 if forward == 0 else 100, 101, 5):
                pose(label, forward, lift)
                verify_local(label)
                verify_knobs(label)
                pin_samples += verify_pins(label)
                verify_clearance()
                for obj in bpy.data.objects:
                    if obj.name.startswith(f"S_{label}_probe_") and tree(obj).overlap(tree(vessel)):
                        raise ValueError("Electrode probe intersects vessel")
                if bpy.data.objects[f"S_{other}_head"].matrix_world != saved:
                    raise ValueError("Other head moved")
                rows.append((label, forward, lift))
        pose(label)
    screen = bpy.data.objects["LS_SCREEN_CONTROL"]
    for label in ("capillary", "pH_temp"):
        pose(label, 0, 100)
    for step in range(16):
        set_pose(screen, tilt_step=step / 3, release_mm=0)
        verify_clearance()
    set_pose(screen, tilt_step=4, release_mm=0)
    clamp_checks = verify_clamps()
    for label in ("capillary", "pH_temp"):
        pose(label)
    actual_metal = sum(
        bool(o.get("nominal_hardware") or o.get("screen_hardware")) for o in bpy.data.objects
    )
    if actual_metal != 32:
        raise ValueError("Electrode hardware budget changed")
    return {
        "elbow_local_tooth_samples": tooth_samples,
        "elbow_axial_release_samples": release_samples,
        "non_working_poses_elbow_released_mm": 2,
        "clamp_checks": clamp_checks,
        "clamp_service_lift_mm": 100,
        "samples": rows,
        "sample_count": len(rows),
        "screen_samples_with_raised_heads": 16,
        "metal_screws": 16,
        "metal_nuts": 16,
        "removable_probe_caps": 2,
        "soft_liner_halves": 6,
        "printed_hand_knobs": 6,
        "knob_bolt_length_mm": 20,
        "knob_bolt_exposure_budget_mm": [0, 1.5],
        "bearing_take_up_budgets_mm": [0.3, 0.2, 0.5, 0.3],
        "printed_pivots": 4,
        "printed_retaining_clips": 4,
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
    bpy.context.view_layer.update()
    for label in ("capillary", "pH_temp"):
        build(label)
        pose(label)
    for label in ("capillary", "pH_temp"):
        electrode_elbow_teeth(label, finish_arm)
    report = verify()
    (OUTPUT / "verification.json").write_text(json.dumps(report, indent=2))
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = 1400, 1100
    scene.render.resolution_percentage = 100
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.camera = bpy.data.objects["LS_VIEW_camera"]
    scene.camera.location = (0.43, -0.65, 0.45)
    scene.camera.data.ortho_scale = 0.65
    look_at(scene.camera, (0, -60, 150))
    for name, forward, lift in (
        ("working", 0, 0),
        ("raised", 0, 100),
        ("extended", 20, 100),
        ("screen_folded", 0, 100),
    ):
        for label in ("capillary", "pH_temp"):
            pose(label, forward, lift)
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
    camera_matrix = scene.camera.matrix_world.copy()
    camera_scale = scene.camera.data.ortho_scale
    pivot = bpy.data.objects["S_capillary_distal_pin"].matrix_world
    target = pivot.translation
    scene.camera.location = pivot @ Vector((-0.07, -0.035, 0.03))
    scene.camera.data.ortho_scale = 0.075
    look_at(scene.camera, tuple(value * 1000 for value in target))
    scene.render.filepath = str(OUTPUT / "retainer-detail.png")
    bpy.ops.render.render(write_still=True)
    for label in ("capillary", "pH_temp"):
        pose(label, 0, 100)
    joint = bpy.data.objects["S_capillary_elbow_bolt"].matrix_world
    scene.camera.location = joint @ Vector((-0.025, -0.065, 0.035))
    scene.camera.data.ortho_scale = 0.085
    look_at(scene.camera, tuple(value * 1000 for value in joint.translation))
    scene.render.filepath = str(OUTPUT / "elbow-released.png")
    bpy.ops.render.render(write_still=True)
    head = bpy.data.objects["S_pH_temp_head"]
    target = head.matrix_world @ Vector((0.021, 0, -0.044))
    scene.camera.location = target + head.matrix_world.to_3x3() @ Vector((0.055, 0.060, 0.028))
    scene.camera.data.ortho_scale = 0.12
    look_at(scene.camera, tuple(value * 1000 for value in target))
    scene.render.filepath = str(OUTPUT / "clamp-detail.png")
    bpy.ops.render.render(write_still=True)
    moved = {}
    try:
        for obj in bpy.data.objects:
            if obj.name.startswith("S_pH_temp_clamp_"):
                shift = -0.015 if obj.name.endswith("_bolt") else 0.018
                if "liner" in obj.name and int(obj.name.rsplit("_", 1)[1]) % 2 == 0:
                    continue
                moved[obj.name] = obj.matrix_world.copy()
                obj.matrix_world = obj.matrix_world @ Matrix.Translation((0, shift, 0))
        bpy.context.view_layer.update()
        scene.render.filepath = str(OUTPUT / "clamp-exploded.png")
        bpy.ops.render.render(write_still=True)
    finally:
        for name, matrix in moved.items():
            bpy.data.objects[name].matrix_world = matrix
        bpy.context.view_layer.update()
    for label in ("capillary", "pH_temp"):
        pose(label)
    scene.camera.matrix_world = camera_matrix
    scene.camera.data.ortho_scale = camera_scale
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "electrode-concept.blend"))


if __name__ == "__main__":
    main()
