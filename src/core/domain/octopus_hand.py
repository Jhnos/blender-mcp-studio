"""Millimetre contract for the V1 five-armed, print-in-place tentacle hand.

The arm is `BiaxialHingeSpec` **composed, not subclassed** — V6 is a controlled
delivery and this profile must not be able to change it. Everything here is what
the palm adds: where the arm stations sit, how the pentagon must be sized to carry
them, where twenty tendons pass through, what the tip anchors, and whether the whole
thing fits the machine it is going to be printed on.

The bed limit is an invariant rather than a comment because it is what chose the
print pose: splayed flat the hand does not fit, standing upright it does. No claim
is made about strength, grip force or cable tension — these are fit-coupon dimensions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields

from src.core.domain.biaxial_hinge import BiaxialHingeSpec


@dataclass(frozen=True, slots=True)
class OctopusHandSpec:
    """No material-strength claim: dimensions describe a printable fit prototype."""

    arm_count: int = 5
    arm_joint_count: int = 4
    arm_station_radius_mm: float = 34.0
    palm_thickness_mm: float = 6.0
    palm_wall_mm: float = 2.0
    max_bed_mm: float = 220.0
    wire_channel_diameter_mm: float = 10.0
    tip_eyelet_diameter_mm: float = 3.0
    tip_eyelet_wall_mm: float = 1.8
    tip_claw_length_mm: float = 14.0
    tip_claw_thickness_mm: float = 3.0
    tip_claw_slope_deg: float = 40.0
    cable_relief_depth_mm: float = 1.0
    cable_relief_widening_mm: float = 0.6

    def __post_init__(self) -> None:
        if any(
            isinstance(getattr(self, field.name), bool)
            or not math.isfinite(getattr(self, field.name))
            or getattr(self, field.name) <= 0
            for field in fields(self)
        ):
            raise ValueError("dimensions must be finite and positive")
        if type(self.arm_count) is not int or not 3 <= self.arm_count <= 8:
            raise ValueError("arm count must be an integer between 3 and 8")
        if type(self.arm_joint_count) is not int:
            raise ValueError("arm joint count must be an integer")
        arm = self.arm_spec  # raises on an arm profile the hinge itself rejects
        if self.arm_station_radius_mm < self.minimum_station_radius_mm:
            raise ValueError("neighbouring arm bodies would intersect on the palm")
        if self.upright_footprint_mm > self.max_bed_mm:
            raise ValueError("upright print envelope exceeds the declared bed")
        innermost = min(
            math.hypot(x, y) - arm.tendon_hole_diameter_mm / 2
            for x, y in self.tendon_hole_positions_mm
        )
        if innermost <= self.wire_channel_diameter_mm / 2 + self.palm_wall_mm:
            raise ValueError("central wire channel breaks into the tendon holes")
        if (
            self.tip_eyelet_radius_mm + self.tip_eyelet_diameter_mm / 2 + self.tip_eyelet_wall_mm
            > arm.body_outer_diameter_mm / 2
        ):
            raise ValueError("tip eyelet leaves no wall in the end body")
        if self.tip_eyelet_diameter_mm <= arm.tendon_hole_diameter_mm:
            raise ValueError("tip eyelet must pass the cable the tendon holes carry")
        if self.tip_claw_slope_deg >= 45:
            raise ValueError("claw overhang would need support when printed upright")
        if self.palm_thickness_mm < arm.root_profile_mm[0][0] + self.palm_wall_mm:
            raise ValueError("palm is too thin to carry the socket roots")
        if self.cable_relief_depth_mm >= self.palm_thickness_mm / 2:
            raise ValueError("cable relief eats more than half the palm thickness")
        if self.closest_tendon_hole_gap_mm <= 2 * self.cable_relief_radius_mm:
            raise ValueError("cable reliefs would merge into each other")
        if innermost + arm.tendon_hole_diameter_mm / 2 - self.cable_relief_radius_mm <= (
            self.wire_channel_diameter_mm / 2
        ):
            raise ValueError("cable relief breaks into the central wire channel")

    @property
    def arm_spec(self) -> BiaxialHingeSpec:
        """The V6 profile, unchanged. Composition keeps its contract frozen."""
        return BiaxialHingeSpec(joint_count=self.arm_joint_count)

    @property
    def minimum_station_radius_mm(self) -> float:
        """Closest the arm axes may sit before neighbouring bodies touch."""
        arm = self.arm_spec
        span = max(arm.body_outer_diameter_mm / 2, arm.connector_envelope_radius_mm)
        return (2 * span + self.palm_wall_mm) / (2 * math.sin(math.pi / self.arm_count))

    @property
    def palm_inradius_mm(self) -> float:
        """Material must reach past every socket, so the flats govern, not the corners."""
        return (
            self.arm_station_radius_mm
            + self.arm_spec.connector_envelope_radius_mm
            + self.palm_wall_mm
        )

    @property
    def palm_circumradius_mm(self) -> float:
        return self.palm_inradius_mm / math.cos(math.pi / self.arm_count)

    @property
    def palm_across_corners_mm(self) -> float:
        return 2 * self.palm_circumradius_mm

    @property
    def arm_station_angles_deg(self) -> tuple[float, ...]:
        return tuple(index * 360.0 / self.arm_count for index in range(self.arm_count))

    @property
    def arm_station_positions_mm(self) -> tuple[tuple[float, float], ...]:
        return tuple(
            (
                self.arm_station_radius_mm * math.cos(math.radians(angle)),
                self.arm_station_radius_mm * math.sin(math.radians(angle)),
            )
            for angle in self.arm_station_angles_deg
        )

    @property
    def tendon_hole_positions_mm(self) -> tuple[tuple[float, float], ...]:
        """Every arm's four tendon holes, rotated onto its station in palm coordinates."""
        local = self.arm_spec.tendon_positions_mm
        placed: list[tuple[float, float]] = []
        for angle in self.arm_station_angles_deg:
            radians = math.radians(angle)
            cos_a, sin_a = math.cos(radians), math.sin(radians)
            origin_x = self.arm_station_radius_mm * cos_a
            origin_y = self.arm_station_radius_mm * sin_a
            placed.extend(
                (origin_x + x * cos_a - y * sin_a, origin_y + x * sin_a + y * cos_a)
                for x, y in local
            )
        return tuple(placed)

    @property
    def cable_relief_radius_mm(self) -> float:
        """A counterbore, not a chamfer: it recesses the bearing edge, not removes it."""
        return self.arm_spec.tendon_hole_diameter_mm / 2 + self.cable_relief_widening_mm

    @property
    def closest_tendon_hole_gap_mm(self) -> float:
        """Nearest centre-to-centre pair anywhere on the palm, across arms included."""
        holes = self.tendon_hole_positions_mm
        return min(
            math.dist(first, second)
            for index, first in enumerate(holes)
            for second in holes[index + 1 :]
        )

    @property
    def upright_footprint_mm(self) -> float:
        """Bed square needed with the palm flat and the arms standing up."""
        arms = 2 * (self.arm_station_radius_mm + self.arm_spec.connector_envelope_radius_mm)
        return max(arms, self.palm_across_corners_mm)

    @property
    def arm_body_count(self) -> int:
        return self.arm_spec.assembly_unit_count

    @property
    def arm_base_offset_mm(self) -> float:
        """Centre height of the first arm body above the palm's top face.

        The palm's top face stands in for a body centre plane: its socket carries
        the male ears the first arm body's female ears close on, so the first body
        sits one full pitch up, exactly as it would on another body.
        """
        return self.arm_spec.unit_pitch_mm

    @property
    def arm_tip_height_mm(self) -> float:
        """Top of the last arm body above the palm's top face, ears included."""
        arm = self.arm_spec
        return (
            self.arm_body_count * arm.unit_pitch_mm
            + arm.joint_center_offset_mm
            + arm.lug_outer_diameter_mm / 2
        )

    @property
    def upright_height_mm(self) -> float:
        return (
            self.palm_thickness_mm
            + self.arm_tip_height_mm
            + self.tip_eyelet_diameter_mm
            + 2 * self.tip_eyelet_wall_mm
        )

    @property
    def splayed_footprint_mm(self) -> float:
        """Kept for the comparison that rejected the flat pose; not a build target."""
        return 2 * (self.arm_station_radius_mm + self.arm_spec.assembled_height_mm)

    @property
    def tip_body_rotation_deg(self) -> float:
        """The last arm body's own twist in the chain, before its station angle.

        Bodies alternate ninety degrees up the chain so the ears meet, which means
        the last body does not face the way its arm does.
        """
        return 90.0 if self.arm_body_count % 2 else 0.0

    @property
    def tip_claw_direction_deg(self) -> float:
        """Local heading that aims the claw at the palm axis once the arm is placed."""
        return (180.0 - self.tip_body_rotation_deg) % 360.0

    @property
    def tip_eyelet_count(self) -> int:
        return len(self.arm_spec.tendon_positions_mm)

    @property
    def tip_eyelet_radius_mm(self) -> float:
        """Eyelets sit straight over the tendon exits so the cable never turns a corner."""
        return self.arm_spec.tendon_radius_mm

    @property
    def total_tendon_count(self) -> int:
        return self.arm_count * self.tip_eyelet_count

    @property
    def printable_part_types(self) -> tuple[str, str, str]:
        return ("octopus_palm", "biaxial_arm_body", "octopus_tip")
