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
