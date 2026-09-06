"""Pentagonal palm: five arm sockets, twenty tendon holes, one wire channel.

The palm's top face is treated as a body centre plane. That is what lets the V6
socket geometry be reused verbatim: the palm carries the same male ears any body
carries on its +Z face, so the first arm body closes on it exactly as it would on
another body — and gains a base joint for free.

Everything is built at station zero and swung around the palm axis afterwards, so
there is one socket recipe rather than five hand-placed ones.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Matrix

from scripts.blender_mesh_primitives import (
    add_cylinder,
    assign,
    boolean,
    cleanup_mesh,
    move_to_collection,
)
from scripts.hinge_retention import cut_retainer_seats
from scripts.hollow_hinge_render import m
from scripts.model_inset_hinge import root
from src.core.domain.biaxial_hinge import BiaxialHingeSpec
from src.core.domain.octopus_hand import OctopusHandSpec

#: The palm's top face sits on the arm's body top plane, so a socket root that
#: starts inside a disc also starts inside the palm instead of floating above it.
_TOP_FACE_MM = 2.0


def orbit_to_station(
    obj: bpy.types.Object, angle_deg: float, station_mm: tuple[float, float]
) -> bpy.types.Object:
    """Bake the object's own transform, then swing its mesh out to an arm station.

    Objects arrive here in two shapes: `root` writes absolute vertices around the
    world origin, `add_cylinder` leaves its origin at the part's own centre. Baking
    the world matrix into the mesh first makes both behave identically, so a single
    rotation about the palm axis places either of them.
    """
    obj.data.transform(obj.matrix_world)
    obj.matrix_world = Matrix.Identity(4)
    swing = Matrix.Translation((m(station_mm[0]), m(station_mm[1]), 0.0)) @ Matrix.Rotation(
        math.radians(angle_deg), 4, "Z"
    )
    obj.data.transform(swing)
    return obj


def create_socket(arm: BiaxialHingeSpec) -> bpy.types.Object:
    """One male-eared socket at station zero — the +Z half of a V6 body, alone."""
    center = arm.side_male_center_mm
    socket = root("HH_OCT_SOCKET_ROOT", "X", -center, 1, arm)
    boolean(socket, root("HH_OCT_SOCKET_ROOT_B", "X", center, 1, arm), "UNION")
    for side in (-1, 1):
        location = (side * center, 0.0, arm.joint_center_offset_mm)
        boolean(
            socket,
            add_cylinder(
                "HH_OCT_SOCKET_EAR",
                arm.lug_outer_diameter_mm / 2,
                arm.lug_thickness_mm,
                location,
                "X",
            ),
            "UNION",
        )
    for side in (-1, 1):
        location = (side * center, 0.0, arm.joint_center_offset_mm)
        boolean(
            socket,
            add_cylinder(
                "HH_OCT_SOCKET_BORE",
                arm.printed_pin_bore_mm / 2,
                arm.lug_thickness_mm + 1,
                location,
                "X",
            ),
            "DIFFERENCE",
        )
    cut_retainer_seats(socket, arm)
    return socket


#: Segments per drilled hole. A 2.4 mm bore at 24 segments is round to 0.010 mm,
#: an order below what the printer resolves — and 41 holes at the 48-segment
#: default push the readiness sampler past its 20k-triangle budget, which makes
#: its verdict partial. Cheap geometry here buys a complete analysis there.
_DRILL_SEGMENTS = 24


def _drill(
    palm: bpy.types.Object, radius_mm: float, x_mm: float, y_mm: float, spec: OctopusHandSpec
) -> None:
    """Through-hole plus a shallow counterbore so cable never bears on the exit edge."""
    depth = spec.palm_thickness_mm + 2
    center_z = _TOP_FACE_MM - spec.palm_thickness_mm / 2
    boolean(
        palm,
        add_cylinder(
            "HH_OCT_DRILL",
            radius_mm,
            depth,
            (x_mm, y_mm, center_z),
            vertices=_DRILL_SEGMENTS,
        ),
        "DIFFERENCE",
    )
    relief = spec.cable_relief_depth_mm
    boolean(
        palm,
        add_cylinder(
            "HH_OCT_RELIEF",
            radius_mm + spec.cable_relief_widening_mm,
            relief + 0.2,
            (x_mm, y_mm, _TOP_FACE_MM - spec.palm_thickness_mm + relief / 2 - 0.1),
            vertices=_DRILL_SEGMENTS,
        ),
        "DIFFERENCE",
    )


def create_palm(
    target: bpy.types.Collection, mat: bpy.types.Material, spec: OctopusHandSpec
) -> bpy.types.Object:
    """The whole palm as one watertight mesh: pentagon, five sockets, every hole."""
    arm = spec.arm_spec
    palm = add_cylinder(
        "HH_OCT_PALM",
        spec.palm_circumradius_mm,
        spec.palm_thickness_mm,
        (0.0, 0.0, _TOP_FACE_MM - spec.palm_thickness_mm / 2),
        vertices=spec.arm_count,
    )
    move_to_collection(palm, target)

    stations = zip(spec.arm_station_angles_deg, spec.arm_station_positions_mm, strict=True)
    for angle, station in stations:
        # The socket is twisted off its arm's radial heading so the base joint's pin
        # lies across the radius: that is what makes the first joint carry the arm in
        # and out of the palm centre rather than swing it sideways around the palm.
        socket = orbit_to_station(create_socket(arm), angle + spec.palm_socket_twist_deg, station)
        boolean(palm, socket, "UNION")

    for x_mm, y_mm in spec.tendon_hole_positions_mm:
        _drill(palm, arm.tendon_hole_diameter_mm / 2, x_mm, y_mm, spec)
    _drill(palm, spec.wire_channel_diameter_mm / 2, 0.0, 0.0, spec)

    cleanup_mesh(palm)
    assign(palm, mat)
    return palm
