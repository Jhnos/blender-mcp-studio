"""Bind the domain screen-operation sequence to existing rigid parts."""

import math

import bpy

from scripts.lab_station_rig import continuous_property, driver
from src.core.domain.lab_station_joints import ScreenFoldSpec


def bind_screen_fold_control(
    screen: bpy.types.Object, right_screw: bpy.types.Object, spec: ScreenFoldSpec | None = None
) -> None:
    """Bind existing parts at the working pose; geometry and hierarchy stay intact.

    The caller establishes the hinge axis and right-side hardware identity.
    Rebinding a non-working pose is rejected rather than guessing its rest frame.
    """
    spec = spec or ScreenFoldSpec()
    if (
        screen == right_screw
        or screen.rotation_mode != "XYZ"
        or right_screw.parent is not None
        or screen.get("fold_angle_deg") != spec.working_angle_deg
        or "收折進度" in screen
    ):
        raise ValueError("Screen binding requires an unbound working pose and independent screw")
    expressions = spec.driver_expressions()
    origin_x, screw_x, angle = screen.location.x, right_screw.location.x, screen.rotation_euler.x
    continuous_property(screen, "fold_angle_deg", spec.working_angle_deg)
    screen["收折進度"] = 0.0
    screen.id_properties_ui("收折進度").update(
        min=0.0,
        max=100.0,
        soft_min=0.0,
        soft_max=100.0,
        description="0 展開 → 鬆右螺栓 → 退齒 → 收折 → 就座 → 鎖回 → 100 收起；名義動作，尚未驗證實體鎖緊力",
    )
    bindings = ("progress",)
    driver(
        screen,
        screen,
        "rotation_euler",
        0,
        f"{angle!r}+(({expressions['angle_deg']})-{spec.working_angle_deg!r})*{math.pi / 180!r}",
        bindings,
        identity_mapping=True,
        property_paths=("收折進度",),
    )
    driver(
        screen,
        screen,
        "location",
        0,
        f"{origin_x!r}+({expressions['release_mm']})*0.001",
        bindings,
        identity_mapping=True,
        property_paths=("收折進度",),
    )
    driver(
        right_screw,
        screen,
        "location",
        0,
        f"{screw_x!r}+({expressions['screw_mm']})*0.001",
        bindings,
        identity_mapping=True,
        property_paths=("收折進度",),
    )
    driver(
        screen,
        screen,
        '["fold_angle_deg"]',
        -1,
        f"(body_angle-{angle!r})*180/pi+{spec.working_angle_deg!r}",
        ("body_angle",),
        identity_mapping=True,
        rna_paths=("rotation_euler[0]",),
    )
    screen.update_tag()
    bpy.context.view_layer.update()
