"""A finger whose three joints close on one tendon.

V1 and V2 gave every joint its own cable — twenty of them across five arms — so
"can the actuator close this?" was never a question anyone had to ask. Driving
three joints from one cable makes it the first question, and it is not answered
by any per-part check: the cable a finger needs is the *sum* of what each joint
takes, and a finger can be watertight, collision-free and print-ready while
demanding more cable than the actuator can pull. It simply never closes.

So the sum is a property with a rejection branch.

This composes `HingePhalanxSpec` rather than inheriting from the octopus hand.
V3 is not an octopus hand: the octopus specs assume radial symmetry and biaxial
joints, and a subtype that cannot honour its supertype's invariants is not a
subtype. Composition also lets V3 override the one thing it must: the borrowed
chain alternates its joint axes 0/90 down the stack, which is right for a
tentacle and wrong for a finger, because a finger bends in one plane.

No force claim: moment arms and stroke are geometry. What the finger can hold
is measured on a bench, not derived here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from src.core.domain.hinge_chain import HingePhalanxSpec


@dataclass(frozen=True, slots=True)
class SingleTendonFingerSpec:
    """No grip-force claim: these are lengths and angles, not a rated finger."""

    #: The link geometry is borrowed whole — fork, tongue, bearing seats, pin,
    #: tendon holes and every printability rule that comes with them. Three
    #: joints means four units: the one bolted into the palm, then three phalanges.
    link: HingePhalanxSpec = HingePhalanxSpec(joint_count=3)

    #: How far the actuator can pull the cable. The finger is refused if the
    #: three joints together want more than this.
    actuator_stroke_mm: float = 30.0

    #: Where the tendon runs from each joint's axis, proximal first. Two jobs at
    #: once: it sets how much cable that joint eats, and how much torque the same
    #: cable tension delivers there.
    moment_arms_mm: tuple[float, ...] = field(default=(7.0, 5.5, 4.0))

    def __post_init__(self) -> None:
        numbers = (self.actuator_stroke_mm, *self.moment_arms_mm)
        if any(
            isinstance(value, bool) or not math.isfinite(value) or value <= 0 for value in numbers
        ):
            raise ValueError("dimensions must be finite and positive")
        if len(self.moment_arms_mm) != self.link.joint_count:
            raise ValueError("every joint needs exactly one moment arm")
        arms = self.moment_arms_mm
        if not all(nearer > further for nearer, further in zip(arms, arms[1:], strict=False)):
            raise ValueError(
                "moment arms must shrink towards the tip, so the finger curls from "
                f"the knuckle rather than from the fingertip: {arms}"
            )
        if self.tendon_travel_mm > self.actuator_stroke_mm:
            raise ValueError(
                "the tendon this finger needs is longer than the actuator stroke: "
                f"{self.tendon_travel_mm:.2f} mm wanted, {self.actuator_stroke_mm:.2f} available"
            )

    @property
    def joint_rotations_deg(self) -> tuple[float, ...]:
        """Every unit stacked unturned, so the finger curls in one plane.

        This is the one borrowed rule V3 must replace. `HingePhalanxSpec` turns
        alternate units a quarter turn, which makes its assembly bend about
        alternating axes — right for a tentacle, wrong for a finger. A finger
        that wanders off its plane cannot meet a thumb, and opposition is the
        only reason the thumb exists.
        """
        return tuple(0.0 for _ in range(self.link.assembly_unit_count))

    @property
    def tendon_travel_mm(self) -> float:
        """Cable consumed going from fully straight to fully closed.

        Each joint pulls its moment arm through its own arc, so the finger's
        demand is the sum. This is the quantity no per-part check can see.
        """
        full = math.radians(self.link.maximum_articulation_deg)
        return sum(arm * full for arm in self.moment_arms_mm)
