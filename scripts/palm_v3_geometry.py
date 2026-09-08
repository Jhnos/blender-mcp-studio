"""The palm plate: four roots in a row, a thumb root across from them, and the
two things the soft layer needs.

Every root is a male tongue, because a finger's own base end is a female fork —
the palm is what the first phalanx hangs from, so it presents the other half of
the same joint. That means the joint at the knuckle is the same joint as every
other joint in the finger, with the same pin and the same bearing seat, which is
one part number rather than a special case.

The thumb root is placed by the spec's own frame, not by numbers typed here. If
the two ever disagree, the reachability figure in `AnthropomorphicPalmSpec` is
describing a hand that was not built.

Soft-layer interface, and deliberately no more than this: a cuff clamp to hold
both sleeves at the wrist, and one air port. The outer glove is bought.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Matrix, Vector

from scripts.blender_mesh_primitives import add_cylinder, boolean, cleanup_mesh
from scripts.hollow_hinge_geometry import create_box
from src.core.domain.palm_v3 import AnthropomorphicPalmSpec

M = 0.001


def _male_tongue(spec: AnthropomorphicPalmSpec, name: str) -> bpy.types.Object:
    """One knuckle root, built at the origin pointing up, ready to be placed."""
    link = spec.finger.link
    stem = create_box(
        f"{name}_STEM",
        (link.male_tongue_thickness_mm, link.lug_outer_diameter_mm, link.joint_center_offset_mm),
        (0.0, 0.0, link.joint_center_offset_mm / 2),
    )
    lug = add_cylinder(
        f"{name}_LUG",
        link.lug_outer_diameter_mm / 2,
        link.male_tongue_thickness_mm,
        (0.0, 0.0, link.joint_center_offset_mm),
        axis=spec.finger.male_hinge_axis,
    )
    boolean(stem, lug, "UNION")
    bore = add_cylinder(
        f"{name}_BORE",
        link.printed_pin_bore_mm / 2,
        link.male_tongue_thickness_mm + 4.0,
        (0.0, 0.0, link.joint_center_offset_mm),
        axis=spec.finger.male_hinge_axis,
    )
    boolean(stem, bore, "DIFFERENCE")
    stem.name = name
    return stem


def _place(obj: bpy.types.Object, origin_mm: tuple[float, float, float], matrix: Matrix) -> None:
    obj.matrix_world = Matrix.Translation(tuple(v * M for v in origin_mm)) @ matrix


def build_palm(spec: AnthropomorphicPalmSpec) -> bpy.types.Object:
    """The plate with every root, channel, clamp and port already cut into it."""
    link = spec.finger.link
    plate_height = spec.thumb_base_drop_mm + link.body_length_mm
    plate = create_box(
        "HJ_V3_PALM",
        (spec.palm_width_mm, link.body_depth_mm, plate_height),
        (0.0, 0.0, -plate_height / 2),
    )

    # The thenar boss, before the roots, so the thumb root has something to
    # land on. Without it the root unions as a second shell and every
    # watertightness check still passes.
    bridge_centre, bridge_size = spec.thenar_bridge_mm
    boolean(plate, create_box("HJ_V3_THENAR", bridge_size, bridge_centre), "UNION")

    roots: list[bpy.types.Object] = []
    for index, x_mm in enumerate(spec.row_finger_x_mm, start=1):
        root = _male_tongue(spec, f"HJ_V3_ROOT_{index}")
        _place(root, (x_mm, 0.0, 0.0), Matrix.Identity(4))
        roots.append(root)

    # The thumb root is placed from the spec's frame rather than from numbers
    # typed here, so the built hand and the reachability figure cannot drift.
    axis, pad = spec.thumb_frame
    across = Vector(axis).cross(Vector(pad))
    thumb_basis = Matrix(
        (
            (across.x, pad[0], axis[0], 0.0),
            (across.y, pad[1], axis[1], 0.0),
            (across.z, pad[2], axis[2], 0.0),
            (0.0, 0.0, 0.0, 1.0),
        )
    )
    thumb_root = _male_tongue(spec, "HJ_V3_ROOT_THUMB")
    _place(thumb_root, spec.thumb_root_mm, thumb_basis)
    roots.append(thumb_root)

    bpy.context.view_layer.update()
    for root in roots:
        boolean(plate, root, "UNION")

    # One tendon channel per finger, straight down the plate behind each root.
    for index, x_mm in enumerate(spec.row_finger_x_mm, start=1):
        boolean(
            plate,
            add_cylinder(
                f"HJ_V3_CUT_TENDON_{index}",
                link.tendon_hole_diameter_mm / 2,
                plate_height + 8.0,
                (x_mm, -spec.finger.moment_arms_mm[0], -plate_height / 2),
            ),
            "DIFFERENCE",
        )
    boolean(
        plate,
        add_cylinder(
            "HJ_V3_CUT_TENDON_THUMB",
            link.tendon_hole_diameter_mm / 2,
            plate_height + 8.0,
            (
                spec.thumb_root_mm[0],
                -spec.finger.moment_arms_mm[0],
                -plate_height / 2,
            ),
        ),
        "DIFFERENCE",
    )

    # Air port, on the back of the hand and clear of anything that grips.
    port_x, port_y = spec.air_port_center_mm
    boolean(
        plate,
        add_cylinder(
            "HJ_V3_CUT_AIR_PORT",
            spec.air_port_diameter_mm / 2,
            link.body_depth_mm + 8.0,
            (port_x, 0.0, -plate_height * 0.72),
            axis="Y",
        ),
        "DIFFERENCE",
    )
    _ = port_y

    # Cuff clamp: a groove right round the wrist for a cable tie or a band to sit
    # in, holding both sleeves. One clamp, because there is one seal.
    boolean(
        plate,
        _clamp_groove(spec, plate_height),
        "DIFFERENCE",
    )

    cleanup_mesh(plate)
    return plate


def _clamp_groove(spec: AnthropomorphicPalmSpec, plate_height: float) -> bpy.types.Object:
    """A shallow band round the wrist, cut as a slightly larger box minus a smaller."""
    link = spec.finger.link
    depth = spec.cuff_clamp_wall_mm
    z = -plate_height + link.body_length_mm / 2
    outer = create_box(
        "HJ_V3_CUT_CLAMP_OUTER",
        (spec.palm_width_mm + 8.0, link.body_depth_mm + 8.0, depth),
        (0.0, 0.0, z),
    )
    inner = create_box(
        "HJ_V3_CUT_CLAMP_INNER",
        (
            spec.palm_width_mm - 2 * depth,
            link.body_depth_mm - 2 * depth,
            depth + 4.0,
        ),
        (0.0, 0.0, z),
    )
    boolean(outer, inner, "DIFFERENCE")
    return outer


def finger_mount_frames(
    spec: AnthropomorphicPalmSpec,
) -> list[tuple[str, tuple[float, float, float], float]]:
    """Where each finger hangs and how far its first joint is from the plate.

    Returned rather than assumed so the assembly and the reachability figure read
    the same placement.
    """
    frames = [
        (f"ARM_{index}", (x_mm, 0.0, 0.0), 0.0)
        for index, x_mm in enumerate(spec.row_finger_x_mm, start=1)
    ]
    frames.append(("THUMB", spec.thumb_root_mm, math.radians(spec.thumb_opposition_deg)))
    return frames
