"""Immutable mechanical contract for a repeated tendon-driven universal joint."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TendonJointSpec:
    """Millimetre dimensions shared by the generator and its print checks."""

    cell_count: int = 2
    disc_diameter_mm: float = 42.0
    disc_thickness_mm: float = 8.0
    joint_gap_mm: float = 20.0
    tendon_hole_diameter_mm: float = 2.8
    tendon_radius_mm: float = math.sqrt(200.0)
    pin_diameter_mm: float = 5.0
    radial_clearance_mm: float = 0.3
    minimum_wall_mm: float = 2.4
    yoke_wall_mm: float = 4.0
    yoke_width_mm: float = 8.0
    maximum_articulation_deg: float = 25.0

    def __post_init__(self) -> None:
        if not 1 <= self.cell_count <= 6:
            raise ValueError("cell_count must be between 1 and 6")
        if not 0.2 <= self.radial_clearance_mm <= 0.6:
            raise ValueError("radial clearance must be between 0.2 and 0.6 mm for FDM")
        if self.minimum_wall_mm < 0.8:
            raise ValueError("minimum wall must be at least 0.8 mm")
        if self.pin_diameter_mm < 3.0:
            raise ValueError("pin diameter must be at least 3.0 mm")
        if self.tendon_hole_diameter_mm < 1.5:
            raise ValueError("tendon hole diameter must be at least 1.5 mm")
        if self.disc_thickness_mm < 2.0 * self.minimum_wall_mm:
            raise ValueError("disc thickness must preserve two minimum walls")
        if self.yoke_wall_mm < self.minimum_wall_mm:
            raise ValueError("yoke wall must not be thinner than the minimum wall")
        if self.edge_wall_mm < self.minimum_wall_mm:
            raise ValueError("tendon holes leave insufficient edge wall")
        if not 5.0 <= self.maximum_articulation_deg <= 35.0:
            raise ValueError("maximum articulation must stay between 5 and 35 degrees")

    @property
    def degrees_of_freedom(self) -> int:
        return self.cell_count * 2

    @property
    def axis_names(self) -> tuple[str, ...]:
        return tuple(
            f"J{cell}_{axis}" for cell in range(1, self.cell_count + 1) for axis in ("X", "Y")
        )

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
    def socket_diameter_mm(self) -> float:
        return self.pin_diameter_mm + 2.0 * self.radial_clearance_mm

    @property
    def edge_wall_mm(self) -> float:
        return (
            self.disc_diameter_mm / 2.0 - self.tendon_radius_mm - self.tendon_hole_diameter_mm / 2.0
        )

    @property
    def disc_pitch_mm(self) -> float:
        return self.disc_thickness_mm + self.joint_gap_mm

    @property
    def assembled_height_mm(self) -> float:
        return self.cell_count * self.disc_pitch_mm + self.disc_thickness_mm
