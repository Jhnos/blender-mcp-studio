"""Packaging and kinematic assumptions; these are not load-rated mechanical parts."""

from dataclasses import dataclass
from math import dist, isfinite, sqrt

Point = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class LabStationSpec:
    link_mm: float = 130.0
    wall_mm: float = 3.0
    lift_travel_mm: float = 100.0
    lcd_glass_mm: tuple[float, float] = (127.7, 87.45)
    lcd_window_mm: tuple[float, float] = (110.0, 67.0)
    base_panel_mm: Point = (230.0, 150.0, 6.0)
    vessel_center_mm: Point = (0.0, -145.0, 6.0)

    def __post_init__(self) -> None:
        if not isfinite(self.lift_travel_mm) or not 81.5 <= self.lift_travel_mm <= 100:
            raise ValueError(
                "Extraction stroke must clear the rim and stay within the 100 mm guide"
            )
        dimensions = (
            self.link_mm,
            self.wall_mm,
            *self.lcd_glass_mm,
            *self.lcd_window_mm,
            *self.base_panel_mm,
            *self.vessel_center_mm,
        )
        if not all(isfinite(value) for value in dimensions):
            raise ValueError("Dimensions must be finite")
        if min(dimensions[:9]) <= 0:
            raise ValueError("Mechanical dimensions must be positive")
        if self.wall_mm >= 10:
            raise ValueError("Wall exceeds this packaging prototype's allowance")
        self.arm_points(1)

    @property
    def lcd_pocket_mm(self) -> tuple[float, float]:
        return self.lcd_glass_mm[0] + 0.8, self.lcd_glass_mm[1] + 0.8

    def probe_origin(self, side: int) -> Point:
        if side not in (-1, 1):
            raise ValueError("Arm side must be -1 or 1")
        return (side * 18.0, -151.0 if side == -1 else -135.0, 195.0 if side == -1 else 165.0)

    def arm_points(self, side: int) -> tuple[Point, Point, Point]:
        """Equal-link elbow-up IK in the root/wrist vertical plane, in millimetres."""
        if side not in (-1, 1):
            raise ValueError("Arm side must be -1 or 1")
        root = (side * 98.0, 45.0, 108.0)
        probe = self.probe_origin(side)
        wrist = (probe[0], probe[1] + 40, probe[2])
        chord = dist(root, wrist)
        if chord >= 2 * self.link_mm:
            raise ValueError("Arm cannot reach the vessel with bent joints")
        horizontal = dist(root[:2], wrist[:2])
        height = sqrt(self.link_mm**2 - (chord / 2) ** 2)
        dx, dy, dz = (wrist[i] - root[i] for i in range(3))
        normal = (
            -dx * dz / (horizontal * chord),
            -dy * dz / (horizontal * chord),
            horizontal / chord,
        )
        lateral = (side * -dy / horizontal, side * dx / horizontal, 0.0)
        normal = (
            0.7 * normal[0] + sqrt(0.51) * lateral[0],
            0.7 * normal[1] + sqrt(0.51) * lateral[1],
            0.7 * normal[2],
        )
        elbow: Point = tuple(  # type: ignore[assignment]
            (root[i] + wrist[i]) / 2 + height * normal[i] for i in range(3)
        )
        return root, elbow, wrist
