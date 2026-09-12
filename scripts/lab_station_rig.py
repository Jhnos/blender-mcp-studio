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
        ("shoulder_release_mm", "Axial tooth release before changing shoulder angle", 0.0, 2.0),
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
    driver(
        shoulder,
        control,
        "location",
        0,
        f"{shoulder.location.x!r}+shoulder_release_mm*0.001",
        ("shoulder_release_mm",),
    )
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
            "shoulder_release_mm",
        ):
            before = float(control[prop])
            try:
                set_pose(control, **{prop: before + (2 if prop.endswith("release_mm") else 15)})
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


def create_rotary_support_rig(label: str, root: Point, elbow: Point, wrist: Point) -> None:
    """Restore independent support joints; wrist compensation is explicitly manual."""
    control = bpy.data.objects["LR_CTRL_" + label]
    yaw = pivot(f"LR_PIVOT_{label}_yaw", root)
    shoulder = pivot(f"LR_PIVOT_{label}_shoulder", root, yaw)
    forearm = pivot(f"LR_PIVOT_{label}_elbow", elbow, shoulder)
    head = pivot(f"LR_PIVOT_{label}_wrist", wrist, forearm)
    for name, obj, axis in (
        ("base_yaw_deg", yaw, 2),
        ("shoulder_deg", shoulder, 0),
        ("elbow_deg", forearm, 0),
        ("wrist_deg", head, 0),
    ):
        control[name] = 0.0
        control.id_properties_ui(name).update(
            min=-45.0,
            max=45.0,
            description="Independent joint; pose study range, not a collision-safe limit",
        )
        driver(obj, control, "rotation_euler", axis, name + "*0.017453292519943295", (name,))
    control["shoulder_release_mm"] = 0.0
    control.id_properties_ui("shoulder_release_mm").update(min=0.0, max=2.0)
    driver(shoulder, control, "location", 0, "shoulder_release_mm*0.001", ("shoulder_release_mm",))
    attach(bpy.data.objects[f"LR_{label}_mount_envelope"], yaw)
    control["elbow_release_mm"] = 0.0
    control.id_properties_ui("elbow_release_mm").update(min=0.0, max=2.0)
    driver(
        forearm,
        control,
        "location",
        0,
        f"{forearm.location.x!r}+elbow_release_mm*0.001",
        ("elbow_release_mm",),
    )
    attach(bpy.data.objects[f"LR_{label}_support_envelope_0"], shoulder)
    attach(bpy.data.objects[f"LR_{label}_support_envelope_1"], forearm)
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith("LR_" + label + "_") and (
            obj.name.endswith("_base") or obj.name.endswith("_fixed")
        ):
            attach(obj, head)
    for name in ("hinge_0", "hinge_1", "moving"):
        obj = bpy.data.objects[f"LR_{label}_{name}"]
        bpy.context.view_layer.update()
        local = head.matrix_world.inverted() @ obj.matrix_world
        attach(obj, head)
        if name == "moving":
            for curve in obj.animation_data.drivers:
                if curve.data_path == "location":
                    expression = curve.driver.expression
                    curve.driver.expression = (
                        f"{local.translation[curve.array_index]!r}+({expression})"
                    )
    # Recompile after all custom properties and parent dependencies exist.
    control.update_tag()
    for obj in (yaw, shoulder, forearm, head):
        for curve in obj.animation_data.drivers:
            curve.driver.expression += "+0"
    bpy.context.view_layer.update()


def verify_rotary_articulation() -> list[dict[str, object]]:
    """Every declared joint must move its own head and leave every other-head mesh fixed."""
    rows = []
    for label, other in (("capillary", "pH_temp"), ("pH_temp", "capillary")):
        control = bpy.data.objects["LR_CTRL_" + label]
        head = bpy.data.objects[f"LR_{label}_head"]
        other_meshes = [
            o
            for o in bpy.context.scene.objects
            if o.type == "MESH" and o.name.startswith("LR_" + other + "_")
        ]
        if not other_meshes:
            raise ValueError("Other articulated head missing")
        for prop in (
            "base_yaw_deg",
            "shoulder_deg",
            "elbow_deg",
            "wrist_deg",
            "lift_mm",
            "elbow_release_mm",
            "shoulder_release_mm",
        ):
            if prop not in control:
                raise ValueError(f"Articulation control missing: {label}.{prop}")
            saved = float(control[prop])
            before = head.matrix_world.copy()
            fixed = {o.name: o.matrix_world.copy() for o in other_meshes}
            try:
                set_pose(control, **{prop: saved + (2 if prop.endswith("release_mm") else 15)})
                own_delta = max(
                    abs(head.matrix_world[r][c] - before[r][c]) for r in range(4) for c in range(4)
                )
                other_delta = max(
                    abs(o.matrix_world[r][c] - fixed[o.name][r][c])
                    for o in other_meshes
                    for r in range(4)
                    for c in range(4)
                )
                if own_delta <= 1e-6 or other_delta > 1e-8:
                    raise ValueError(f"Articulation independence failed: {label}.{prop}")
                rows.append(
                    {
                        "head": label,
                        "control": prop,
                        "own_delta": own_delta,
                        "other_delta": other_delta,
                    }
                )
            finally:
                set_pose(control, **{prop: saved})
    return rows
