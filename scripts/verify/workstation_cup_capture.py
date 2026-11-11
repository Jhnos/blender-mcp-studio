"""Capture a cup qualification scene through the Blender dependency graph."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from scripts.verify.native_session_verify_factory import sha256
from scripts.verify.workstation_cup_checks import TRANSFER_LINES

if TYPE_CHECKING:
    from bpy.types import Object, Scene

FOLD = "整機_螢幕收折"
FOLD_PROPERTY = "fold_angle_deg"
CUP_WALL_REFERENCE = "wall_is_non_printed_reference"
CUP_SERVICE_FRAME = "nominal_cup_parked_frame"


def capture_transfer(
    scene: Scene, cup: Object, meshes: dict[str, Object], service_frame: int
) -> list[list[float]]:
    """Read every cup knot and ensure the surrounding scene holds its pose."""
    from bpy_extras.anim_utils import action_get_channelbag_for_slot

    animation = cup.animation_data
    if animation is None or animation.action is None:
        raise ValueError("recorded cup is missing its action")
    if cup.parent or cup.constraints or animation.drivers or animation.nla_tracks:
        raise ValueError("recorded cup requires an unparented translation")
    curves = action_get_channelbag_for_slot(animation.action, animation.action_slot).fcurves
    if not curves or any(
        curve.data_path != "location"
        or curve.mute
        or curve.modifiers
        or curve.sampled_points
        or any(key.interpolation != "LINEAR" for key in curve.keyframe_points)
        for curve in curves
    ):
        raise ValueError("recorded cup requires linear location keys")
    initial_location = tuple(cup.matrix_world.translation)
    initial_basis = cup.matrix_world.to_3x3().copy()
    stationary = {name: obj.matrix_world.copy() for name, obj in meshes.items() if obj != cup}
    positions = [initial_location]
    started = False
    times = sorted(
        {
            key.co.x
            for curve in curves
            for key in curve.keyframe_points
            if service_frame < key.co.x <= scene.frame_end
        }
    )
    end = None
    for time in times:
        scene.frame_set(int(time), subframe=time % 1)
        position = tuple(cup.matrix_world.translation)
        if (
            any(meshes[name].matrix_world != matrix for name, matrix in stationary.items())
            or cup.matrix_world.to_3x3() != initial_basis
        ):
            raise ValueError("assembly or cup orientation moves during recorded transfer")
        positions.append(position)
        if position != initial_location:
            started = True
        elif started:
            end = time
            break
    if end is None:
        raise ValueError("recorded cup has not returned to its seat")
    for obj in scene.objects:
        if obj == cup:
            continue
        for item in (obj, obj.data) if obj.type == "CURVE" else (obj,):
            action = item.animation_data
            if not action or not action.action:
                continue
            if action.nla_tracks:
                raise ValueError("assembly animation is active during recorded transfer")
            bag = action_get_channelbag_for_slot(action.action, action.action_slot)
            for curve in bag.fcurves:
                value = curve.evaluate(service_frame)
                if (
                    curve.modifiers
                    or curve.sampled_points
                    or curve.evaluate(end) != value
                    or any(key.interpolation != "LINEAR" for key in curve.keyframe_points)
                    or any(
                        key.co.y != value
                        for key in curve.keyframe_points
                        if service_frame <= key.co.x <= end
                    )
                ):
                    raise ValueError("assembly animation is active during recorded transfer")
    return [[coordinate * 1000 for coordinate in position] for position in positions]


def transfer_line_bounds(scene: Scene) -> dict[str, list[list[list[float]]]]:
    """Enclose each installed Bézier span and its bevel in world millimetres."""
    import numpy as np

    bounds = {}
    for name in TRANSFER_LINES:
        obj = scene.objects.get(name)
        if obj is None or obj.type != "CURVE" or obj.modifiers:
            raise ValueError(f"missing or unsupported installed line: {name}")
        data = obj.data
        if data.bevel_object or data.taper_object or data.bevel_depth <= 0:
            raise ValueError(f"unsupported installed line section: {name}")
        (spline,) = data.splines
        if spline.type != "BEZIER" or spline.use_cyclic_u or len(spline.bezier_points) < 2:
            raise ValueError(f"unsupported installed line path: {name}")
        transform = obj.matrix_world
        bevel = 1000 * data.bevel_depth * np.linalg.norm(np.array(transform.to_3x3()), ord=2)
        points = list(spline.bezier_points)
        spans = []
        for start, end in zip(points[:-1], points[1:], strict=True):
            controls = 1000 * np.array(
                [transform @ p for p in (start.co, start.handle_right, end.handle_left, end.co)]
            )
            pad = bevel * max(start.radius, end.radius) + 0.001
            spans.append(
                [(controls.min(axis=0) - pad).tolist(), (controls.max(axis=0) + pad).tolist()]
            )
        bounds[name] = spans
    return bounds


def capture(
    source: Path,
    evidence: Path,
    *,
    screen_steps: int,
    parked_arms: tuple[tuple[float, float], ...],
    required_meshes: set[str],
    cup_name: str,
) -> None:
    """Blender-only adapter. Capture original meshes and actual display transforms."""
    import bpy

    from scripts.lab_station_native_revision import surface
    from scripts.lab_station_rig import set_pose
    from scripts.verify.native_revision_fixture import assert_factory_isolated

    assert_factory_isolated()
    if Path(bpy.data.filepath).resolve() != source:
        raise ValueError("Blender did not open the selected snapshot")
    original_sha = sha256(source)
    scene = bpy.context.scene
    controls = [scene.objects[f"V35_{side}_controls"] for side in ("capillary", "pH_temp")]
    fold = scene.objects[FOLD]
    (hinge,) = fold.animation_data.drivers
    (variable,) = hinge.driver.variables
    (target,) = variable.targets
    if (
        fold.parent
        or fold.constraints
        or hinge.data_path != "rotation_euler"
        or hinge.array_index != 0
        or hinge.driver.expression != "(min(60,max(0,angle))-60)*0.017453292519943295"
        or variable.name != "angle"
        or target.id != fold
        or target.data_path != f'["{FOLD_PROPERTY}"]'
    ):
        raise ValueError("unsupported display hinge motion")
    meshes = {obj.name: obj for obj in scene.objects if obj.type == "MESH"}
    if not required_meshes <= meshes.keys():
        raise ValueError("selected assembly lacks required cup or display geometry")
    cup = meshes[cup_name]
    saved_nominal = cup.get(CUP_WALL_REFERENCE, False)
    if not isinstance(saved_nominal, bool):
        raise ValueError("invalid saved nominal cup marker")
    recorded = None
    if saved_nominal:
        service_frame = cup.get(CUP_SERVICE_FRAME)
        if (
            type(service_frame) is not int
            or not scene.frame_start <= service_frame <= scene.frame_end
        ):
            raise ValueError("saved nominal cup is missing its parked service frame")
        scene.frame_set(service_frame)
        actual_arms = tuple((obj["upper_lift_deg"], obj["lower_adjust_deg"]) for obj in controls)
        animation = cup.animation_data
        if animation and animation.action:
            recorded = capture_transfer(scene, cup, meshes, service_frame)
            parked_arms = actual_arms
            scene.frame_set(service_frame)
        elif actual_arms != parked_arms:
            raise ValueError("saved nominal cup service frame does not have both arms parked")
    display = {name for name, obj in meshes.items() if obj.parent == fold}
    if not {"LS_FIT_lcd_front", "LS_FIT_lcd_back"} <= display:
        raise ValueError("display panels are not bound to the certified hinge")

    def update_arms(arm_values: list[tuple[float, float]]) -> None:
        for obj, (upper, lower) in zip(controls, arm_values, strict=True):
            set_pose(obj, upper_lift_deg=upper, lower_adjust_deg=lower)
            if (obj["upper_lift_deg"], obj["lower_adjust_deg"]) != (upper, lower):
                raise ValueError(f"timeline replaced the requested pose for {obj.name}")

    def update_display(screen: float) -> None:
        fold[FOLD_PROPERTY] = screen
        fold.update_tag()
        bpy.context.view_layer.update()

    def matrix(name: str) -> tuple[tuple[float, ...], ...]:
        return tuple(tuple(row) for row in meshes[name].matrix_world)

    initial = [(obj["upper_lift_deg"], obj["lower_adjust_deg"]) for obj in controls]
    initial_fold = fold[FOLD_PROPERTY]
    before = {name: matrix(name) for name in meshes}
    update_arms(list(parked_arms))
    update_display(60.0)
    parked = {name: surface(obj) for name, obj in meshes.items()}
    lines = transfer_line_bounds(scene) if recorded is not None else {}
    stationary = {name: matrix(name) for name in meshes.keys() - display}
    frames = []
    for index in range(screen_steps + 1):
        update_display(index * 60.0 / screen_steps)
        if any(matrix(name) != expected for name, expected in stationary.items()):
            raise ValueError("an unlisted object moves during display folding")
        frames.append({name: matrix(name) for name in display})
    update_arms(initial)
    update_display(initial_fold)
    if before != {name: matrix(name) for name in meshes} or sha256(source) != original_sha:
        raise ValueError("capture changed the source")
    evidence.write_text(
        json.dumps(
            {
                "native_sha256": original_sha,
                "saved_nominal_cup": saved_nominal,
                "pivot_mm": [value * 1000 for value in fold.location],
                "parked": parked,
                "screen_frames": frames,
                "recorded_cup_transfer_mm": recorded,
                "transfer_line_bounds_mm": lines,
            }
        )
    )
