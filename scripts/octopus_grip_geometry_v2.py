"""Grip pads on the four cardinals, aimed at whatever the hand is closing on.

V1 put its pads on the diagonals and said the cardinals were taken by the ears. Out at
the rim they are not: measured on the real V1 mesh, no ear or root reaches past
16.70 mm on a cardinal and the pad's buried face starts at 17.00 mm. Aiming them is
also the roomier placement — swept through the joint's full travel, pad-to-pad
clearance is 0.204 mm on the diagonals and 0.553 mm on the cardinals.

The section is V1's, one point longer. The extra point is a chamfer on the pad's upward
face, so the pad eases into the disc instead of ending on a square edge; the underside
chamfer it already had is what keeps it printable standing proud of a horizontal disc.

No grip-force claim: these are contact areas, not a rated gripper.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from scripts.blender_mesh_primitives import boolean, cleanup_mesh, loft_rings
from src.core.domain.octopus_hand_v2 import OctopusHandV2Spec


def create_pad(spec: OctopusHandV2Spec, heading_deg: float) -> bpy.types.Object:
    """One pad, built in a radial/tangential frame and swung to its heading.

    The two rails are the pad's side faces: each walks the same closed section at a
    constant *angle* off the heading, so the pad widens with radius and its outer face
    is a chord — which is why the envelope is read from the corners, not the face.
    """
    half_arc = math.tan(math.radians(spec.grip_pad_arc_deg / 2))
    heading = math.radians(heading_deg)
    cos_h, sin_h = math.cos(heading), math.sin(heading)

    rails: list[list[tuple[float, float, float]]] = []
    for side in (-1.0, 1.0):
        rail: list[tuple[float, float, float]] = []
        for radius, height in spec.grip.pad_profile_mm:
            tangent = side * radius * half_arc
            rail.append(
                (radius * cos_h - tangent * sin_h, radius * sin_h + tangent * cos_h, height)
            )
        rails.append(rail)
    return loft_rings("HH_OCT2_PAD", rails)


def add_grip_pads(body: bpy.types.Object, spec: OctopusHandV2Spec) -> bpy.types.Object:
    """Union one pad onto each cardinal of `body`.

    The cardinal set maps onto itself under the chain's ninety degree twist, exactly as
    the diagonals did, so every body in the arm still shares this one mesh — and every
    body, whatever its twist, ends up with a pad pointing at the palm's centre.
    """
    for heading in spec.grip_pad_angles_deg:
        boolean(body, create_pad(spec, heading), "UNION")
    cleanup_mesh(body)
    return body


def assert_cap_faces_the_pads(tip: bpy.types.Object, spec: OctopusHandV2Spec) -> None:
    """The built cap must present a flat face down every direction a pad aims.

    The spec already refuses a facet count and phase that cannot do this, but that is
    arithmetic: it says nothing about the mesh the arithmetic was supposed to produce.
    The first attempt at this fix changed the facet count and left `create_cap` building
    at phase zero, and every domain test stayed green while the built tip still met all
    four grip directions on a corner.

    Measured by ray, not by scanning normals. A normal scan was written first and was
    not discriminating: the centre channel and the cable bores are drilled with
    twenty-four segments, so their walls offer a normal within half a degree of any
    heading you care to name, and the scan passed a cap deliberately turned off-aim.
    The ray answers the question that was actually asked — what does the first surface
    a finger touches look like — and nothing behind that surface can vote.

    Deliberately not in `octopus_tip_geometry`: V1's cap is *meant* to sit edge-on to its
    diagonal pads and is a frozen delivery. This is V2's requirement, so it lives with
    V2's aimed surfaces and runs only on V2's generator.
    """
    tree = BVHTree.FromPolygons(
        [vertex.co.copy() for vertex in tip.data.vertices],
        [tuple(polygon.vertices) for polygon in tip.data.polygons],
        all_triangles=False,
        epsilon=0.0,
    )
    height = (spec.tip_cap_shoulder_z_mm + spec.tip_cap_top_z_mm) / 2 * 0.001
    start = 3 * spec.tip_cap_max_radius_mm * 0.001
    for heading in spec.grip_pad_angles_deg:
        radians = math.radians(heading)
        inward = Vector((-math.cos(radians), -math.sin(radians), 0.0))
        origin = Vector((-start * inward.x, -start * inward.y, height))
        _, normal, _, _ = tree.ray_cast(origin, inward)
        if normal is None:
            raise RuntimeError(
                f"nothing stands in the way of a finger pressing from {heading:.0f} "
                "degrees — the cap has a hole where its gripping face should be"
            )
        flat = Vector((normal.x, normal.y, 0.0))
        off_deg = math.degrees(flat.angle(-inward)) if flat.length > 1e-9 else 90.0
        if off_deg > 0.5:
            raise RuntimeError(
                f"the surface a finger meets at {heading:.0f} degrees stands {off_deg:.1f} "
                "degrees off square — that finger presses on an edge, not a face"
            )
