"""Millimetre contract for the V1 five-armed, print-in-place tentacle hand.

The arm is `BiaxialHingeSpec` **composed, not subclassed** — V6 is a controlled
delivery and this profile must not be able to change it. Everything here is what
the hand adds: where the arm stations sit, how the pentagon must be sized to carry
them, where twenty tendons pass through, what grips, and whether the whole thing
fits the machine it is going to be printed on.

Two of these invariants shape the design rather than merely guard it. The printer
bed chose the print pose, because splayed flat the hand does not fit. And the palm
socket is twisted a quarter turn off its arm's radial heading, because a hinge
turns about its pin: leave the pin along the radius and the first joint swings the
arm sideways around the palm instead of closing on what it is holding.

No claim is made about strength, grip force or cable tension — these are fit-coupon
dimensions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields

from src.core.domain.biaxial_hinge import BiaxialHingeSpec
from src.core.domain.octopus_grip import GripSurfaceSpec


@dataclass(frozen=True, slots=True)
class OctopusHandSpec:
    """No material-strength claim: dimensions describe a printable fit prototype."""

    arm_count: int = 5
    arm_joint_count: int = 4
    arm_station_radius_mm: float = 41.5
    palm_thickness_mm: float = 6.0
    palm_wall_mm: float = 2.0
    max_bed_mm: float = 220.0
    wire_channel_diameter_mm: float = 10.0
    grip_outer_diameter_mm: float = 42.0
    grip_pad_height_mm: float = 8.0
    grip_pad_arc_deg: float = 50.0
    grip_pad_slope_deg: float = 45.0
    tip_facet_count: int = 6
    tip_cap_flare_mm: float = 3.0
    tip_cap_height_mm: float = 14.0
    tip_cap_top_diameter_mm: float = 22.0
    tip_cable_bore_diameter_mm: float = 3.0
    tip_feature_fuse_mm: float = 1.0
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
        if type(self.tip_facet_count) is not int or self.tip_facet_count < 3:
            raise ValueError("tip facet count must be an integer of at least 3")
        arm = self.arm_spec  # raises on an arm profile the hinge itself rejects

        # Building the grip profile enforces its own printability rules; what this
        # layer adds is that those surfaces must actually stand proud of the body.
        if self.grip.grip_envelope_radius_mm <= arm.body_outer_diameter_mm / 2:
            raise ValueError("grip surfaces do not reach past the body they sit on")

        if self.arm_station_radius_mm < self.minimum_station_radius_mm:
            raise ValueError("neighbouring arms would intersect on the palm")
        if self.upright_footprint_mm > self.max_bed_mm:
            raise ValueError("upright print envelope exceeds the declared bed")
        innermost = min(
            math.hypot(x, y) - arm.tendon_hole_diameter_mm / 2
            for x, y in self.tendon_hole_positions_mm
        )
        if innermost <= self.wire_channel_diameter_mm / 2 + self.palm_wall_mm:
            raise ValueError("central wire channel breaks into the tendon holes")

        if self.palm_thickness_mm < arm.root_profile_mm[0][0] + self.palm_wall_mm:
            raise ValueError("palm is too thin to carry the socket roots")
        if self.cable_relief_depth_mm >= self.palm_thickness_mm / 2:
            raise ValueError("cable relief eats more than half the palm thickness")
        if self.closest_tendon_hole_gap_mm <= 2 * self.cable_relief_radius_mm:
            raise ValueError("cable reliefs would merge into each other")

    # ---------------------------------------------------------------- the arm

    @property
    def arm_spec(self) -> BiaxialHingeSpec:
        """The V6 profile, unchanged. Composition keeps its contract frozen."""
        return BiaxialHingeSpec(joint_count=self.arm_joint_count)

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

    # ------------------------------------------------------------- joint axes

    @property
    def palm_socket_twist_deg(self) -> float:
        """Twist of the palm socket away from its arm's radial direction.

        A hinge turns about its pin axis. A socket left facing along the radius
        gives the arm a base joint that swings it sideways around the palm, which
        opens and closes nothing. Turning the socket a quarter turn puts the pin
        across the radius, so the first joint carries the arm in and out of the
        palm centre — the motion a grasping arm actually needs.
        """
        return 90.0

    def body_twist_deg(self, index: int) -> float:
        """Twist of arm body `index` (1-based) before its station angle is added.

        The palm socket is twisted, so the whole chain above it is too: body one
        meets the socket square, and every body after alternates as usual.
        """
        return 0.0 if index % 2 else 90.0

    def joint_axis_twist_deg(self, joint_index: int) -> float:
        """Pin-axis heading of joint `joint_index` (0 is the base joint at the palm).

        Even joints run tangentially, odd joints radially, so an arm curls in and
        out and swings side to side by turns.
        """
        return 90.0 if joint_index % 2 == 0 else 0.0

    # -------------------------------------------------- the gripping surfaces

    @property
    def grip(self) -> GripSurfaceSpec:
        """The contact surfaces, which own their own printability rules."""
        return GripSurfaceSpec(
            arm=self.arm_spec,
            grip_outer_diameter_mm=self.grip_outer_diameter_mm,
            grip_pad_height_mm=self.grip_pad_height_mm,
            grip_pad_arc_deg=self.grip_pad_arc_deg,
            grip_pad_slope_deg=self.grip_pad_slope_deg,
            tip_facet_count=self.tip_facet_count,
            tip_cap_flare_mm=self.tip_cap_flare_mm,
            tip_cap_height_mm=self.tip_cap_height_mm,
            tip_cap_top_diameter_mm=self.tip_cap_top_diameter_mm,
            tip_cable_bore_diameter_mm=self.tip_cable_bore_diameter_mm,
            tip_feature_fuse_mm=self.tip_feature_fuse_mm,
        )

    @property
    def grip_pad_angles_deg(self) -> tuple[float, ...]:
        return self.grip.grip_pad_angles_deg

    @property
    def grip_pad_projection_mm(self) -> float:
        return self.grip.grip_pad_projection_mm

    @property
    def grip_envelope_radius_mm(self) -> float:
        return self.grip.grip_envelope_radius_mm

    @property
    def grip_flat_face_height_mm(self) -> float:
        return self.grip.grip_flat_face_height_mm

    @property
    def tip_feature_base_z_mm(self) -> float:
        return self.grip.tip_feature_base_z_mm

    @property
    def tip_cap_base_z_mm(self) -> float:
        return self.grip.tip_cap_base_z_mm

    @property
    def tip_cap_base_radius_mm(self) -> float:
        return self.grip.tip_cap_base_radius_mm

    @property
    def tip_cap_shoulder_z_mm(self) -> float:
        return self.grip.tip_cap_shoulder_z_mm

    @property
    def tip_cap_top_z_mm(self) -> float:
        return self.grip.tip_cap_top_z_mm

    @property
    def tip_cap_max_radius_mm(self) -> float:
        return self.grip.tip_cap_max_radius_mm

    @property
    def tip_cap_flare_slope_deg(self) -> float:
        return self.grip.tip_cap_flare_slope_deg

    @property
    def tip_cap_taper_slope_deg(self) -> float:
        return self.grip.tip_cap_taper_slope_deg

    def tip_cap_radius_at_mm(self, z_mm: float) -> float:
        return self.grip.tip_cap_radius_at_mm(z_mm)

    @property
    def tip_cable_bore_angles_deg(self) -> tuple[float, float]:
        return self.grip.tip_cable_bore_angles_deg

    @property
    def tip_cable_bore_z_mm(self) -> float:
        return self.grip.tip_cable_bore_z_mm

    # ---------------------------------------------------------------- the palm

    @property
    def minimum_station_radius_mm(self) -> float:
        """Closest the arm axes may sit before neighbouring grip surfaces touch."""
        arm = self.arm_spec
        span = max(
            self.grip_envelope_radius_mm,
            arm.body_outer_diameter_mm / 2,
            arm.connector_envelope_radius_mm,
        )
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

    # ------------------------------------------------------------ the envelope

    @property
    def arm_tip_height_mm(self) -> float:
        """Top of the tip cap above the palm's top face."""
        return self.arm_body_count * self.arm_spec.unit_pitch_mm + self.tip_cap_top_z_mm

    @property
    def upright_footprint_mm(self) -> float:
        """Bed square needed with the palm flat and the arms standing up."""
        arms = 2 * (self.arm_station_radius_mm + self.grip_envelope_radius_mm)
        return max(arms, self.palm_across_corners_mm)

    @property
    def upright_height_mm(self) -> float:
        return self.palm_thickness_mm + self.arm_tip_height_mm

    @property
    def splayed_footprint_mm(self) -> float:
        """Kept for the comparison that rejected the flat pose; not a build target."""
        return 2 * (self.arm_station_radius_mm + self.arm_spec.assembled_height_mm)

    @property
    def total_tendon_count(self) -> int:
        return self.arm_count * len(self.arm_spec.tendon_positions_mm)

    @property
    def printable_part_types(self) -> tuple[str, str, str]:
        return ("octopus_palm", "biaxial_arm_body", "octopus_tip")
