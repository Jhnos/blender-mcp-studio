"""Retainer seats, captive double-headed pins, and removable grooved pins/clips."""

from scripts.blender_mesh_primitives import (
    add_cylinder,
    assign,
    boolean,
    cleanup_mesh,
    move_to_collection,
)
from scripts.hollow_hinge_geometry import create_box
from scripts.model_inset_hinge import create_pin
from src.core.domain.biaxial_hinge import BiaxialHingeSpec


def cut_retainer_seats(body, spec: BiaxialHingeSpec) -> None:
    inner = spec.side_male_center_mm - spec.lug_thickness_mm / 2
    for side in (-1, 1):
        seat = add_cylinder(
            "HH_RETENTION_SEAT",
            spec.retainer_seat_diameter_mm / 2,
            spec.retainer_seat_depth_mm + 0.2,
            (
                side * (inner + (spec.retainer_seat_depth_mm - 0.2) / 2),
                0,
                spec.joint_center_offset_mm,
            ),
            "X",
        )
        boolean(body, seat, "DIFFERENCE")
    cleanup_mesh(body)


def create_captive_pin(target, mat, spec: BiaxialHingeSpec):
    pin = create_pin(target, mat, spec)
    pin.hide_viewport = False
    outside = spec.pin_under_head_radius_mm + spec.pin_head_height_mm
    end = outside - spec.retainer_inner_radius_mm
    boolean(pin, create_box("HH_TRIM_PIN", (20, 20, 10), (0, 0, end + 5)), "DIFFERENCE")
    collar = add_cylinder(
        "HH_CAPTIVE_HEAD",
        spec.retainer_diameter_mm / 2,
        spec.retainer_thickness_mm,
        (0, 0, end - spec.retainer_thickness_mm / 2),
    )
    boolean(pin, collar, "UNION")
    cleanup_mesh(pin)
    pin.name = "HH_CAPTIVE_PIN_MASTER"
    pin.hide_viewport = True
    return pin


def create_grooved_pin(target, mat, spec: BiaxialHingeSpec):
    pin = create_pin(target, mat, spec)
    pin.hide_viewport = False
    outside = spec.pin_under_head_radius_mm + spec.pin_head_height_mm
    groove_center = outside - spec.retainer_inner_radius_mm - spec.groove_length_mm / 2
    tool = add_cylinder(
        "HH_GROOVE_RING", spec.pin_diameter_mm / 2 + 1, spec.groove_length_mm, (0, 0, groove_center)
    )
    core = add_cylinder(
        "HH_GROOVE_CORE",
        spec.groove_diameter_mm / 2,
        spec.groove_length_mm + 1,
        (0, 0, groove_center),
    )
    boolean(tool, core, "DIFFERENCE")
    boolean(pin, tool, "DIFFERENCE")
    cleanup_mesh(pin)
    pin.name = "HH_REMOVABLE_PIN_MASTER"
    pin.hide_viewport = True
    return pin


def create_retaining_clip(target, mat, spec: BiaxialHingeSpec):
    height = spec.clip_thickness_mm
    clip = add_cylinder("HH_CLIP_MASTER", spec.retainer_diameter_mm / 2, height, (0, 0, height / 2))
    hole = add_cylinder(
        "HH_CLIP_HOLE", spec.clip_inner_diameter_mm / 2, height + 2, (0, 0, height / 2)
    )
    boolean(clip, hole, "DIFFERENCE")
    boolean(
        clip,
        create_box("HH_CLIP_OPENING", (5, spec.clip_opening_mm, 3), (2.5, 0, height / 2)),
        "DIFFERENCE",
    )
    cleanup_mesh(clip)
    for vertex in clip.data.vertices:
        vertex.co += clip.location
    clip.location = (0, 0, 0)
    assign(clip, mat)
    move_to_collection(clip, target)
    clip.hide_render = clip.hide_viewport = True
    return clip
