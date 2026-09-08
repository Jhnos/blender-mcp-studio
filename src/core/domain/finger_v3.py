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
    #:
    #: The window these live in is far narrower than it looks — see
    #: `smallest_usable_moment_arm_mm` and `largest_usable_moment_arm_mm`, which
    #: on the borrowed link leave barely a millimetre between them. The first
    #: draft of this spec used (7.0, 5.5, 4.0) and two of those three ran the
    #: tendon through the pin's wall.
    moment_arms_mm: tuple[float, ...] = field(default=(7.1, 6.6, 6.1))

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
        floor = self.smallest_usable_moment_arm_mm
        ceiling = self.largest_usable_moment_arm_mm
        for arm in arms:
            if arm < floor:
                raise ValueError(
                    f"moment arm {arm:.2f} mm runs the tendon into the pin's wall; "
                    f"the tendon and the pin share one cross-section and both need "
                    f"{self.link.minimum_wall_mm:.2f} mm, so {floor:.2f} mm is the floor"
                )
            if arm > ceiling:
                raise ValueError(
                    f"moment arm {arm:.2f} mm breaks the tendon bore out through the "
                    f"body wall; {ceiling:.2f} mm is the ceiling"
                )
        if self.tendon_travel_mm > self.actuator_stroke_mm:
            raise ValueError(
                "the tendon this finger needs is longer than the actuator stroke: "
                f"{self.tendon_travel_mm:.2f} mm wanted, {self.actuator_stroke_mm:.2f} available"
            )

    @property
    def smallest_usable_moment_arm_mm(self) -> float:
        """Closest the tendon may run to the axis before it eats the pin's wall.

        The tendon bore and the pin bore share one small cross-section at the
        joint. Walking the tendon inward is the obvious way to steepen the
        moment-arm gradient, and it is bounded by the pin long before it is
        bounded by anything anyone would think to check.
        """
        link = self.link
        return (
            link.printed_pin_bore_mm / 2 + link.minimum_wall_mm + link.tendon_hole_diameter_mm / 2
        )

    @property
    def largest_usable_moment_arm_mm(self) -> float:
        """Furthest out the bore may sit and still be inside the finger."""
        link = self.link
        return link.body_depth_mm / 2 - link.minimum_wall_mm - link.tendon_hole_diameter_mm / 2

    @property
    def moment_arm_window_mm(self) -> float:
        """How much room the gradient actually has. On the borrowed link: not much.

        Measured at 1.15 mm, which makes the moment-arm ratio between the base
        and tip joints about 1.16 — nowhere near enough to sequence three joints
        on its own. The consequence is a design decision, not a nuisance: with
        this link, closing order has to come from the spring stiffness gradient,
        and the moment arms only trim it.
        """
        return self.largest_usable_moment_arm_mm - self.smallest_usable_moment_arm_mm

    @property
    def hinge_axis(self) -> str:
        """Both ends of every phalanx turn about this one axis.

        The borrowed link does not: its male lug is on X and its female fork on
        Y, and that is exactly why its chain rule turns alternate units a quarter
        turn — the turn is what lets a male end enter the next unit's female end
        at all. Keeping perpendicular ends *and* stacking unrotated describes a
        finger that cannot be assembled: every dimension checks out, every part
        prints, and the second phalanx will not go onto the first.

        So V3's phalanx puts both ends on one axis. This is not a free choice
        alongside the planar decision — it is the same decision, and
        `joint_rotations_deg` below is its other half.
        """
        return "X"

    @property
    def male_hinge_axis(self) -> str:
        return self.hinge_axis

    @property
    def female_hinge_axis(self) -> str:
        return self.hinge_axis

    @property
    def joint_rotations_deg(self) -> tuple[float, ...]:
        """Every unit stacked unturned, so the finger curls in one plane.

        `HingePhalanxSpec` turns alternate units a quarter turn, which makes its
        assembly bend about alternating axes — right for a tentacle, wrong for a
        finger. A finger that wanders off its plane cannot meet a thumb, and
        opposition is the only reason the thumb exists.

        Stacking unrotated is only coherent because `hinge_axis` put both ends
        of the phalanx on one axis. Change one without the other and the finger
        stops going together.
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
