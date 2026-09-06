"""Tip features: four cable eyelets and one inward claw, on the last arm body.

Two jobs, deliberately two pieces of geometry. The eyelets anchor the drive
cables — the tendon hole runs up through a boss and meets a cross-hole, so the
cable turns once and is knotted through a closed ring rather than over an edge.
The claw is for grabbing and touches no cable at all; changing one does not
disturb the other.

Everything is built in the body's own frame with the body centre at the origin,
so the caller places the finished tip exactly like any other body.
"""

from __future__ import annotations

import math

import bpy

from scripts.blender_mesh_primitives import add_cylinder, boolean, cleanup_mesh
from scripts.hollow_hinge_render import m
from src.core.domain.biaxial_hinge import BiaxialHingeSpec
from src.core.domain.octopus_hand import OctopusHandSpec

#: Segments per tip cylinder. Same reason as the palm drills: a complete readiness
#: analysis is worth more than facets nobody can print.
_TIP_SEGMENTS = 24


def _boss_radius_mm(spec: OctopusHandSpec) -> float:
    return spec.tip_eyelet_diameter_mm / 2 + spec.tip_eyelet_wall_mm


def _boss_height_mm(spec: OctopusHandSpec) -> float:
    return spec.tip_eyelet_diameter_mm + 2 * spec.tip_eyelet_wall_mm


def create_eyelet(
    spec: OctopusHandSpec, arm: BiaxialHingeSpec, x_mm: float, y_mm: float
) -> bpy.types.Object:
    """A boss over one tendon exit, cross-drilled so the cable can be tied through."""
    height = _boss_height_mm(spec)
    base_z = spec.tip_feature_base_z_mm
    boss = add_cylinder(
        "HH_OCT_EYELET",
        _boss_radius_mm(spec),
        height + spec.tip_feature_fuse_mm,
        (x_mm, y_mm, base_z + (height + spec.tip_feature_fuse_mm) / 2),
        vertices=_TIP_SEGMENTS,
    )
    cross = add_cylinder(
        "HH_OCT_EYELET_CROSS",
        spec.tip_eyelet_diameter_mm / 2,
        2 * _boss_radius_mm(spec) + 2,
        (x_mm, y_mm, base_z + spec.tip_feature_fuse_mm + height / 2),
        "Y",
        vertices=_TIP_SEGMENTS,
    )
    boolean(boss, cross, "DIFFERENCE")
    return boss


def create_claw(spec: OctopusHandSpec, arm: BiaxialHingeSpec) -> bpy.types.Object:
    """A tapered hook rising from the rim and leaning back over the arm axis.

    Built in a radial/tangential frame and then swung to `tip_claw_direction_deg`,
    which is the heading that undoes the last body's own twist in the chain — so
    the finished claw faces the palm axis instead of sideways.

    The lean is measured from vertical, so a slope under 45 degrees keeps the
    underside self-supporting when the arm is printed standing up.
    """
    slope = math.radians(spec.tip_claw_slope_deg)
    heading = math.radians(spec.tip_claw_direction_deg)
    cos_h, sin_h = math.cos(heading), math.sin(heading)
    base_radius = arm.body_outer_diameter_mm / 2 - spec.tip_claw_thickness_mm / 2
    base_z = spec.tip_feature_base_z_mm
    tip_radius = base_radius - spec.tip_claw_length_mm * math.sin(slope)
    tip_z = base_z + spec.tip_claw_length_mm * math.cos(slope)

    levels = (
        (base_radius, base_z, spec.tip_claw_thickness_mm / 2, spec.tip_claw_thickness_mm),
        (tip_radius, tip_z, spec.tip_claw_thickness_mm / 3, spec.tip_claw_thickness_mm / 2),
    )
    vertices = [
        (
            m((radius + d_radius) * cos_h - d_tangent * sin_h),
            m((radius + d_radius) * sin_h + d_tangent * cos_h),
            m(z),
        )
        for radius, z, half_thickness, half_width in levels
        for d_radius, d_tangent in (
            (-half_thickness, -half_width),
            (half_thickness, -half_width),
            (half_thickness, half_width),
            (-half_thickness, half_width),
        )
    ]
    faces = [(3, 2, 1, 0), (4, 5, 6, 7)]
    for corner in range(4):
        following = (corner + 1) % 4
        faces.append((corner, following, following + 4, corner + 4))

    mesh = bpy.data.meshes.new("HH_OCT_CLAW_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    claw = bpy.data.objects.new("HH_OCT_CLAW", mesh)
    bpy.context.collection.objects.link(claw)
    cleanup_mesh(claw)
    return claw


def add_tip_features(body: bpy.types.Object, spec: OctopusHandSpec) -> bpy.types.Object:
    """Union eyelets and claw onto one body, then re-open every cable path.

    The body must own its mesh — a `repeat_body` copy shares data with the master,
    and cutting one would cut the whole arm.
    """
    arm = spec.arm_spec
    for x_mm, y_mm in arm.tendon_positions_mm:
        boolean(body, create_eyelet(spec, arm, x_mm, y_mm), "UNION")
    boolean(body, create_claw(spec, arm), "UNION")

    # The bosses were unioned straight over the tendon exits; drill them open again
    # so the cable still has a path from the palm to the cross-hole above it.
    depth = arm.body_length_mm + 2 * _boss_height_mm(spec) + 4
    for x_mm, y_mm in arm.tendon_positions_mm:
        boolean(
            body,
            add_cylinder(
                "HH_OCT_TIP_TENDON",
                arm.tendon_hole_diameter_mm / 2,
                depth,
                (x_mm, y_mm, 0.0),
                vertices=_TIP_SEGMENTS,
            ),
            "DIFFERENCE",
        )
    cleanup_mesh(body)
    return body
