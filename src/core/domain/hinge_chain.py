"""Immutable contract for a repeatable, bearing-ready hinge phalanx chain."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HingePhalanxSpec:
    """Millimetre dimensions for one orthogonal male/female hinge link."""

    joint_count: int = 4
    body_length_mm: float = 40.0
    body_width_mm: float = 24.0
    body_depth_mm: float = 22.0
    joint_center_offset_mm: float = 24.0
    tendon_hole_diameter_mm: float = 2.8
    tendon_radius_mm: float = 7.0
    pin_diameter_mm: float = 4.0
    printed_radial_clearance_mm: float = 0.25
    bearing_seat_diameter_mm: float = 8.1
    bearing_width_mm: float = 3.0
    lug_outer_diameter_mm: float = 13.0
    male_tongue_thickness_mm: float = 5.0
    fork_gap_mm: float = 5.6
    fork_lug_thickness_mm: float = 4.5
    minimum_wall_mm: float = 2.4
    maximum_articulation_deg: float = 50.0

    def __post_init__(self) -> None:
        if not 1 <= self.joint_count <= 8:
            raise ValueError("joint_count must be between 1 and 8")
        if not self.body_length_mm > self.body_width_mm > self.body_depth_mm:
            raise ValueError("phalanx body must be longer than its oval cross section")
        if self.body_slenderness_ratio < 1.6:
            raise ValueError("phalanx body must have a finger-like slenderness ratio")
        if self.joint_center_offset_mm <= self.body_length_mm / 2.0:
            raise ValueError("joint center must clear the phalanx body")
        if self.minimum_wall_mm < 0.8:
            raise ValueError("minimum wall must be at least 0.8 mm")
        if self.pin_diameter_mm < 3.0:
            raise ValueError("pin diameter must be at least 3.0 mm")
        if not 0.15 <= self.printed_radial_clearance_mm <= 0.5:
            raise ValueError("printed pin clearance must be between 0.15 and 0.5 mm")
        if self.bearing_seat_diameter_mm <= self.printed_pin_bore_mm:
            raise ValueError("bearing seat must be wider than the printed pin bore")
        if self.bearing_radial_wall_mm < self.minimum_wall_mm:
            raise ValueError("bearing seat leaves insufficient lug wall")
        if self.fork_lug_thickness_mm < self.bearing_width_mm:
            raise ValueError("fork lug must contain the bearing width")
        required_gap = self.male_tongue_thickness_mm + 2.0 * self.printed_radial_clearance_mm
        if self.fork_gap_mm < required_gap:
            raise ValueError("fork gap must clear the male tongue")
        if self.fork_total_width_mm > self.body_depth_mm:
            raise ValueError("fork width must fit the phalanx depth")
        if self.minimum_tendon_edge_wall_mm < self.minimum_wall_mm:
            raise ValueError("tendon holes leave insufficient body wall")
        if not 10.0 <= self.maximum_articulation_deg <= 65.0:
            raise ValueError("maximum articulation must stay between 10 and 65 degrees")

    @property
    def body_slenderness_ratio(self) -> float:
        return self.body_length_mm / self.body_width_mm

    @property
    def assembly_unit_count(self) -> int:
        return self.joint_count + 1

    @property
    def degrees_of_freedom(self) -> int:
        return self.joint_count

    @property
    def printable_part_types(self) -> tuple[str, ...]:
        return ("hinge_phalanx",)

    @property
    def male_hinge_axis(self) -> str:
        return "X"

    @property
    def female_hinge_axis(self) -> str:
        return "Y"

    @property
    def assembly_rotations_deg(self) -> tuple[float, ...]:
        return tuple(90.0 if index % 2 else 0.0 for index in range(self.assembly_unit_count))

    @property
    def axis_names(self) -> tuple[str, ...]:
        return tuple(
            f"J{joint}_{'X' if joint % 2 else 'Y'}" for joint in range(1, self.joint_count + 1)
        )

    @property
    def common_hardware(self) -> tuple[str, str]:
        return ("4mm_pin", "MR84_4x8x3_bearing")

    @property
    def printed_pin_bore_mm(self) -> float:
        return self.pin_diameter_mm + 2.0 * self.printed_radial_clearance_mm

    @property
    def bearing_radial_wall_mm(self) -> float:
        return (self.lug_outer_diameter_mm - self.bearing_seat_diameter_mm) / 2.0

    @property
    def fork_total_width_mm(self) -> float:
        return self.fork_gap_mm + 2.0 * self.fork_lug_thickness_mm

    @property
    def tendon_positions_mm(self) -> tuple[tuple[float, float], ...]:
        return (
            (-self.tendon_radius_mm, 0.0),
            (0.0, -self.tendon_radius_mm),
            (0.0, self.tendon_radius_mm),
            (self.tendon_radius_mm, 0.0),
        )

    @property
    def minimum_tendon_edge_wall_mm(self) -> float:
        hole_radius = self.tendon_hole_diameter_mm / 2.0
        x_wall = self.body_width_mm / 2.0 - self.tendon_radius_mm - hole_radius
        y_wall = self.body_depth_mm / 2.0 - self.tendon_radius_mm - hole_radius
        return min(x_wall, y_wall)

    @property
    def unit_pitch_mm(self) -> float:
        return 2.0 * self.joint_center_offset_mm

    @property
    def assembled_height_mm(self) -> float:
        return (self.assembly_unit_count - 1) * self.unit_pitch_mm + (
            2.0 * self.joint_center_offset_mm + self.lug_outer_diameter_mm
        )
