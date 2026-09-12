"""Coarse printed indexing coupon and screen envelope; no holding-force claim."""

from dataclasses import dataclass
from math import cos, isfinite, radians, sin

from src.core.domain.lab_station import Point


@dataclass(frozen=True, slots=True)
class SerratedJointSpec:
    teeth: int = 24
    radius_mm: float = 18.0
    bore_radius_mm: float = 2.7
    tooth_inner_radius_mm: float = 6.0
    base_mm: float = 4.0
    tooth_height_mm: float = 1.2
    assembly_gap_mm: float = 0.2
    release_mm: float = 2.0

    def __post_init__(self) -> None:
        if type(self.teeth) is not int or self.teeth < 4 or self.teeth % 2:
            raise ValueError("An even positive tooth count of at least four is required")
        values = (
            self.radius_mm,
            self.bore_radius_mm,
            self.tooth_inner_radius_mm,
            self.base_mm,
            self.tooth_height_mm,
            self.assembly_gap_mm,
            self.release_mm,
        )
        if any(not isfinite(v) or v <= 0 for v in values):
            raise ValueError("Joint dimensions must be finite and positive")
        if not self.bore_radius_mm < self.tooth_inner_radius_mm < self.radius_mm:
            raise ValueError("Bore, tooth root and outer radii must be ordered")
        if self.release_mm < self.tooth_height_mm + 0.3:
            raise ValueError("Release stroke must disengage teeth with clearance")

    @property
    def step_deg(self) -> float:
        return 360 / self.teeth

    def profile(self, angle_deg: float) -> float:
        phase = (angle_deg / self.step_deg) % 1
        return self.tooth_height_mm * (1 - abs(2 * phase - 1))

    def face_gap(self, angle_deg: float, rotation_deg: float, *, released: bool = False) -> float:
        return (
            self.assembly_gap_mm
            + self.profile(angle_deg - rotation_deg)
            - self.profile(angle_deg)
            + (self.release_mm if released else 0)
        )


@dataclass(frozen=True, slots=True)
class ScreenHingeSpec:
    pivot_mm: Point = (0.0, -49.0, 128.0)
    default_step: int = 4

    def envelope(self, angle_deg: float) -> tuple[Point, ...]:
        """Actual front/back box extents including the 36 mm rear enclosure."""
        angle = radians(angle_deg)
        return tuple(
            (
                x,
                self.pivot_mm[1] + y * cos(angle) - z * sin(angle),
                self.pivot_mm[2] + y * sin(angle) + z * cos(angle),
            )
            for x in (-85.0, 85.0)
            for y in (-18.0, 110.0)
            for z in (-36.0, 18.0)
        )
