"""V2 palm: a chamfered, corner-truncated plate with a buttress behind every socket.

The V1 palm was a five-sided cylinder — one primitive call, square top and bottom
edges, five sharp points, and a phase that put those points eighteen degrees off the
arms. This one is lofted instead, from the outline the spec computes: four rings, the
outer two stepped in by the rim chamfer so the plate meets the bed and the air on a
45 degree face rather than a square edge.

The sockets are V1's, unchanged and imported rather than re-typed — the whole point of
turning the plate was to carry the same socket on better material. What is added on
top of them is a stem per arm, and a wire bore per arm beside it.

Nothing here claims strength. A buttress is more material in the right place, which is
not the same as a qualified load path.
"""

from __future__ import annotations

import bpy

from scripts.blender_mesh_primitives import (
    add_cylinder,
    assign,
    boolean,
    cleanup_mesh,
    loft_rings,
    move_to_collection,
)
from scripts.octopus_palm_geometry import create_socket, orbit_to_station
from src.core.domain.octopus_hand_v2 import OctopusHandV2Spec

#: Segments per drilled hole. Same reason as V1's: at 48 the readiness sampler runs
#: past its triangle budget and reports a partial verdict, which a contract must fail.
_DRILL_SEGMENTS = 24


def create_plate(spec: OctopusHandV2Spec) -> bpy.types.Object:
    """The bare plate: truncated pentagon, chamfered top and bottom, nothing on it yet.

    Four rings rather than a cylinder's two. The outer pair are the outline stepped in
    by the chamfer — stepped, not scaled, because the corner flats and the long edges
    sit at different distances and scaling would give a chamfer at the right angle on
    neither of them.
    """
    outline = spec.palm_outline
    top = spec.palm_top_face_z_mm
    bottom = top - spec.palm_thickness_mm
    chamfer = spec.palm_rim_chamfer_mm
    full = outline.inset_vertices_mm(0.0)
    stepped = outline.inset_vertices_mm(chamfer)
    rings = [
        [(x, y, bottom) for x, y in stepped],
        [(x, y, bottom + chamfer) for x, y in full],
        [(x, y, top - chamfer) for x, y in full],
        [(x, y, top) for x, y in stepped],
    ]
    return loft_rings("HH_OCT2_PALM", rings)


def create_stem(spec: OctopusHandV2Spec) -> bpy.types.Object:
    """One buttress, built on the +X arm heading and swung to its station afterwards.

    Both ends are buried a fuse depth into what they meet — into the socket root
    inboard and into the plate below — because a face landing exactly flush leaves the
    Boolean two coplanar sheets to resolve, which is where readiness has found
    non-manifold edges before.

    The top ring is not planar: it is the ramp, high against the socket and low at its
    outer end, which is what keeps the stem under the arm's swept underside.
    """
    stem = spec.stem
    fuse = spec.tip_feature_fuse_mm
    inner = stem.inner_radius_mm - fuse
    outer = stem.outer_radius_mm
    half = spec.stem_half_width_mm
    base = spec.palm_top_face_z_mm - fuse
    inner_top = stem.top_z_mm(inner)
    outer_top = stem.top_z_mm(outer)
    rings = [
        [
            (inner, -half, base),
            (outer, -half, base),
            (outer, half, base),
            (inner, half, base),
        ],
        [
            (inner, -half, inner_top),
            (outer, -half, outer_top),
            (outer, half, outer_top),
            (inner, half, inner_top),
        ],
    ]
    return loft_rings("HH_OCT2_STEM", rings)


def drill_relieved(
    palm: bpy.types.Object, radius_mm: float, x_mm: float, y_mm: float, spec: OctopusHandV2Spec
) -> None:
    """Through-hole plus a counterbore, so no cable ever bears on a sharp exit edge.

    V1 has the same shape as a private helper. It is written again rather than imported
    because V1's palm generator belongs to a package whose output is checksummed, and
    reaching into it to widen a name would put that package's bytes at risk for no
    geometric gain.
    """
    depth = spec.palm_thickness_mm + 2
    center_z = spec.palm_top_face_z_mm - spec.palm_thickness_mm / 2
    boolean(
        palm,
        add_cylinder(
            "HH_OCT2_DRILL", radius_mm, depth, (x_mm, y_mm, center_z), vertices=_DRILL_SEGMENTS
        ),
        "DIFFERENCE",
    )
    relief = spec.cable_relief_depth_mm
    boolean(
        palm,
        add_cylinder(
            "HH_OCT2_RELIEF",
            radius_mm + spec.cable_relief_widening_mm,
            relief + 0.2,
            (x_mm, y_mm, spec.palm_top_face_z_mm - spec.palm_thickness_mm + relief / 2 - 0.1),
            vertices=_DRILL_SEGMENTS,
        ),
        "DIFFERENCE",
    )


def create_palm(
    target: bpy.types.Collection, mat: bpy.types.Material, spec: OctopusHandV2Spec
) -> bpy.types.Object:
    """The whole plate as one watertight mesh: outline, sockets, stems, every hole."""
    arm = spec.arm_spec
    palm = create_plate(spec)
    move_to_collection(palm, target)

    stations = list(zip(spec.arm_station_angles_deg, spec.arm_station_positions_mm, strict=True))
    for angle, station in stations:
        # The socket is twisted off its arm's radial heading so the base joint's pin
        # lies across the radius — V1's reason, and V1's geometry, unchanged.
        socket = orbit_to_station(create_socket(arm), angle + spec.palm_socket_twist_deg, station)
        boolean(palm, socket, "UNION")
    for angle, _station in stations:
        # The stem is already in palm coordinates, so it only has to be swung round the
        # axis — no translation to a station, unlike the socket.
        boolean(palm, orbit_to_station(create_stem(spec), angle, (0.0, 0.0)), "UNION")

    for x_mm, y_mm in spec.tendon_hole_positions_mm:
        drill_relieved(palm, arm.tendon_hole_diameter_mm / 2, x_mm, y_mm, spec)
    for x_mm, y_mm in spec.arm_wire_bore_positions_mm:
        drill_relieved(palm, spec.arm_wire_bore_radius_mm, x_mm, y_mm, spec)
    drill_relieved(palm, spec.wire_channel_diameter_mm / 2, 0.0, 0.0, spec)

    cleanup_mesh(palm)
    assign(palm, mat)
    return palm
