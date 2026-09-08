"""Turning a direction in space, with no knowledge of what is being turned.

Split out of `palm_v3` when that module reached its line budget. The seam is
not arbitrary: where a thumb's pad ends up pointing is palm knowledge, but how
a vector turns about an axis is not, and the budget gate asked for the cut
while the seam was still obvious.

The alias here is `Axis3` rather than `Vector3` on purpose — `Vector3` is
already a dataclass in `scene_operations`, and the palm module had quietly
defined a second, unrelated thing under that name.
"""

from __future__ import annotations

import math

#: A direction or a point as a bare triple. Not `scene_operations.Vector3`,
#: which is a value object carrying a scene's units and defaults.
Axis3 = tuple[float, float, float]


def rotate_y(vector: Axis3, degrees: float) -> Axis3:
    """Turn about the global Y axis."""
    angle = math.radians(degrees)
    x, y, z = vector
    return (
        x * math.cos(angle) + z * math.sin(angle),
        y,
        -x * math.sin(angle) + z * math.cos(angle),
    )


def roll_about(vector: Axis3, axis: Axis3, degrees: float) -> Axis3:
    """Turn `vector` about `axis` — a roll, not a turn about a global axis.

    The difference is not pedantic. Rolling the thumb's pad about the global Z
    while its own axis had already been swung leaves the two no longer square:
    measured at a dot product of -0.166, a frame that is a parallelogram rather
    than a corner, so every tip position computed in it is wrong by an amount
    that changes with posture.
    """
    angle = math.radians(degrees)
    cos = math.cos(angle)
    sin = math.sin(angle)
    dot = sum(a * b for a, b in zip(axis, vector, strict=True))
    cross = (
        axis[1] * vector[2] - axis[2] * vector[1],
        axis[2] * vector[0] - axis[0] * vector[2],
        axis[0] * vector[1] - axis[1] * vector[0],
    )
    return tuple(  # type: ignore[return-value]
        vector[index] * cos + cross[index] * sin + axis[index] * dot * (1.0 - cos)
        for index in range(3)
    )
