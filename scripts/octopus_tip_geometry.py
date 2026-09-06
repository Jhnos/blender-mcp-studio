"""The tip: a terminal segment, not a body with parts glued to it.

A tip ends its chain, so it keeps no ears it cannot use. Everything above the disc's
top face is cut away and replaced by a faceted cap — flat faces press on an object
where a cylinder only touches it on a line, and the profile flares off the disc at a
self-supporting angle and then only ever narrows, so it prints upright without
support.

Cables are anchored by two through-bores rather than four bosses. Each bore crosses
one opposed pair of tendon holes inside the cap, so a cable comes up its hole, turns
once, and is knotted through a closed ring.
"""

from __future__ import annotations

import math

import bpy

from scripts.blender_mesh_primitives import add_cylinder, boolean, cleanup_mesh
from scripts.hollow_hinge_geometry import create_box
from scripts.hollow_hinge_render import m
from scripts.octopus_palm_geometry import orbit_to_station
from src.core.domain.octopus_hand import OctopusHandSpec

#: Segments per drilled hole. Same reason as the palm drills: a complete readiness
#: analysis is worth more than facets nobody can print.
_BORE_SEGMENTS = 24


def create_cap(spec: OctopusHandSpec) -> bpy.types.Object:
    """The faceted terminal cap as a closed solid, ready to union onto a body.

    Three rings: the disc's own radius where it fuses in, the widest shoulder, and
    the flat top face. Ring one to two flares outward at a printable angle; two to
    three only narrows, which never overhangs.
    """
    rings = (
        (spec.tip_cap_base_radius_mm, spec.tip_cap_base_z_mm),
        (spec.tip_cap_max_radius_mm, spec.tip_cap_shoulder_z_mm),
        (spec.tip_cap_top_diameter_mm / 2, spec.tip_cap_top_z_mm),
    )
    facets = spec.tip_facet_count
    vertices: list[tuple[float, float, float]] = []
    for radius, height in rings:
        for index in range(facets):
            angle = 2 * math.pi * index / facets
            vertices.append((m(radius * math.cos(angle)), m(radius * math.sin(angle)), m(height)))

    faces: list[tuple[int, ...]] = [
        tuple(reversed(range(facets))),
        tuple(range(2 * facets, 3 * facets)),
    ]
    for level in (0, facets):
        for index in range(facets):
            following = (index + 1) % facets
            faces.append(
                (
                    level + index,
                    level + following,
                    level + following + facets,
                    level + index + facets,
                )
            )

    mesh = bpy.data.meshes.new("HH_OCT_CAP_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    cap = bpy.data.objects.new("HH_OCT_CAP", mesh)
    bpy.context.collection.objects.link(cap)
    cleanup_mesh(cap)
    return cap


def _open_cable_paths(tip: bpy.types.Object, spec: OctopusHandSpec) -> None:
    """Re-drill everything the cap covered, then cross-bore the cable anchors."""
    arm = spec.arm_spec
    # The drill has to clear the cap, not the disc. Sizing it off the body left the
    # centre channel blind above z=13 while the cap top sits at z=18 — invisible in
    # the bounding box, and caught only by the centre-ray probe.
    bottom_z = -(arm.joint_center_offset_mm + arm.lug_outer_diameter_mm / 2 + 2)
    top_z = spec.tip_cap_top_z_mm + 2
    depth = top_z - bottom_z
    centre_z = (top_z + bottom_z) / 2
    boolean(
        tip,
        add_cylinder(
            "HH_OCT_TIP_CENTER",
            arm.center_channel_diameter_mm / 2,
            depth,
            (0.0, 0.0, centre_z),
            vertices=_BORE_SEGMENTS,
        ),
        "DIFFERENCE",
    )
    # Tendon holes stop above the cross-bore: the cable ends there, and leaving the
    # cap's top face solid keeps the gripping surface whole.
    tendon_top_z = spec.tip_cable_bore_z_mm + spec.tip_cable_bore_diameter_mm
    tendon_depth = tendon_top_z - bottom_z
    for index, position in enumerate(arm.tendon_positions_mm):
        boolean(
            tip,
            add_cylinder(
                f"HH_OCT_TIP_TENDON_{index}",
                arm.tendon_hole_diameter_mm / 2,
                tendon_depth,
                (position[0], position[1], (tendon_top_z + bottom_z) / 2),
                vertices=_BORE_SEGMENTS,
            ),
            "DIFFERENCE",
        )

    for heading in spec.tip_cable_bore_angles_deg:
        bore = add_cylinder(
            "HH_OCT_TIP_CROSS",
            spec.tip_cable_bore_diameter_mm / 2,
            2 * spec.tip_cap_max_radius_mm + 4,
            (0.0, 0.0, spec.tip_cable_bore_z_mm),
            "X",
            vertices=_BORE_SEGMENTS,
        )
        boolean(tip, orbit_to_station(bore, heading, (0.0, 0.0)), "DIFFERENCE")


def build_tip(tip: bpy.types.Object, spec: OctopusHandSpec) -> bpy.types.Object:
    """Turn a private copy of the plain body into the terminal segment.

    `tip` must already own its mesh — a `repeat_body` style copy shares data, and
    cutting one would cut the whole arm.
    """
    span = 4 * spec.arm_spec.body_outer_diameter_mm
    boolean(
        tip,
        create_box(
            "HH_OCT_TIP_TRIM",
            (span, span, span),
            (0.0, 0.0, spec.tip_feature_base_z_mm + span / 2),
        ),
        "DIFFERENCE",
    )
    boolean(tip, create_cap(spec), "UNION")
    _open_cable_paths(tip, spec)
    cleanup_mesh(tip)
    return tip
