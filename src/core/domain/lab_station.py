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
        wrist = (probe[0], probe[1] + 60, probe[2])
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

    def shoulder_neck(self, side: int) -> Point:
        """Leave the moving tooth half before the upper link returns toward the elbow."""
        root, _, _ = self.arm_points(side)
        target = self.elbow_necks(side)[0]
        dy, dz = target[1] - root[1], target[2] - root[2]
        length = sqrt(dy * dy + dz * dz)
        return root[0] + 14, root[1] + 30 * dy / length, root[2] + 30 * dz / length

    def elbow_necks(self, side: int) -> tuple[Point, Point]:
        """Keep both links outside the tooth faces until beyond the plate radius."""
        root, elbow, wrist = self.arm_points(side)
        result = []
        for target, offset in ((root, -14), ((wrist[0], wrist[1], wrist[2] + 26), 14)):
            dy, dz = target[1] - elbow[1], target[2] - elbow[2]
            length = sqrt(dy * dy + dz * dz)
            result.append(
                (elbow[0] + offset, elbow[1] + 30 * dy / length, elbow[2] + 30 * dz / length)
            )
        return result[0], result[1]


@dataclass(frozen=True, slots=True)
class ProbeClampSpec:
    """Replaceable soft liners; geometry is not a glass pressure qualification."""

    split_gap_mm: float = 0.8
    jaw_depth_mm: float = 46.0
    bolt_y_mm: tuple[float, float] = (-18.0, 18.0)

    def __post_init__(self) -> None:
        values = (self.split_gap_mm, self.jaw_depth_mm, *self.bolt_y_mm)
        if (
            not all(isfinite(v) for v in values)
            or not 0 < self.split_gap_mm <= 1.2
            or self.jaw_depth_mm / 2 - max(abs(y) for y in self.bolt_y_mm) < 4.8
        ):
            raise ValueError("Invalid jaw gap or fastener edge wall")

    def bores(self, dual: bool) -> tuple[tuple[float, float], ...]:
        return ((-6.0, 7.2), (8.0, 4.2)) if dual else ((0.0, 4.2),)

    def liner_outer_radius(self, bore: float) -> float:
        return bore - 0.1

    def liner_inner_radius(self, bore: float) -> float:
        return bore - 1.1

    def liner_flange_radius(self, bore: float) -> float:
        return bore + 0.9


@dataclass(frozen=True, slots=True)
class RotaryLiftSpec:
    """Ideal parallelogram path, independent of the Blender implementation."""

    length_mm: float = 130.0
    stroke_mm: float = 100.0
    spacing_mm: float = 40.0

    def __post_init__(self) -> None:
        values = (self.length_mm, self.stroke_mm, self.spacing_mm)
        if not all(isfinite(v) and v > 0 for v in values) or self.stroke_mm >= 2 * self.length_mm:
            raise ValueError("Rotary lift dimensions must be positive and avoid the toggle")

    def joints(self, lift_mm: float) -> tuple[Point, Point, Point, Point]:
        if not isfinite(lift_mm) or not 0 <= lift_mm <= self.stroke_mm:
            raise ValueError("Lift lies outside the mechanism stroke")
        half = self.stroke_mm / 2
        reach = sqrt(self.length_mm**2 - half**2)
        excursion = sqrt(self.length_mm**2 - (lift_mm - half) ** 2) - reach
        return (
            (0, reach, half),
            (0, reach, half + self.spacing_mm),
            (0, -excursion, lift_mm),
            (0, -excursion, lift_mm + self.spacing_mm),
        )


@dataclass(frozen=True, slots=True)
class SimpleArmSpec:
    """Two-link manual arm; inverse kinematics describes a coordinated hand motion."""

    link_mm: float = 150.0
    reach_mm: float = sqrt(80**2 + 190**2)
    working_rise_mm: float = 72.0

    def planar_joints(self, lift_mm: float = 0) -> tuple[tuple[float, float], ...]:
        forward, rise = self.reach_mm, self.working_rise_mm + lift_mm
        chord = sqrt(forward**2 + rise**2)
        if (
            not all(isfinite(v) for v in (forward, rise, self.link_mm))
            or not 0 < chord < 2 * self.link_mm
        ):
            raise ValueError("Pose outside two-link reach")
        height = sqrt(self.link_mm**2 - chord**2 / 4)
        elbow = (forward / 2 - rise / chord * height, rise / 2 + forward / chord * height)
        return ((0.0, 0.0), elbow, (forward, rise))
