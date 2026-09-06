"""Grip pads on the four plain rim sectors of every repeated arm body.

Ears occupy the cardinal directions — male on X above, female on Y below — so the
diagonals are the only free rim. They are also the rotation-invariant choice: the
chain twists ninety degrees body to body, and a diagonal maps onto a diagonal, so
one pad pattern serves every body whatever its own twist.

Each pad is a trapezoidal block whose outer face is flat, because a flat face beds
against an object where a cylinder only touches it on a line. Printed upright the
pad stands proud of a vertical disc, so its underside is chamfered back to the body
rather than left as a bare horizontal overhang.
"""

from __future__ import annotations

import math

import bpy

from scripts.blender_mesh_primitives import boolean, cleanup_mesh
from scripts.hollow_hinge_render import m
from src.core.domain.octopus_hand import OctopusHandSpec

#: How far the pad's inner face sinks into the disc so the union fuses.
_FUSE_MM = 1.0


def create_pad(spec: OctopusHandSpec, heading_deg: float) -> bpy.types.Object:
    """One pad, built in a radial/tangential frame and swung to its heading."""
    arm = spec.arm_spec
    inner_radius = arm.body_outer_diameter_mm / 2 - _FUSE_MM
    outer_radius = spec.grip_outer_diameter_mm / 2
    top_z = spec.grip_pad_height_mm / 2
    bottom_z = -spec.grip_pad_height_mm / 2
    chamfer_z = top_z - spec.grip_flat_face_height_mm
    half_arc = math.tan(math.radians(spec.grip_pad_arc_deg / 2))

    # (radius, height) walked as a closed loop: in at the top, out along the flat
    # face, then back down the chamfer to the body.
    profile = (
        (inner_radius, top_z),
        (outer_radius, top_z),
        (outer_radius, chamfer_z),
        (inner_radius, bottom_z),
    )
    heading = math.radians(heading_deg)
    cos_h, sin_h = math.cos(heading), math.sin(heading)
    vertices: list[tuple[float, float, float]] = []
    for radius, height in profile:
        half_width = radius * half_arc
        for tangent in (-half_width, half_width):
            vertices.append(
                (
                    m(radius * cos_h - tangent * sin_h),
                    m(radius * sin_h + tangent * cos_h),
                    m(height),
                )
            )

    faces: list[tuple[int, ...]] = [(0, 2, 4, 6), (7, 5, 3, 1)]
    for index in range(4):
        following = (index + 1) % 4
        faces.append((2 * index, 2 * index + 1, 2 * following + 1, 2 * following))

    mesh = bpy.data.meshes.new("HH_OCT_PAD_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    pad = bpy.data.objects.new("HH_OCT_PAD", mesh)
    bpy.context.collection.objects.link(pad)
    cleanup_mesh(pad)
    return pad


def add_grip_pads(body: bpy.types.Object, spec: OctopusHandSpec) -> bpy.types.Object:
    """Union one pad onto each plain diagonal of `body`.

    The body must own its mesh if the caller does not want every copy to change —
    here it is deliberately the shared master, so all twenty repeated bodies grip.
    """
    for heading in spec.grip_pad_angles_deg:
        boolean(body, create_pad(spec, heading), "UNION")
    cleanup_mesh(body)
    return body
