"""Millimetre contract for the V5 in-disc, gusseted, split-pin prototype."""

from __future__ import annotations

import math
from dataclasses import dataclass, fields


@dataclass(frozen=True, slots=True)
class InsetHingeSpec:
    """No material-strength claim: dimensions describe a physical fit coupon."""

    joint_count: int = 8
    body_outer_diameter_mm: float = 34.0
    body_length_mm: float = 4.0
    joint_center_offset_mm: float = 10.0
    center_channel_diameter_mm: float = 10.0
    tendon_radius_mm: float = 13.0
    tendon_hole_diameter_mm: float = 2.4
    side_male_center_mm: float = 8.0
    side_female_center_mm: float = 11.6
    lug_thickness_mm: float = 3.0
    lug_outer_diameter_mm: float = 9.6
    pin_diameter_mm: float = 4.0
    printed_radial_clearance_mm: float = 0.25
    pin_head_diameter_mm: float = 6.0
    pin_head_height_mm: float = 1.6
    pin_shank_length_mm: float = 7.6
    pin_tip_length_mm: float = 0.8
    pin_head_gap_mm: float = 0.3
    maximum_articulation_deg: float = 34.0

    def __post_init__(self) -> None:
        if any(
            isinstance(getattr(self, field.name), bool)
            or not math.isfinite(getattr(self, field.name))
            or getattr(self, field.name) <= 0
            for field in fields(self)
        ):
            raise ValueError("dimensions must be finite and positive")
        if (
            type(self.joint_count) is not int
            or self.joint_count % 2
            or not 4 <= self.joint_count <= 12
        ):
            raise ValueError("joint count must be an even integer between 4 and 12")
        if self.connector_envelope_radius_mm >= self.body_outer_diameter_mm / 2:
            raise ValueError("connectors and pin heads must fit inside the disc")
        lower, shoulder, neck = self.root_profile_mm
        if not lower[0] < self.body_length_mm / 2 < shoulder[0]:
            raise ValueError("disc must intersect the sloping foot, not the vertical shoulder")
        if self.side_hinge_running_clearance_mm < 0.4:
            raise ValueError("mating lugs need axial running clearance")
        if self.pin_tip_inner_radius_mm < self.center_channel_diameter_mm / 2 + 0.3:
            raise ValueError("split pin intrudes into the sensor channel")
        male_inner = self.side_male_center_mm - self.lug_thickness_mm / 2
        if self.pin_tip_inner_radius_mm + self.pin_tip_length_mm > male_inner + 0.2:
            raise ValueError("pin does not span both lugs")
        if male_inner < self.center_channel_diameter_mm / 2 + 1.0:
            raise ValueError("male ear intrudes into the sensor channel")
        if (self.lug_outer_diameter_mm - self.printed_pin_bore_mm) / 2 < 2.0:
            raise ValueError("pin bore leaves insufficient ear wall")
        if (
            math.hypot(neck[2], self.joint_center_offset_mm - neck[0])
            >= self.lug_outer_diameter_mm / 2
        ):
            raise ValueError("gusset must overlap the circular ear")
        if (
            min(
                self.tendon_radius_mm
                - self.tendon_hole_diameter_mm / 2
                - self.center_channel_diameter_mm / 2,
                self.body_outer_diameter_mm / 2
                - self.tendon_radius_mm
                - self.tendon_hole_diameter_mm / 2,
            )
            < 2.0
        ):
            raise ValueError("tendon holes leave insufficient disc wall")
        if self.pin_tip_length_mm >= self.pin_shank_length_mm or self.maximum_articulation_deg > 34:
            raise ValueError("unsupported pin or articulation envelope")

    @property
    def root_profile_mm(self) -> tuple[tuple[float, float, float], ...]:
        """(Height above disc centre, axial half-width, tangential half-width)."""
        return ((1.8, 3.0, 8.5), (3.0, 1.5, 7.0), (6.5, 1.5, 2.0))

    @property
    def root_transition_angle_deg(self) -> float:
        lower, upper = self.root_profile_mm[:2]
        return math.degrees(math.atan2(upper[0] - lower[0], lower[1] - upper[1]))

    @property
    def gusset_slope_deg(self) -> float:
        lower, upper = self.root_profile_mm[1:]
        return math.degrees(math.atan2(upper[0] - lower[0], lower[2] - upper[2]))

    @property
    def connector_envelope_radius_mm(self) -> float:
        root = max(
            math.hypot(self.side_female_center_mm + axial, tangent)
            for _, axial, tangent in self.root_profile_mm
        )
        lug = math.hypot(
            self.side_female_center_mm + self.lug_thickness_mm / 2,
            self.lug_outer_diameter_mm / 2,
        )
        head = math.hypot(
            self.pin_under_head_radius_mm + self.pin_head_height_mm,
            self.pin_head_diameter_mm / 2,
        )
        return max(root, lug, head)

    @property
    def side_hinge_running_clearance_mm(self) -> float:
        return self.side_female_center_mm - self.side_male_center_mm - self.lug_thickness_mm

    @property
    def printed_pin_bore_mm(self) -> float:
        return self.pin_diameter_mm + 2 * self.printed_radial_clearance_mm

    @property
    def pin_under_head_radius_mm(self) -> float:
        return self.side_female_center_mm + self.lug_thickness_mm / 2 + self.pin_head_gap_mm

    @property
    def pin_tip_inner_radius_mm(self) -> float:
        return self.pin_under_head_radius_mm - self.pin_shank_length_mm

    @property
    def pin_length_mm(self) -> float:
        return self.pin_head_height_mm + self.pin_shank_length_mm

    @property
    def required_pin_count(self) -> int:
        return 2 * self.joint_count

    @property
    def printable_part_types(self) -> tuple[str, str]:
        return ("inset_hinge_module", "headed_side_pin")

    @property
    def unit_pitch_mm(self) -> float:
        return 2 * self.joint_center_offset_mm

    @property
    def assembly_unit_count(self) -> int:
        return self.joint_count + 1

    @property
    def assembly_rotations_deg(self) -> tuple[float, ...]:
        return tuple(90.0 if i % 2 else 0.0 for i in range(self.assembly_unit_count))

    @property
    def axis_names(self) -> tuple[str, ...]:
        return tuple(f"J{i}_{'X' if i % 2 else 'Y'}" for i in range(1, self.joint_count + 1))

    @property
    def tendon_positions_mm(self) -> tuple[tuple[float, float], ...]:
        diagonal = self.tendon_radius_mm / math.sqrt(2)
        return tuple((x * diagonal, y * diagonal) for x in (-1, 1) for y in (-1, 1))

    @property
    def assembled_height_mm(self) -> float:
        return self.joint_count * self.unit_pitch_mm + 2 * (
            self.joint_center_offset_mm + self.lug_outer_diameter_mm / 2
        )
