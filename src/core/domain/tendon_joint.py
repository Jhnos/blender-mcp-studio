"""Immutable contract for one repeated tendon-driven vertebra part."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TendonVertebraSpec:
    """Millimetre dimensions for identical two-axis ball-socket vertebrae."""

    interface_count: int = 2
    body_diameter_mm: float = 42.0
    body_thickness_mm: float = 8.0
    joint_center_offset_mm: float = 10.0
    tendon_hole_diameter_mm: float = 2.8
    tendon_radius_mm: float = math.sqrt(200.0)
    ball_diameter_mm: float = 10.0
    ball_neck_diameter_mm: float = 6.0
    radial_clearance_mm: float = 0.3
    minimum_wall_mm: float = 2.4
    socket_slot_mm: float = 1.4
    socket_retention_mm: float = 2.0
    maximum_articulation_deg: float = 25.0

    def __post_init__(self) -> None:
        if not 1 <= self.interface_count <= 6:
            raise ValueError("interface_count must be between 1 and 6")
        if not 0.2 <= self.radial_clearance_mm <= 0.6:
            raise ValueError("radial clearance must be between 0.2 and 0.6 mm for FDM")
        if self.minimum_wall_mm < 0.8:
            raise ValueError("minimum wall must be at least 0.8 mm")
        if self.ball_diameter_mm < 8.0:
            raise ValueError("ball diameter must be at least 8.0 mm")
        if self.ball_neck_diameter_mm > self.ball_diameter_mm - 2.0:
            raise ValueError("ball neck must leave articulation clearance")
        if self.tendon_hole_diameter_mm < 1.5:
            raise ValueError("tendon hole diameter must be at least 1.5 mm")
        if self.body_thickness_mm < 2.0 * self.minimum_wall_mm:
            raise ValueError("body thickness must preserve two minimum walls")
        if self.edge_wall_mm < self.minimum_wall_mm:
            raise ValueError("tendon holes leave insufficient edge wall")
        if self.socket_slot_mm < 0.8:
            raise ValueError("socket slot must be printable and flexible")
        if not 1.0 <= self.socket_retention_mm <= self.ball_radius_mm * 0.6:
            raise ValueError("socket retention leaves an invalid snap opening")
        if not 5.0 <= self.maximum_articulation_deg <= 35.0:
            raise ValueError("maximum articulation must stay between 5 and 35 degrees")

    @property
    def assembly_unit_count(self) -> int:
        return self.interface_count + 1

    @property
    def degrees_of_freedom(self) -> int:
        return self.interface_count * 2

    @property
    def axis_names(self) -> tuple[str, ...]:
        return tuple(
            f"J{interface}_{axis}"
            for interface in range(1, self.interface_count + 1)
            for axis in ("X", "Y")
        )

    @property
    def printable_part_types(self) -> tuple[str, ...]:
        return ("vertebra",)

    @property
    def tendon_positions_mm(self) -> tuple[tuple[float, float], ...]:
        offset = round(self.tendon_radius_mm / math.sqrt(2.0), 3)
        return (
            (-offset, -offset),
            (-offset, offset),
            (offset, -offset),
            (offset, offset),
        )

    @property
    def ball_radius_mm(self) -> float:
        return self.ball_diameter_mm / 2.0

    @property
    def socket_diameter_mm(self) -> float:
        return self.ball_diameter_mm + 2.0 * self.radial_clearance_mm

    @property
    def socket_outer_diameter_mm(self) -> float:
        return self.socket_diameter_mm + 2.0 * self.minimum_wall_mm

    @property
    def edge_wall_mm(self) -> float:
        return (
            self.body_diameter_mm / 2.0 - self.tendon_radius_mm - self.tendon_hole_diameter_mm / 2.0
        )

    @property
    def unit_pitch_mm(self) -> float:
        return 2.0 * self.joint_center_offset_mm

    @property
    def assembled_height_mm(self) -> float:
        return (self.assembly_unit_count - 1) * self.unit_pitch_mm + (
            2.0 * self.joint_center_offset_mm + self.socket_outer_diameter_mm / 2.0
        )
