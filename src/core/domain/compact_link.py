"""A phalanx sized for a human finger, which means a joint with no bearing in it.

The borrowed `HingePhalanxSpec` cannot reach human scale, and exactly one
dimension is responsible. Its moment arms are floored by the pin bore plus a
wall plus the tendon — 6.05 mm — and not one of those three shrinks when the
body does. The ceiling is set by body depth and falls as the body narrows, so
the two close on each other: at 22 mm of depth the whole usable window is
1.15 mm wide, a ratio of 1.19 between the widest and narrowest arm a joint may
have. That is nowhere near enough to sequence three joints, which is why V3
had to hand the ordering entirely to its return springs.

That was written down as a property of the machine. It is a property of the pin.

Halve the pin, delete the bearing, and thin the walls to what a 0.4 mm nozzle
actually lays down, and the same window at 15 mm of depth runs 3.15 to 5.55 mm
— a ratio of 1.76, and a body seven millimetres shallower. The moment arms can
order the joints again.

Prior art agrees and goes further: of the closest open designs, `100_fingers`
replaces the joint with a living hinge and `RoninHand` prints its joints in
place, both deleting the pin rather than shrinking it. Those are the better
long-term answers and they are also a different verification problem — a living
hinge fails by fatigue, which is a material property no geometry contract can
measure. Shrinking the pin keeps every check this repo already owns and every
number the coupon print is about to produce. See `docs/hand-v3/01-prior-art.md`.

Nothing here is validated by a printed part. The clearances are the numbers the
coupon exists to confirm, and until it is printed they are intentions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CompactHingeLinkSpec:
    """Millimetre dimensions for a bearingless finger link at human scale.

    A separate class rather than different arguments to `HingePhalanxSpec`,
    because that spec's invariants encode the octopus arm it was drawn for — a
    pin of at least 3 mm and a seat that must hold a rolling element. Loosening
    them would weaken a frozen deliverable to make room for a new machine, which
    is the wrong direction. Both satisfy `FingerLinkSpec`; that is the whole of
    what they need to share.
    """

    joint_count: int = 2
    #: 38 x 17 x 15. Depth is the governing number: it sets the moment-arm
    #: ceiling, and 15 mm is about a human proximal phalanx.
    body_length_mm: float = 38.0
    body_width_mm: float = 17.0
    body_depth_mm: float = 15.0
    #: Chosen from the reach it produces, not picked. A three-unit finger spans
    #: `4 x offset + lug / 2`, so 24.0 gives 98.5 mm — a human finger is roughly
    #: 100 mm from base joint to tip.
    joint_center_offset_mm: float = 24.0
    tendon_hole_diameter_mm: float = 1.5
    #: The default moment arm, mid-window rather than at either edge.
    tendon_radius_mm: float = 4.5
    pin_diameter_mm: float = 2.0
    printed_radial_clearance_mm: float = 0.20
    #: No seat: the lug is bored to the pin and nothing else. Held equal to the
    #: bore so any consumer that subtracts a seat removes nothing, and stated
    #: again through `has_bearing_seat` so no one has to notice the equality.
    bearing_seat_diameter_mm: float = 2.4
    bearing_width_mm: float = 0.0
    lug_outer_diameter_mm: float = 5.0
    male_tongue_thickness_mm: float = 3.0
    fork_gap_mm: float = 3.4
    fork_lug_thickness_mm: float = 2.5
    #: What a 0.4 mm nozzle lays down reliably in three passes.
    minimum_wall_mm: float = 1.2
    maximum_articulation_deg: float = 50.0

    def __post_init__(self) -> None:
        if not 1 <= self.joint_count <= 8:
            raise ValueError("joint_count must be between 1 and 8")
        if self.minimum_wall_mm < 0.8:
            raise ValueError("minimum wall must be at least 0.8 mm")
        if self.pin_diameter_mm < 1.5:
            raise ValueError("a pin under 1.5 mm bends during assembly")
        if not 0.15 <= self.printed_radial_clearance_mm <= 0.5:
            raise ValueError("printed pin clearance must be between 0.15 and 0.5 mm")
        if not self.body_length_mm > self.body_width_mm > self.body_depth_mm:
            raise ValueError("phalanx body must be longer than its oval cross section")
        if self.lug_outer_diameter_mm < self.printed_pin_bore_mm + 2.0 * self.minimum_wall_mm:
            raise ValueError("the lug leaves no wall around the pin bore")
        required_gap = self.male_tongue_thickness_mm + 2.0 * self.printed_radial_clearance_mm
        if self.fork_gap_mm < required_gap:
            raise ValueError("fork gap must clear the male tongue")
        if self.fork_total_width_mm > self.body_depth_mm:
            raise ValueError("fork width must fit the phalanx depth")
        # The invariant this class exists for. Every per-dimension rule above can
        # pass while the tendon has nowhere legal to run, because the floor and
        # the ceiling are set by different things and neither one knows about the
        # other. Halving the pin again would look fine everywhere else and leave
        # a joint nothing to turn on.
        if self.largest_usable_moment_arm_mm <= self.smallest_usable_moment_arm_mm:
            raise ValueError(
                "the pin bore and the body depth have closed on each other: "
                f"the tendon may sit between {self.smallest_usable_moment_arm_mm:.2f} and "
                f"{self.largest_usable_moment_arm_mm:.2f} mm, which is nowhere"
            )
        if self.minimum_tendon_edge_wall_mm < self.minimum_wall_mm:
            raise ValueError("tendon holes leave insufficient body wall")
        if self.adjacent_body_clearance_mm <= 0.0:
            raise ValueError("a unit's lug reaches into the next unit's body")
        if not 10.0 <= self.maximum_articulation_deg <= 65.0:
            raise ValueError("maximum articulation must stay between 10 and 65 degrees")

    @property
    def assembly_unit_count(self) -> int:
        return self.joint_count + 1

    @property
    def printed_pin_bore_mm(self) -> float:
        return self.pin_diameter_mm + 2.0 * self.printed_radial_clearance_mm

    @property
    def fork_total_width_mm(self) -> float:
        return self.fork_gap_mm + 2.0 * self.fork_lug_thickness_mm

    @property
    def unit_pitch_mm(self) -> float:
        return 2.0 * self.joint_center_offset_mm

    @property
    def has_bearing_seat(self) -> bool:
        """No. That absence is the design, not an omission."""
        return False

    @property
    def common_hardware(self) -> tuple[str, ...]:
        return ("2mm_pin",)

    @property
    def smallest_usable_moment_arm_mm(self) -> float:
        """Pin bore, a wall, and half the tendon. None of this shrinks with the body."""
        return (
            self.printed_pin_bore_mm / 2.0
            + self.minimum_wall_mm
            + self.tendon_hole_diameter_mm / 2.0
        )

    @property
    def largest_usable_moment_arm_mm(self) -> float:
        """Furthest out the bore may sit and still be inside the finger."""
        return self.body_depth_mm / 2.0 - self.minimum_wall_mm - self.tendon_hole_diameter_mm / 2.0

    @property
    def moment_arm_window_ratio(self) -> float:
        """Widest arm over narrowest. Under about 1.5 the springs must do the ordering."""
        return self.largest_usable_moment_arm_mm / self.smallest_usable_moment_arm_mm

    @property
    def minimum_tendon_edge_wall_mm(self) -> float:
        hole_radius = self.tendon_hole_diameter_mm / 2.0
        across = self.body_width_mm / 2.0 - self.tendon_radius_mm - hole_radius
        through = self.body_depth_mm / 2.0 - self.tendon_radius_mm - hole_radius
        return min(across, through)

    @property
    def adjacent_body_clearance_mm(self) -> float:
        """Gap between one unit's lug and the next unit's body, at rest.

        The borrowed link is negative here by 2.5 mm at its own defaults, which
        is two separately printed parts sharing the same space. Kept as a named
        quantity so it can never be negative unnoticed again.
        """
        lug_reach = self.joint_center_offset_mm + self.lug_outer_diameter_mm / 2.0
        next_body_starts = self.unit_pitch_mm - self.body_length_mm / 2.0
        return next_body_starts - lug_reach

    @property
    def assembled_height_mm(self) -> float:
        return (self.assembly_unit_count - 1) * self.unit_pitch_mm + (
            2.0 * self.joint_center_offset_mm + self.lug_outer_diameter_mm
        )
