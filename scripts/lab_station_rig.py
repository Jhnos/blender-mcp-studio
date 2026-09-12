"""Independent pose controls for packaging studies, not a mechanical locking model."""

from __future__ import annotations

from collections.abc import Sequence

import bpy

from src.core.domain.lab_station import LabStationSpec, Point


def attach(obj: bpy.types.Object, parent: bpy.types.Object) -> None:
    bpy.context.view_layer.update()
    world = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world


def pivot(name: str, point: Point, parent: bpy.types.Object | None = None) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.location = tuple(v / 1000 for v in point)
    obj.empty_display_type = "ARROWS"
    obj.empty_display_size = 0.012
    obj.rotation_mode = "XYZ"
    if parent is not None:
        attach(obj, parent)
    return obj


def driver(
    obj: bpy.types.Object,
    control: bpy.types.Object,
    path: str,
    axis: int,
    expression: str,
    properties: Sequence[str],
) -> None:
    curve = obj.driver_add(path, axis)
    curve.driver.type = "SCRIPTED"
    for prop in properties:
        variable = curve.driver.variables.new()
        variable.name = prop
        variable.type = "SINGLE_PROP"
        variable.targets[0].id = control
        variable.targets[0].data_path = f'["{prop}"]'
    curve.driver.expression = expression


def create_arm_rig(
    label: str,
    points: tuple[Point, Point, Point],
    upper_objects: Sequence[bpy.types.Object],
    lower_objects: Sequence[bpy.types.Object],
    wrist_objects: Sequence[bpy.types.Object],
    sliding_objects: Sequence[bpy.types.Object],
    base_objects: Sequence[bpy.types.Object] = (),
) -> bpy.types.Object:
    """Each arm owns its root, elbow, wrist and slide; no other arm is a parent/driver target."""
    root, elbow, wrist = points
    control = pivot("LS_CTRL_" + label, root)
    shoulder = pivot("LS_PIVOT_" + label + "_shoulder", root, control)
    forearm = pivot("LS_PIVOT_" + label + "_elbow", elbow, shoulder)
    head = pivot("LS_PIVOT_" + label + "_wrist", wrist, forearm)
    slide = pivot("LS_PIVOT_" + label + "_slide", wrist, head)
    for name, description, low, high in (
        ("yaw_deg", "This arm only: base yaw offset; not a collision-safe limit", -45.0, 45.0),
        ("shoulder_deg", "Shoulder angle offset from the displayed rest pose", -35.0, 35.0),
        ("elbow_deg", "Elbow angle offset from the displayed rest pose", -45.0, 45.0),
        ("elbow_release_mm", "Axial tooth release before changing elbow angle", 0.0, 2.0),
        ("head_tilt_deg", "Independent head pitch; zero keeps probes vertical", -30.0, 30.0),
        (
            "probe_slide_mm",
            "Straight extraction stroke in millimetres",
            0.0,
            LabStationSpec().lift_travel_mm,
        ),
    ):
        control[name] = 0.0
        control.id_properties_ui(name).update(
            description=description, min=low, max=high, soft_min=low, soft_max=high
        )
    for objects, owner in (
        (base_objects, control),
        (upper_objects, shoulder),
        (lower_objects, forearm),
        (wrist_objects, head),
        (sliding_objects, slide),
    ):
        for obj in objects:
            attach(obj, owner)
    radians = "*0.017453292519943295"
    driver(control, control, "rotation_euler", 2, "yaw_deg" + radians, ("yaw_deg",))
    driver(shoulder, control, "rotation_euler", 0, "shoulder_deg" + radians, ("shoulder_deg",))
    driver(forearm, control, "rotation_euler", 0, "elbow_deg" + radians, ("elbow_deg",))
    driver(
        forearm,
        control,
        "location",
        0,
        f"{forearm.location.x!r}+elbow_release_mm*0.001",
        ("elbow_release_mm",),
    )
    driver(
        head,
        control,
        "rotation_euler",
        0,
        "(head_tilt_deg-shoulder_deg-elbow_deg)" + radians,
        ("head_tilt_deg", "shoulder_deg", "elbow_deg"),
    )
    driver(slide, control, "location", 2, "probe_slide_mm*0.001", ("probe_slide_mm",))
    bpy.context.view_layer.update()
    return control


def set_pose(control: bpy.types.Object, **values: float) -> None:
    for key, value in values.items():
        control[key] = value
    control.update_tag()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    bpy.context.view_layer.update()


def verify_independence(labels: Sequence[str]) -> list[dict[str, object]]:
    """Exercise every control against another real head; prove isolation, not collision safety."""
    if len(labels) < 2:
        raise ValueError("Independence needs at least two arms")
    heads = {label: bpy.data.objects[f"LS_FIT_{label}_clamp_cap"] for label in labels}
    baseline = {label: obj.matrix_world.copy() for label, obj in heads.items()}
    records: list[dict[str, object]] = []
    for label in labels:
        control = bpy.data.objects["LS_CTRL_" + label]
        for prop in (
            "yaw_deg",
            "shoulder_deg",
            "elbow_deg",
            "head_tilt_deg",
            "probe_slide_mm",
            "elbow_release_mm",
        ):
            before = float(control[prop])
            try:
                set_pose(control, **{prop: before + (2 if prop == "elbow_release_mm" else 15)})
                deltas = {
                    name: max(
                        abs(obj.matrix_world[row][column] - baseline[name][row][column])
                        for row in range(4)
                        for column in range(4)
                    )
                    for name, obj in heads.items()
                }
                if deltas[label] <= 1e-6 or any(
                    value > 1e-8 for name, value in deltas.items() if name != label
                ):
                    raise RuntimeError(f"Independent head control failed: {label}.{prop}: {deltas}")
                records.append(
                    {"arm": label, "control": prop, "passed": True, "matrix_deltas": deltas}
                )
            finally:
                set_pose(control, **{prop: before})
    return records
