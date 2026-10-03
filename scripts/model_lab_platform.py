"""Electrode-holder concept: retained upper hinge, parallel forearm, triangular head carrier."""

from __future__ import annotations

import json
import math
import shutil
from dataclasses import asdict
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from scripts.blender_mesh_primitives import refine_closed_mesh
from scripts.hollow_hinge_render import look_at
from scripts.lab_electrode_check import (
    verify_clamps as verify_clamps,
)
from scripts.lab_electrode_check import (
    verify_forearm_stack as verify_forearm_stack,
)
from scripts.lab_electrode_check import (
    verify_head_envelopes as verify_head_envelopes,
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
from scripts.lab_electrode_check import (
    verify_platform_geometry as verify_platform_geometry,
)
from scripts.lab_electrode_check import (
    verify_pose as verify_pose,
)
from scripts.lab_electrode_closure import (
    apply_shoulder_release,
)
from scripts.lab_electrode_closure import apply_take_up as apply_take_up
from scripts.lab_electrode_closure import closure_spec as closure_spec
from scripts.lab_electrode_closure import verify_interference as verify_interference
from scripts.lab_electrode_closure import (
    verify_joint_release as verify_joint_release,
)
from scripts.lab_electrode_closure import (
    verify_joint_teeth as verify_joint_teeth,
)
from scripts.lab_electrode_closure import (
    verify_pin_service as verify_pin_service,
)
from scripts.lab_electrode_closure import (
    verify_seated as verify_seated,
)
from scripts.lab_electrode_closure import verify_take_up as verify_take_up
from scripts.lab_electrode_module import bake as bake
from scripts.lab_electrode_module import build as build
from scripts.lab_electrode_motion import motion_report, verify_shoulder_transfer
from scripts.lab_electrode_motion import verify_service_tilt as verify_service_tilt
from scripts.lab_electrode_motion import verify_wrist_faces as verify_wrist_faces
from scripts.lab_electrode_motion import (
    verify_wrist_geometry as verify_wrist_geometry,
)
from scripts.lab_electrode_routes import build_guides, render_guide_detail, verify_guide_geometry
from scripts.lab_electrode_routes import verify_guide_controls as verify_guide_controls
from scripts.lab_electrode_routes import verify_guides as verify_guides
from scripts.lab_station_arm import finish_arm
from scripts.lab_station_joints import electrode_joint_teeth
from scripts.lab_station_render import (
    configure_electrode_view,
    render_electrode_details,
    render_electrode_seated,
)
from scripts.lab_station_rig import set_electrode_service_tilt, set_electrode_wrist_pose, set_pose
from scripts.model_lab_simple import verify_clearance
from src.core.domain.lab_station import (
    ELECTRODE_ASSEMBLIES,
    ElectrodeArmSpec,
    ElectrodeAssemblySpec,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tmp/lab-station-electrode-guides-aligned"


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
    bpy.data.objects[prefix + "tip_bolt"]["wrist_release_mm"] = 0
    set_electrode_wrist_pose(label, 0, 2 if release or shoulder else 0)
    bpy.context.view_layer.update()


def render_shoulder_transfer() -> None:
    scene = configure_electrode_view()
    for label in ("capillary", "pH_temp"):
        pose(label)

    def capture(name: str) -> None:
        scene.render.filepath = str(OUTPUT / ("transfer-" + name + ".png"))
        bpy.ops.render.render(write_still=True)
        if name.startswith("end-"):
            bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / ("transfer-" + name + ".blend")))

    report = verify_shoulder_transfer(pose, capture)
    (OUTPUT / "shoulder-transfer.json").write_text(json.dumps(report, indent=2))


