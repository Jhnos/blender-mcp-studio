"""Declared single-head maintenance samples, separate from Blender execution."""

from dataclasses import dataclass
from typing import Literal

from src.core.domain.lab_station import ElectrodeArmSpec
from src.core.domain.verification import VerificationSuite
from src.verification.scenario_runner import Scenario


@dataclass(frozen=True, slots=True)
class WristPoint:
    stage: str
    angle_deg: float
    release_mm: float


_SERVICE_ANGLE = ElectrodeArmSpec().wrist_indexed_angle(0, 100, 1)
WRIST_POINTS = tuple(WristPoint("rotate", _SERVICE_ANGLE * i / 20, 2) for i in range(21)) + tuple(
    WristPoint("reseat", _SERVICE_ANGLE, 2 - i / 5) for i in range(11)
)


@dataclass(frozen=True, slots=True)
class ServiceProbe:
    head: Literal["capillary", "pH_temp"]
    operation: Literal["wrist", "clamp"]
    control: Literal["none", "working", "obstacle"] = "none"


SERVICE_CASES = {
    "electrode-wrist-service": (
        Scenario("wrist_capillary_clear", ServiceProbe("capillary", "wrist"), "clear"),
        Scenario("wrist_ph_temp_clear", ServiceProbe("pH_temp", "wrist"), "clear"),
        Scenario(
            "wrist_obstacle_rejected", ServiceProbe("pH_temp", "wrist", "obstacle"), "blocked"
        ),
    ),
    "electrode-clamp-service": (
        Scenario("clamp_capillary_clear", ServiceProbe("capillary", "clamp"), "clear"),
        Scenario("clamp_ph_temp_clear", ServiceProbe("pH_temp", "clamp"), "clear"),
        Scenario(
            "clamp_capillary_working_rejected",
            ServiceProbe("capillary", "clamp", "working"),
            "blocked",
        ),
        Scenario(
            "clamp_ph_temp_working_rejected", ServiceProbe("pH_temp", "clamp", "working"), "blocked"
        ),
        Scenario(
            "clamp_obstacle_rejected", ServiceProbe("pH_temp", "clamp", "obstacle"), "blocked"
        ),
    ),
}


def service_suites() -> tuple[VerificationSuite, ...]:
    scopes = (
        (
            "electrode-wrist-service",
            "Electrode wrist maintenance",
            "32 release/rotate/reseat samples per independent head, all nine cable segments, "
            "and a live obstacle control. No continuous sweep or load qualification.",
        ),
        (
            "electrode-clamp-service",
            "Electrode independent clamp removal",
            "286 moving samples plus 12 axial-stop checks; nine cable segments, working-pose "
            "and live obstacle controls. Conditional individual removal paths, not a complete "
            "ordered maintenance sequence or physical qualification.",
        ),
    )
    return tuple(
        VerificationSuite(
            key, title, scope, tuple((c.name, c.expected) for c in SERVICE_CASES[key])
        )
        for key, title, scope in scopes
    )
