"""Can the thumb meet the index fingertip? The one property that makes a palm a hand.

Every dimension of a palm can be right — sockets, lengths, plate width — and
the thing still not be a hand, because the thumb sweeps past the index instead
of meeting it. Opposition is the only reason a thumb exists, so it is the
acceptance condition, and it is computed rather than drawn.

A finger is a planar chain with known segment lengths and known joint limits,
so where its tip can go is arithmetic. Whether two such reachable sets come
within touching distance is arithmetic too. These functions take the palm as a
parameter; the palm keeps a three-line property that delegates here, the way
`bearing_seat_cuts` takes a link.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from src.core.domain.rotation import Axis3

if TYPE_CHECKING:
    from src.core.domain.palm_v3 import AnthropomorphicPalmSpec

#: Joint angles are sampled this coarsely when asking where a fingertip can
#: reach. On purpose: this answers "can these two ever meet", not "by what path".
POSTURE_STEP_DEG = 10.0


def posture_samples_deg(palm: AnthropomorphicPalmSpec) -> tuple[float, ...]:
    """Every step from straight to the finger link's own limit, inclusive.

    Derived, not listed. A literal `(0, …, 50)` was silently truncating any
    link that could bend further, and reporting a reach it never sampled.
    """
    limit = palm.finger.link.maximum_articulation_deg
    count = int(limit // POSTURE_STEP_DEG)
    return tuple(index * POSTURE_STEP_DEG for index in range(count + 1))


def posture_grid(palm: AnthropomorphicPalmSpec, joints: int) -> tuple[tuple[float, ...], ...]:
    allowed = posture_samples_deg(palm)
    grid: list[tuple[float, ...]] = [()]
    for _ in range(joints):
        grid = [(*posture, angle) for posture in grid for angle in allowed]
    return tuple(grid)


def row_tip_world(
    palm: AnthropomorphicPalmSpec, x_mm: float, angles_deg: tuple[float, ...]
) -> Axis3:
    palmar, along = palm.fingertip_in_finger_frame_mm(angles_deg)
    return (x_mm, palmar, along)


def thumb_tip_world(palm: AnthropomorphicPalmSpec, angles_deg: tuple[float, ...]) -> Axis3:
    palmar, along = palm.tip_in_frame_mm(palm.thumb_segment_lengths_mm, angles_deg)
    axis, pad = palm.thumb_frame
    origin = palm.thumb_root_mm
    return (
        origin[0] + along * axis[0] - palmar * pad[0],
        origin[1] + along * axis[1] - palmar * pad[1],
        origin[2] + along * axis[2] - palmar * pad[2],
    )


#: Axis positions are sampled this finely when the resting thumb is checked
#: against the row. Fine enough that a joint gap of a few millimetres is seen.
REST_SAMPLE_STEP_MM = 1.0


def _unit_axis_samples(
    chain_lift_mm: float, link_pitch_mm: float, half_length_mm: float, units: int
) -> list[tuple[float, float]]:
    """(distance along the chain, distance from that unit's centre) for every sample."""
    samples: list[tuple[float, float]] = []
    steps = int(2 * half_length_mm / REST_SAMPLE_STEP_MM)
    for index in range(units):
        centre = chain_lift_mm + index * link_pitch_mm
        for step in range(steps + 1):
            local = -half_length_mm + step * REST_SAMPLE_STEP_MM
            samples.append((centre + local, local))
    return samples


def _extent_towards(
    width_mm: float, depth_mm: float, length_mm: float, local_mm: float, direction_local: Axis3
) -> float:
    """How far an ellipsoid body reaches from its axis point towards `direction_local`.

    The body is the ellipsoid (width, depth, length); at `local_mm` along its
    axis the cross-section shrinks, and the support in a direction is the
    ellipse's radius that way.
    """
    half = length_mm / 2
    if abs(local_mm) >= half:
        return 0.0
    taper = math.sqrt(1.0 - (local_mm / half) ** 2)
    dx, dy, _ = direction_local
    horizontal = math.hypot(dx, dy)
    if horizontal < 1e-12:
        return 0.0
    ux, uy = dx / horizontal, dy / horizontal
    return taper * math.sqrt((width_mm / 2 * ux) ** 2 + (depth_mm / 2 * uy) ** 2) * horizontal


def thumb_rest_clearance_mm(palm: AnthropomorphicPalmSpec) -> float:
    """Closest the straight thumb comes to any straight row finger, surface to surface.

    Negative means they pass through each other at rest. Bodies are the
    ellipsoids the phalanx plan builds; lugs and necks are thinner and are
    not modelled, so a small positive number here is not a guarantee — the
    real-machine disjoint gate remains the ground truth. This is what lets a
    placement be refused before Blender ever builds it.
    """
    link = palm.finger.link
    thumb_link = palm.thumb.link
    width, depth, length = link.body_width_mm, link.body_depth_mm, link.body_length_mm
    t_width, t_depth, t_length = (
        thumb_link.body_width_mm,
        thumb_link.body_depth_mm,
        thumb_link.body_length_mm,
    )
    lift = 2 * link.joint_center_offset_mm
    t_lift = link.joint_center_offset_mm + thumb_link.joint_center_offset_mm
    axis, pad = palm.thumb_frame
    across = (
        axis[1] * pad[2] - axis[2] * pad[1],
        axis[2] * pad[0] - axis[0] * pad[2],
        axis[0] * pad[1] - axis[1] * pad[0],
    )
    root = palm.thumb_root_mm

    finger_samples = _unit_axis_samples(
        lift, link.unit_pitch_mm, length / 2, link.assembly_unit_count
    )
    thumb_samples = _unit_axis_samples(
        t_lift, thumb_link.unit_pitch_mm, t_length / 2, thumb_link.assembly_unit_count
    )
    best = math.inf
    for along, t_local in thumb_samples:
        thumb_point = tuple(root[i] + along * axis[i] for i in range(3))
        for x_mm in palm.row_finger_x_mm:
            for height, f_local in finger_samples:
                finger_point = (x_mm, 0.0, height)
                gap_vector = tuple(finger_point[i] - thumb_point[i] for i in range(3))
                distance = math.sqrt(sum(component**2 for component in gap_vector))
                if distance < 1e-9:
                    best = min(best, -max(width, depth))
                    continue
                unit = tuple(component / distance for component in gap_vector)
                # Finger frame is the world frame; the thumb's is (across, pad, axis).
                finger_reach = _extent_towards(
                    width, depth, length, f_local, (-unit[0], -unit[1], -unit[2])
                )
                thumb_dir = (
                    sum(unit[i] * across[i] for i in range(3)),
                    sum(unit[i] * pad[i] for i in range(3)),
                    sum(unit[i] * axis[i] for i in range(3)),
                )
                thumb_reach = _extent_towards(t_width, t_depth, t_length, t_local, thumb_dir)
                best = min(best, distance - finger_reach - thumb_reach)
    return best


def thumb_index_tip_gap_mm(palm: AnthropomorphicPalmSpec) -> float:
    """Closest the thumb tip can come to the index tip, over both reachable sets.

    A reachability question, not a posture: it asks whether *some* pair of
    postures brings the tips together, which is what "opposable" means. The
    grid is coarse, and `pinch_contact_mm` is correspondingly generous.
    """
    index_x = palm.row_finger_x_mm[0]
    row_tips = [
        row_tip_world(palm, index_x, angles)
        for angles in posture_grid(palm, palm.finger.link.joint_count)
    ]
    best = math.inf
    for thumb_angles in posture_grid(palm, palm.thumb.link.joint_count):
        thumb = thumb_tip_world(palm, thumb_angles)
        for tip in row_tips:
            gap = math.dist(thumb, tip)
            if gap < best:
                best = gap
    return best
