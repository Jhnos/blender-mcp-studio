"""Nominal active screw and passive pivot, sharing the screen's five-phase motion."""

from dataclasses import dataclass, field
from math import isfinite, pi

from src.core.domain.lab_station_joints import ScreenFoldSpec, SerratedJointSpec


@dataclass(frozen=True, slots=True)
class ScreenClampPose:
    body_x_mm: float
    body_angle_rad: float
    active_x_mm: float
    active_angle_rad: float
    pin_float_mm: float


@dataclass(frozen=True, slots=True)
class ScreenClampSpec:
    """Rigid reference kinematics; neither thread engagement nor force qualification."""

    sequence: ScreenFoldSpec = field(
        default_factory=lambda: ScreenFoldSpec(release_mm=2.2, screw_mm=2.4)
    )
    joint: SerratedJointSpec = field(default_factory=SerratedJointSpec)
    pitch_mm: float = 0.8
    float_limit_mm: float = 0.28

    def __post_init__(self) -> None:
        if (
            not isfinite(self.pitch_mm)
            or self.pitch_mm <= 0
            or not isfinite(self.float_limit_mm)
            or self.float_limit_mm < 0
        ):
            raise ValueError("Clamp pitch and axial float must be finite with valid signs")
        for angle in (self.sequence.working_angle_deg, self.sequence.target_angle_deg):
            if abs(angle / self.joint.step_deg - round(angle / self.joint.step_deg)) > 1e-9:
                raise ValueError("Clamp endpoints must lie on indexed tooth angles")
        if self.sequence.release_mm < self.joint.tooth_height_mm + 0.3:
            raise ValueError("Clamp release must clear the selected teeth")

    def pose(self, progress: float, *, axial_float_mm: float = 0.0) -> ScreenClampPose:
        if not isfinite(axial_float_mm) or abs(axial_float_mm) > self.float_limit_mm:
            raise ValueError("Passive-pin float outside the declared nominal envelope")
        motion = self.sequence.pose(progress)
        angle = (motion["angle_deg"] - self.sequence.working_angle_deg) * pi / 180
        return ScreenClampPose(
            body_x_mm=-self.joint.assembly_gap_mm + motion["release_mm"],
            body_angle_rad=angle,
            active_x_mm=motion["release_mm"] - motion["screw_mm"],
            active_angle_rad=angle - 2 * pi * motion["screw_mm"] / self.pitch_mm,
            pin_float_mm=axial_float_mm,
        )

    def driver_expressions(self) -> dict[str, str]:
        channels = self.sequence.driver_expressions()
        angle = f"(({channels['angle_deg']})-{self.sequence.working_angle_deg!r})*pi/180"
        screw = channels["screw_mm"]
        return {
            "body_x_mm": f"{-self.joint.assembly_gap_mm!r}+({channels['release_mm']})",
            "body_angle_rad": angle,
            "active_x_mm": f"({channels['release_mm']})-({screw})",
            "active_angle_rad": f"({angle})-2*pi*({screw})/{self.pitch_mm!r}",
            "pin_float_mm": "pin_float",
        }
