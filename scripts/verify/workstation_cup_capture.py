"""Capture a cup qualification scene through the Blender dependency graph."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.verify.native_session_verify_factory import sha256

FOLD = "整機_螢幕收折"
FOLD_PROPERTY = "fold_angle_deg"


def capture(
    source: Path,
    evidence: Path,
    *,
    screen_steps: int,
    parked_arms: tuple[tuple[float, float], ...],
    required_meshes: set[str],
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
                "pivot_mm": [value * 1000 for value in fold.location],
                "parked": parked,
                "screen_frames": frames,
            }
        )
    )