def render_wrist_release() -> None:
    scene = configure_electrode_view()
    angle = ElectrodeArmSpec().wrist_indexed_angle(0, 100, 1)
    for label in ("capillary", "pH_temp"):
        pose(label, 0, 100)
        set_electrode_wrist_pose(label, angle, 2)
    for label in ("capillary", "pH_temp"):
        verify_pose(label)
        verify_wrist_faces(label, 2.2)
    frame = bpy.data.objects["S_capillary_tip_bolt"].matrix_world
    scene.camera.location = frame @ Vector((-0.018, -0.065, 0.025))
    scene.camera.data.ortho_scale = 0.080
    look_at(scene.camera, tuple(v * 1000 for v in frame.translation))
    scene.render.filepath = str(OUTPUT / "wrist-released.png")
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "wrist-released.blend"))
    hidden = {
        o.name: o.hide_render
        for o in bpy.data.objects
        if o.name.startswith("S_capillary_")
        and (
            o.get("compact_head_part")
            or "probe_" in o.name
            or o.name.endswith(("tip_bolt", "tip_knob"))
        )
    }
    try:
        for name in hidden:
            bpy.data.objects[name].hide_render = True
        scene.camera.location = frame @ Vector((-0.045, -0.016, 0.012))
        scene.camera.data.ortho_scale = 0.065
        look_at(scene.camera, tuple(v * 1000 for v in frame.translation))
        scene.render.filepath = str(OUTPUT / "wrist-teeth-detail.png")
        bpy.ops.render.render(write_still=True)
    finally:
        for name, value in hidden.items():
            bpy.data.objects[name].hide_render = value
    for label in ("capillary", "pH_temp"):
        pose(label)
    configure_electrode_view()


def build_scene(
    configuration: ElectrodeAssemblySpec = ELECTRODE_ASSEMBLIES["baseline"],
    *,
    output: Path = OUTPUT,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name in ("motion-capillary.json", "motion-pH_temp.json", "verification.json"):
        (output / name).unlink(missing_ok=True)
    baseline = output / "baseline.blend"
    shutil.copyfile(ROOT / "tmp/lab-station-simple/simple-concept.blend", baseline)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    with bpy.data.libraries.load(str(baseline), link=False) as (source, loaded):
        loaded.objects = source.objects
    for obj in loaded.objects:
        if obj is not None:
            bpy.context.collection.objects.link(obj)
    for name in ("LS_FIT_spill_dish", "LS_REF_vessel_250ml_ENVELOPE"):
        bpy.data.objects[name].location += Vector(configuration.vessel_shift_mm) / 1000
    bpy.context.view_layer.update()
    for label in ("capillary", "pH_temp"):
        build(label, configuration.head(label))
        pose(label)
    for joint in ("elbow", "shoulder", "tip"):
        for label in ("capillary", "pH_temp"):
            electrode_joint_teeth(label, finish_arm, joint)
    for label in ("capillary", "pH_temp"):
        for part in ("upper", "platform"):
            refine_closed_mesh(bpy.data.objects[f"S_{label}_{part}"])
    build_guides()
    bpy.context.scene["electrode_configuration"] = json.dumps(asdict(configuration), sort_keys=True)


def verify_scene(label: str | None = None) -> None:
    report = motion_report(pose, OUTPUT, label)
    if report is None:
        return
    report["guide_geometry"] = verify_guide_geometry()
    report["guide_count"] = verify_guides(required=True)
    (OUTPUT / "verification.json").write_text(json.dumps(report, indent=2))


def render_scene() -> None:
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
        verify_guides(required=True)
        scene.render.filepath = str(OUTPUT / (name + ".png"))
        bpy.ops.render.render(write_still=True)
    for label in ("capillary", "pH_temp"):
        pose(label)
    set_pose(bpy.data.objects["LS_SCREEN_CONTROL"], tilt_step=4, release_mm=0)
    render_electrode_details(OUTPUT, pose)
    for label in ("capillary", "pH_temp"):
        pose(label, 0, 100)
        set_electrode_service_tilt(label)
    render_electrode_seated(OUTPUT, "service-seated", ("tip",))
    render_wrist_release()
    render_electrode_seated(OUTPUT)
    render_guide_detail(OUTPUT)
    frame = bpy.data.objects["S_capillary_tip_bolt"].matrix_world
    scene.camera.location = frame @ Vector((-0.040, -0.035, 0.035))
    scene.camera.data.ortho_scale = 0.080
    look_at(scene.camera, tuple(v * 1000 for v in frame.translation))
    scene.render.filepath = str(OUTPUT / "wrist-seated-detail.png")
    bpy.ops.render.render(write_still=True)
    configure_electrode_view()
    for label in ("capillary", "pH_temp"):
        pose(label)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "electrode-concept.blend"))


def main() -> None:
    build_scene()
    verify_scene()
    render_scene()


if __name__ == "__main__":
    main()
