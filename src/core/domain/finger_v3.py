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
    #:
    #: The joint centre is pushed out from the borrowed default of 24.0 mm.
    #: At 24.0 the lug reaches 30.5 mm while the next body starts at 28.0, so the
    #: two separately printed parts share 2.5 mm of space. The borrowed spec
    #: allows it — its own rule only asks that the joint centre clear the body
    #: *centre* — and the archived generator that shipped that arrangement never
    #: had a contract to fail. Measured on the built stack: 303 overlapping faces.
    link: HingePhalanxSpec = HingePhalanxSpec(joint_count=3, joint_center_offset_mm=27.0)

    #: How far the actuator can pull the cable. The finger is refused if the
    #: three joints together want more than this.
    actuator_stroke_mm: float = 30.0

    #: Where the tendon runs from each joint's axis, proximal first. Two jobs at
    #: once: it sets how much cable that joint eats, and how much torque the same
    #: cable tension delivers there.
    #:
    #: Equal by default, which is a measured conclusion rather than a
    #: simplification. The window these can live in is 6.05-7.20 mm — the pin bore
    #: bounds one end and the body wall the other — so the steepest gradient
    #: available is a ratio of 1.19, nowhere near enough to sequence three joints.
    #: Order comes from the spring stiffness gradient; the arms only trim force.
    #: Equal arms therefore buy one printed part instead of three for nothing
    #: given up. A future link with a thinner pin reopens the window, which is why
    #: this stays a tuple.
    moment_arms_mm: tuple[float, ...] = field(default=(6.6, 6.6, 6.6))

    #: Where the wiring runs, on the back of the finger. V1 and V2 sent sensor
    #: wiring down a channel on the body's own axis and forbade the pin from
    #: intruding on it. This link is a different hinge — its pin passes straight
    #: through the axis — so a central channel would open into the pin bore, and
    #: the contract declares the axis solid for that reason. That is not a reason
    #: to have no wiring path at all, which is what the first version of this spec
    #: quietly meant. Mirroring the tendon puts it clear of the pin and clear of
    #: the wall, at the same diameter, on the side nothing else uses.
    wiring_bore_offset_mm: float = 6.6

    def __post_init__(self) -> None:
        numbers = (self.actuator_stroke_mm, *self.moment_arms_mm)
        if any(
            isinstance(value, bool) or not math.isfinite(value) or value <= 0 for value in numbers
        ):
            raise ValueError("dimensions must be finite and positive")
        if len(self.moment_arms_mm) != self.link.joint_count:
            raise ValueError("every joint needs exactly one moment arm")
        arms = self.moment_arms_mm
        if not all(nearer >= further for nearer, further in zip(arms, arms[1:], strict=False)):
            raise ValueError(
                "moment arms must never grow towards the tip, or the finger curls "
                f"from the fingertip and rolls objects out of the hand: {arms}"
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
        if self.adjacent_body_clearance_mm <= 0:
            link = self.link
            raise ValueError(
                "the lug reaches "
                f"{link.joint_center_offset_mm + link.lug_outer_diameter_mm / 2:.2f} mm "
                "and the next unit's body starts at "
                f"{link.unit_pitch_mm - link.body_length_mm / 2:.2f} mm, so two "
                "separately printed parts would occupy the same space"
            )
        link = self.link
        if self.wiring_bore_offset_mm <= 0:
            raise ValueError(
                "the wiring bore belongs on the back of the finger; a negative offset "
                "puts it on the tendon's own side, where it would meet the cable"
            )
        to_pin = (
            self.wiring_bore_offset_mm
            - link.tendon_hole_diameter_mm / 2
            - link.printed_pin_bore_mm / 2
        )
        to_wall = (
            link.body_depth_mm / 2 - self.wiring_bore_offset_mm - link.tendon_hole_diameter_mm / 2
        )
        if to_pin < link.minimum_wall_mm:
            raise ValueError(
                f"the wiring bore leaves {to_pin:.2f} mm against the pin bore, under the "
                f"{link.minimum_wall_mm:.2f} mm minimum wall"
            )
        if to_wall < link.minimum_wall_mm:
            raise ValueError(
                f"the wiring bore leaves {to_wall:.2f} mm to the outer wall, under the "
                f"{link.minimum_wall_mm:.2f} mm minimum"
            )
        if self.tendon_travel_mm > self.actuator_stroke_mm:
            raise ValueError(
                "the tendon this finger needs is longer than the actuator stroke: "
                f"{self.tendon_travel_mm:.2f} mm wanted, {self.actuator_stroke_mm:.2f} available"
            )

    @property
    def adjacent_body_clearance_mm(self) -> float:
        """Gap between one unit's lug and the next unit's body, along the stack.

        Nothing in the borrowed link measures this: it checks that the joint
        centre clears the body centre, which says nothing about whether the lug
        standing proud of that centre reaches into the neighbour a whole pitch
        away. Two separately printed parts sharing millimetres is not a Boolean
        problem — each mesh is watertight — it is an assembly that cannot exist.
        """
        link = self.link
        lug_reach = link.joint_center_offset_mm + link.lug_outer_diameter_mm / 2
        next_body_starts = link.unit_pitch_mm - link.body_length_mm / 2
        return next_body_starts - lug_reach

    def _palmar_gap_mm(self, flexion_deg: float) -> float:
        """Closest approach of two adjacent bodies' palmar faces, at one posture.

        Both faces are straight lines in the bending plane, so the distance is
        found by sampling them rather than by solving: the faces are short, the
        sampling is dense, and the number only ever feeds an upper bound.
        """
        link = self.link
        half_length = link.body_length_mm / 2.0
        palmar = -link.body_depth_mm / 2.0
        centre = (0.0, link.joint_center_offset_mm)
        angle = math.radians(flexion_deg)

        def turned(point: tuple[float, float]) -> tuple[float, float]:
            y, z = point[0] - centre[0], point[1] - centre[1]
            return (
                centre[0] + y * math.cos(angle) - z * math.sin(angle),
                centre[1] + y * math.sin(angle) + z * math.cos(angle),
            )

        steps = 21
        near = [
            (palmar, half_length - index * (link.body_length_mm / (steps - 1)))
            for index in range(steps)
        ]
        far = [
            turned(
                (
                    palmar,
                    link.unit_pitch_mm - half_length + index * (link.body_length_mm / (steps - 1)),
                )
            )
            for index in range(steps)
        ]
        return min(math.dist(one, other) for one in near for other in far)

    @property
    def palmar_surface_gap_at_rest_mm(self) -> float:
        """How far apart the gripping faces are with the finger straight."""
        return self._palmar_gap_mm(0.0)

    @property
    def palmar_surface_gap_at_full_flexion_mm(self) -> float:
        """The same faces once the finger has closed as far as it can."""
        return self._palmar_gap_mm(self.link.maximum_articulation_deg)

    @property
    def maximum_interlayer_thickness_mm(self) -> float:
        """Thickest the inflated layer may become without costing travel.

        The bladder has never been built and its real inflated thickness is a
        bench measurement. This is the other half of that question, and it is
        pure geometry: past this, the two gloves meet before the joints do, and
        pushing the syringe buys surface by spending flexion. It is the number a
        glove purchase has to respect.
        """
        return self.palmar_surface_gap_at_full_flexion_mm / 2.0

    @property
    def tendon_bore_offset_mm(self) -> float:
        """Where the tendon runs, palmar, hence negative."""
        return -self.moment_arms_mm[0]

    @property
    def phalanx_part_count(self) -> int:
        """How many distinct parts have to be printed and kept track of."""
        return len(set(self.moment_arms_mm))

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
