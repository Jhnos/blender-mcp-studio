"""Bind existing rigid screen clamp roles without creating or changing mesh data."""

from math import atan2, hypot, isfinite

import bpy

from scripts.lab_station_rig import continuous_property, driver
from src.core.domain.screen_clamp import ScreenClampSpec


def bind_screen_clamp_control(
    screen: bpy.types.Object,
    active_screw: bpy.types.Object,
    active_nut: bpy.types.Object,
    passive_pin: bpy.types.Object,
    passive_retainer: bpy.types.Object,
    spec: ScreenClampSpec | None = None,
) -> None:
    """Install nominal lead and float on five supplied, distinct rigid identities.

    The caller owns hardware geometry and engagement. The neutral screen frame
    must be axis aligned; its children follow its existing hinge pivot. Passive
    references are reparented with world transforms preserved before seating.
    The active part may have baked geometry away from its object origin; its Y/Z
    translation follows its rotation about the existing screen hinge, not origin zero.
    """
    spec = spec or ScreenClampSpec()
    roles = (screen, active_screw, active_nut, passive_pin, passive_retainer)
    bpy.context.view_layer.update()
    if (
        len(set(roles)) != len(roles)
        or any(not isfinite(v) for obj in roles for row in obj.matrix_world for v in row)
        or screen.parent is not None
        or screen.rotation_mode != "XYZ"
        or any(abs(v) > 1e-7 for v in screen.rotation_euler)
        or any(abs(v - 1) > 1e-7 for v in screen.scale)
        or active_screw.rotation_mode != "XYZ"
        or active_screw.parent is not None
        or any(abs(v) > 1e-7 for v in active_screw.rotation_euler[1:])
        or screen.get("fold_angle_deg") != spec.sequence.working_angle_deg
        or "收折進度" in screen
    ):
        raise ValueError("Clamp roles require distinct unbound parts at the neutral working frame")
    bpy.context.view_layer.update()
    frames = {obj: obj.matrix_world.copy() for obj in (active_nut, passive_pin, passive_retainer)}
    for obj, world in frames.items():
        obj.parent = screen
        obj.matrix_parent_inverse = screen.matrix_world.inverted()
        obj.matrix_world = world
    bpy.context.view_layer.update()
    origin_x, origin_angle = screen.location.x, screen.rotation_euler.x
    screw_x, screw_angle = active_screw.location.x, active_screw.rotation_euler.x
    expressions = spec.driver_expressions()
    pivot_y, pivot_z = screen.location.y, screen.location.z
    offset_y, offset_z = active_screw.location.y - pivot_y, active_screw.location.z - pivot_z
    radius, phase = hypot(offset_y, offset_z), atan2(offset_z, offset_y)
    # Polar rotation uses one trig call, keeping the complete progress expression
    # within RNA capacity without a driven-property dependency or new rigid part.
    delta = expressions["active_angle_rad"]
    active_y = f"{pivot_y!r}+{radius!r}*cos(({delta})+({phase!r}))"
    active_z = f"{pivot_z!r}+{radius!r}*sin(({delta})+({phase!r}))"
    continuous_property(screen, "fold_angle_deg", spec.sequence.working_angle_deg)
    screen["收折進度"] = 0.0
    screen.id_properties_ui("收折進度").update(
        min=0.0,
        max=100.0,
        description=f"鬆主動螺栓→退齒→調到{spec.sequence.target_angle_deg:g}°→就座→鎖回；名義控制，非製造驗收",
    )
    screen["樞軸軸向間隙"] = 0.0
    screen.id_properties_ui("樞軸軸向間隙").update(
        min=-spec.float_limit_mm,
        max=spec.float_limit_mm,
        description="被動樞軸及保持螺母的共同軸向間隙(mm)；名義包絡",
    )
    bindings = (
        (screen, "location", 0, f"{origin_x!r}+({expressions['body_x_mm']})*.001"),
        (screen, "rotation_euler", 0, f"{origin_angle!r}+({expressions['body_angle_rad']})"),
        (active_screw, "location", 0, f"{screw_x!r}+({expressions['active_x_mm']})*.001"),
    )
    for obj, path, index, expression in bindings:
        driver(
            obj,
            screen,
            path,
            index,
            expression,
            ("progress",),
            identity_mapping=True,
            property_paths=("收折進度",),
        )
    for path, axis, expression in (
        ("rotation_euler", 0, f"{screw_angle!r}+({delta})"),
        ("location", 1, active_y),
        ("location", 2, active_z),
    ):
        driver(
            active_screw,
            screen,
            path,
            axis,
            expression,
            ("progress",),
            identity_mapping=True,
            property_paths=("收折進度",),
        )
    driver(
        screen,
        screen,
        '["fold_angle_deg"]',
        -1,
        f"body_angle*180/pi+{spec.sequence.working_angle_deg!r}",
        ("body_angle",),
        identity_mapping=True,
        rna_paths=("rotation_euler[0]",),
    )
    for obj in (passive_pin, passive_retainer):
        driver(
            obj,
            screen,
            "location",
            0,
            f"{obj.location.x!r}+({expressions['pin_float_mm']})*.001",
            ("pin_float",),
            identity_mapping=True,
            property_paths=("樞軸軸向間隙",),
        )
    for obj in roles:
        obj.update_tag()
    bpy.context.view_layer.update()
