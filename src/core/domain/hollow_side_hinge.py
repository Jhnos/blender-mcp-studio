"""Immutable contract for a short, hollow, dual-side hinge chain."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HollowSideHingeSpec:
    """Millimetre dimensions for one repeatable annular hinge module."""

    joint_count: int = 8
    body_length_mm: float = 10.4
    body_outer_diameter_mm: float = 28.0
    joint_center_offset_mm: float = 10.0
    center_channel_diameter_mm: float = 10.0
    tendon_hole_diameter_mm: float = 2.4
    tendon_radius_mm: float = 9.5
    pin_diameter_mm: float = 4.0
    printed_radial_clearance_mm: float = 0.25
    bearing_seat_diameter_mm: float = 8.1
    bearing_width_mm: float = 3.0
    lug_outer_diameter_mm: float = 19.8
    side_male_center_mm: float = 16.0
    side_female_center_mm: float = 19.5
    male_lug_thickness_mm: float = 3.0
    female_lug_thickness_mm: float = 3.2
    lug_profile_clearance_mm: float = 0.5
    bridge_thickness_mm: float = 2.4
    bridge_width_mm: float = 4.0
    motion_envelope_margin_mm: float = 0.05
    minimum_wall_mm: float = 2.4
    minimum_running_clearance_mm: float = 0.3
    maximum_articulation_deg: float = 34.0

    def __post_init__(self) -> None:
        if not 4 <= self.joint_count <= 12 or self.joint_count % 2:
            raise ValueError("joint_count must be even and between 4 and 12")
        if self.body_length_mm > 18.0 or self.unit_pitch_mm > 24.0:
            raise ValueError("module must remain short enough for dense articulation")
        if self.body_length_mm < 2.0 * self.minimum_wall_mm:
            raise ValueError("body length leaves insufficient wall")
        if not 8.0 <= self.center_channel_diameter_mm <= 12.0:
            raise ValueError("center channel must stay between 8 and 12 mm")
        if self.minimum_annular_wall_mm < self.minimum_wall_mm:
            raise ValueError("center channel leaves insufficient annular wall")
        if self.center_hardware_clearance_mm < self.minimum_running_clearance_mm:
            raise ValueError("side hardware intrudes into the center channel")
        if self.side_hinge_running_clearance_mm < self.minimum_running_clearance_mm:
            raise ValueError("side hinge lugs need printable running clearance")
        if self.side_lug_body_clearance_mm < self.minimum_running_clearance_mm:
            raise ValueError("side hinge lugs must sit outside the annular body")
        if self.bridge_thickness_mm < self.minimum_wall_mm:
            raise ValueError("side lug bridge is thinner than the printable wall")
        if self.bridge_to_opposite_lug_clearance_mm < self.minimum_running_clearance_mm:
            raise ValueError("side lug bridge collides with the mating lug")
        if self.bridge_corner_radial_margin_mm < self.minimum_running_clearance_mm:
            raise ValueError("side lug bridge falls outside the lug profile")
        if self.bearing_radial_wall_mm < self.minimum_wall_mm:
            raise ValueError("bearing seat leaves insufficient lug wall")
        if self.female_lug_thickness_mm < self.bearing_width_mm:
            raise ValueError("female lug must contain the bearing width")
        if self.minimum_tendon_inner_wall_mm < self.minimum_wall_mm:
            raise ValueError("tendon holes are too close to the center channel")
        if self.minimum_tendon_outer_wall_mm < self.minimum_wall_mm:
            raise ValueError("tendon holes are too close to the outer wall")
        if self.cumulative_articulation_x_deg < 120.0:
            raise ValueError("articulation must reach at least 120 degrees per plane")
        if self.geometric_face_clearance_deg < self.maximum_articulation_deg:
            raise ValueError("articulation exceeds the flat-face clearance envelope")
        required_joint_gap = self.bearing_seat_diameter_mm + 2.0 * self.minimum_running_clearance_mm
        if self.joint_gap_mm < required_joint_gap:
            raise ValueError("joint gap cannot clear the side bearing envelope")

    @property
    def assembly_unit_count(self) -> int:
        return self.joint_count + 1

    @property
    def degrees_of_freedom(self) -> int:
        return self.joint_count

    @property
    def printable_part_types(self) -> tuple[str, ...]:
        return ("hollow_side_hinge_module",)

    @property
    def pins_per_joint(self) -> int:
        return 2

    @property
    def bearings_per_joint(self) -> int:
        return 2

    @property
    def common_hardware(self) -> tuple[str, str]:
        return ("M4_side_pin", "MR84_4x8x3_bearing")

    @property
    def printed_pin_bore_mm(self) -> float:
        return self.pin_diameter_mm + 2.0 * self.printed_radial_clearance_mm

    @property
    def center_channel_is_open(self) -> bool:
        return self.center_hardware_clearance_mm >= self.minimum_running_clearance_mm

    @property
    def minimum_annular_wall_mm(self) -> float:
        return (self.body_outer_diameter_mm - self.center_channel_diameter_mm) / 2.0

    @property
    def center_hardware_clearance_mm(self) -> float:
        hardware_inner_edge = self.side_male_center_mm - self.male_lug_thickness_mm / 2.0
        return hardware_inner_edge - self.center_channel_diameter_mm / 2.0

    @property
    def side_hinge_running_clearance_mm(self) -> float:
        male_outer_edge = self.side_male_center_mm + self.male_lug_thickness_mm / 2.0
        female_inner_edge = self.side_female_center_mm - self.female_lug_thickness_mm / 2.0
        return female_inner_edge - male_outer_edge

    @property
    def side_hardware_outer_radius_mm(self) -> float:
        return self.side_female_center_mm + self.female_lug_thickness_mm / 2.0

    @property
    def side_lug_body_clearance_mm(self) -> float:
        male_inner_edge = self.side_male_center_mm - self.male_lug_thickness_mm / 2.0
        return male_inner_edge - self.body_outer_diameter_mm / 2.0

    @property
    def bridge_inner_face_from_joint_mm(self) -> float:
        angle = math.radians(self.maximum_articulation_deg)
        opposite_lug_cap = self.joint_gap_mm / 2.0 - self.lug_profile_clearance_mm
        swept_width = self.bridge_width_mm / 2.0 * math.sin(angle)
        return (
            opposite_lug_cap
            + self.minimum_running_clearance_mm
            + self.motion_envelope_margin_mm
            + swept_width
        ) / math.cos(angle)

    @property
    def bridge_center_from_joint_mm(self) -> float:
        return self.bridge_inner_face_from_joint_mm + self.bridge_thickness_mm / 2.0

    @property
    def bridge_to_opposite_lug_clearance_mm(self) -> float:
        angle = math.radians(self.maximum_articulation_deg)
        opposite_lug_cap = self.joint_gap_mm / 2.0 - self.lug_profile_clearance_mm
        swept_inner_face = self.bridge_inner_face_from_joint_mm * math.cos(
            angle
        ) - self.bridge_width_mm / 2.0 * math.sin(angle)
        return swept_inner_face - opposite_lug_cap

    @property
    def bridge_corner_radial_margin_mm(self) -> float:
        outer_face = self.bridge_inner_face_from_joint_mm + self.bridge_thickness_mm
        corner_radius = math.hypot(self.bridge_width_mm / 2.0, outer_face)
        return self.lug_outer_diameter_mm / 2.0 - corner_radius

    @property
    def bearing_radial_wall_mm(self) -> float:
        return (self.lug_outer_diameter_mm - self.bearing_seat_diameter_mm) / 2.0

    @property
    def tendon_positions_mm(self) -> tuple[tuple[float, float], ...]:
        diagonal = self.tendon_radius_mm / math.sqrt(2.0)
        return (
            (-diagonal, -diagonal),
            (-diagonal, diagonal),
            (diagonal, -diagonal),
            (diagonal, diagonal),
        )

    @property
    def minimum_tendon_inner_wall_mm(self) -> float:
        return (
            self.tendon_radius_mm
            - self.tendon_hole_diameter_mm / 2.0
            - self.center_channel_diameter_mm / 2.0
        )

    @property
    def minimum_tendon_outer_wall_mm(self) -> float:
        return (
            self.body_outer_diameter_mm / 2.0
            - self.tendon_radius_mm
            - self.tendon_hole_diameter_mm / 2.0
        )

    @property
    def unit_pitch_mm(self) -> float:
        return 2.0 * self.joint_center_offset_mm

    @property
    def assembled_height_mm(self) -> float:
        clipped_lug_cap = self.joint_gap_mm / 2.0 - self.lug_profile_clearance_mm
        return (self.assembly_unit_count - 1) * self.unit_pitch_mm + 2.0 * (
            self.joint_center_offset_mm + clipped_lug_cap
        )

    @property
    def assembly_rotations_deg(self) -> tuple[float, ...]:
        return tuple(90.0 if index % 2 else 0.0 for index in range(self.assembly_unit_count))

    @property
    def axis_names(self) -> tuple[str, ...]:
        return tuple(
            f"J{joint}_{'X' if joint % 2 else 'Y'}" for joint in range(1, self.joint_count + 1)
        )

    @property
    def cumulative_articulation_x_deg(self) -> float:
        return ((self.joint_count + 1) // 2) * self.maximum_articulation_deg

    @property
    def cumulative_articulation_y_deg(self) -> float:
        return (self.joint_count // 2) * self.maximum_articulation_deg

    @property
    def geometric_face_clearance_deg(self) -> float:
        outer_radius = self.body_outer_diameter_mm / 2.0
        clearance_ratio = min(1.0, self.joint_gap_mm / outer_radius)
        return math.degrees(math.asin(clearance_ratio))

    @property
    def joint_gap_mm(self) -> float:
        return self.unit_pitch_mm - self.body_length_mm
