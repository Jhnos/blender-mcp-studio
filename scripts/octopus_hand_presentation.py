"""Octopus hand views: assembly, palm top, tip detail and the upright print layout.

`capture` is imported from the V6 presentation rather than copied. Its body holds
nothing V6-specific — camera move, label, render, restore — and this repo has already
paid once for generators that were forks of each other. When a third caller appears it
should move into `hollow_hinge_render`; until then importing it is the cheap half of
that refactor and touches no V6 file.
"""

from __future__ import annotations

from pathlib import Path

import bpy

from scripts.biaxial_hinge_presentation import capture
from scripts.blender_mesh_primitives import assign, material
from scripts.hollow_hinge_render import m, setup_render
from src.core.domain.octopus_hand import OctopusHandSpec


def layout_parts(
    parts: list[bpy.types.Object], target: bpy.types.Collection
) -> list[bpy.types.Object]:
    """One copy of each distinct printable part, spaced along X on the print plane."""
    placed: list[bpy.types.Object] = []
    cursor_mm = 0.0
    for index, source in enumerate(parts):
        obj = source.copy()
        obj.data = source.data
        obj.name = f"HH_OCT_LAYOUT_PART_{index + 1}"
        target.objects.link(obj)
        width_mm = max(source.dimensions) * 1000.0
        obj.location = (m(cursor_mm + width_mm / 2), 0.0, 0.0)
        obj.rotation_euler = (0.0, 0.0, 0.0)
        obj.hide_render = obj.hide_viewport = True
        cursor_mm += width_mm + 10.0
        placed.append(obj)
    return placed


def present_octopus(
    output: Path,
    spec: OctopusHandSpec,
    hand_objects: list[bpy.types.Object],
    layout_objects: list[bpy.types.Object],
) -> None:
    """Four renders, each restoring what it hid, so the .blend saves in one state."""
    output.mkdir(parents=True, exist_ok=True)
    label = material("HH_OCT_LABEL", (0.92, 0.94, 0.98, 1))
    floor = material("HH_OCT_FLOOR", (0.05, 0.06, 0.08, 1))
    camera, _ = setup_render(spec.arm_spec, floor, assign)

    for obj in [*hand_objects, *layout_objects]:
        obj.hide_render = True

    span = spec.upright_footprint_mm
    mid_height = spec.upright_height_mm / 2
    station = spec.arm_station_positions_mm[0]

    capture(
        output,
        "octopus_hand_assembly.png",
        camera,
        hand_objects,
        (span * 1.5, -span * 2.4, span * 1.7),
        (0.0, 0.0, mid_height),
        span * 2.1,
        "Octopus hand V1 - five arms in the upright print pose",
        label,
    )
    capture(
        output,
        "octopus_palm_top.png",
        camera,
        hand_objects,
        (0.1, -0.1, span * 2.6),
        (0.0, 0.0, 0.0),
        span * 1.25,
        "Palm - five sockets, twenty tendon holes, one wire channel",
        label,
    )
    capture(
        output,
        "octopus_tip_detail.png",
        camera,
        hand_objects,
        (station[0] + 90.0, -110.0, spec.arm_tip_height_mm + 60.0),
        (station[0], station[1], spec.arm_tip_height_mm - 10.0),
        90.0,
        "Tip - four cable eyelets and one inward claw",
        label,
    )
    capture(
        output,
        "octopus_print_layout.png",
        camera,
        layout_objects,
        (0.0, -span * 1.9, span * 0.9),
        (span * 0.55, 0.0, 10.0),
        span * 2.0,
        "Distinct printable parts - palm, arm body, tip",
        label,
    )

    for obj in hand_objects:
        obj.hide_render = False
