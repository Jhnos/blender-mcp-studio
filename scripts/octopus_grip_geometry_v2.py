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
