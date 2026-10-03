"""Declared single-head maintenance samples, separate from Blender execution."""

import math
from dataclasses import dataclass, replace
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
    operation: Literal["wrist", "clamp", "transfer", "cycle"]
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


for _probe in (
    ServiceProbe("capillary", "transfer"),
    ServiceProbe("pH_temp", "transfer"),
    ServiceProbe("capillary", "cycle"),
    ServiceProbe("pH_temp", "cycle"),
):
    _head, _operation = _probe.head, _probe.operation
    _name = _operation + "_" + _head
    SERVICE_CASES["electrode-" + _operation + "-" + _head] = (
        Scenario(_name + "_clear", _probe, "clear"),
        Scenario(
            _name + "_obstacle_rejected", ServiceProbe(_head, _operation, "obstacle"), "blocked"
        ),
    )


def service_suites() -> tuple[VerificationSuite, ...]:
    scopes: tuple[tuple[str, str, str], ...] = (
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
    scopes += tuple(
        (
            "electrode-transfer-" + head,
            "Electrode seated transfer: " + head,
            "188 working-seat to service-seat samples for one head while its neighbour remains seated; "
            "all nine cable segments and an independent midpoint obstruction control. "
            "No complete disassembly, continuous sweep or physical load qualification.",
        )
        for head in ("capillary", "pH_temp")
    )
    scopes += tuple(
        (
            "electrode-cycle-" + head,
            "Electrode ordered clamp cycle: " + head,
            "Ordered extraction and reverse insertion from a seated service pose; all extracted "
            "parts remain collision obstacles, all nine cable segments and a live obstruction control. "
            "208 capillary or 260 pH/temperature samples; no thread, tooling, continuous sweep or load qualification.",
        )
        for head in ("capillary", "pH_temp")
    )
    return tuple(
        VerificationSuite(
            key, title, scope, tuple((c.name, c.expected) for c in SERVICE_CASES[key])
        )
        for key, title, scope in scopes
    )


@dataclass(frozen=True, slots=True)
class ServiceState:
    """Absolute pose; joint triples use shoulder, elbow, wrist order."""

    forward_mm: float = 0
    lift_mm: float = 0
    angle_deg: float = 0
    release_mm: tuple[float, float, float] = (0, 0, 0)
    closure: tuple[float, float, float] = (0, 0, 0)

    def __post_init__(self) -> None:
        if any(
            not isinstance(values, tuple)  # narrow-ok: typed dataclass invariant
            or len(values) != 3
            for values in (self.release_mm, self.closure)
        ):
            raise ValueError("Service joint values must be immutable triples")
        values = (self.forward_mm, self.lift_mm, self.angle_deg, *self.release_mm, *self.closure)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Service state must contain finite values")
        if any(not 0 <= value <= 2 for value in self.release_mm):
            raise ValueError("Joint release must lie within 0–2 mm")
        if any(not 0 <= value <= 1 for value in self.closure):
            raise ValueError("Joint closure fraction must lie within 0–1")
        if any(
            release and closure
            for release, closure in zip(self.release_mm, self.closure, strict=True)
        ):
            raise ValueError("A released joint cannot also be tightened")


@dataclass(frozen=True, slots=True)
class ServiceStep:
    stage: str
    state: ServiceState


def service_transfer_steps() -> tuple[ServiceStep, ...]:
    """Sample working-seat to service-seat, retaining identical stage boundaries."""
    spec = ElectrodeArmSpec()
    forward, lift = spec.indexed_target(3, shoulder_step=0)
    state = ServiceState(closure=(1, 1, 1))
    steps: list[ServiceStep] = []

    def append(stage: str, target: ServiceState, intervals: int) -> None:
        nonlocal state

        def interpolate(a: float, b: float, index: int) -> float:
            return a + (b - a) * index / intervals

        for index in range(intervals + 1):
            sample = (
                state
                if index == 0
                else target
                if index == intervals
                else ServiceState(
                    interpolate(state.forward_mm, target.forward_mm, index),
                    interpolate(state.lift_mm, target.lift_mm, index),
                    interpolate(state.angle_deg, target.angle_deg, index),
                    (
                        interpolate(state.release_mm[0], target.release_mm[0], index),
                        interpolate(state.release_mm[1], target.release_mm[1], index),
                        interpolate(state.release_mm[2], target.release_mm[2], index),
                    ),
                    (
                        interpolate(state.closure[0], target.closure[0], index),
                        interpolate(state.closure[1], target.closure[1], index),
                        interpolate(state.closure[2], target.closure[2], index),
                    ),
                )
            )
            steps.append(ServiceStep(stage, sample))
        state = target

    def joint_stage(stage: str, field: str, joint: int, value: float, intervals: int) -> None:
        values = list(state.release_mm if field == "release_mm" else state.closure)
        values[joint] = value
        triple = (values[0], values[1], values[2])
        target = (
            replace(state, release_mm=triple)
            if field == "release_mm"
            else replace(state, closure=triple)
        )
        append(stage, target, intervals)

    names = ("shoulder", "elbow", "tip")
    for joint in (2, 1, 0):
        joint_stage("unseat-" + names[joint], "closure", joint, 0, 14)
    for joint in (2, 1, 0):
        joint_stage("release-" + names[joint], "release_mm", joint, 2, 10)
    append("transfer", replace(state, forward_mm=forward, lift_mm=lift), 10)
    append("rotate", replace(state, angle_deg=spec.wrist_indexed_angle(forward, lift, 1)), 20)
    for joint in (2, 1, 0):
        joint_stage("reseat-" + names[joint], "release_mm", joint, 0, 10)
    for joint in (0, 1, 2):
        joint_stage("seat-" + names[joint], "closure", joint, 1, 14)
    return tuple(steps)


@dataclass(frozen=True, slots=True)
class ClampStep:
    """Absolute local-Y offsets: two bolts, cap assembly, then each probe assembly."""

    direction: Literal["remove", "insert"]
    group: int
    offsets_mm: tuple[float, ...]


def clamp_cycle_steps(probe_count: int) -> tuple[ClampStep, ...]:
    """Keep extracted components in the scene and insert along the reverse path."""
    if type(probe_count) is not int or probe_count not in (1, 2):
        raise ValueError("Clamp cycle requires one or two probes")
    offsets = [0.0] * (probe_count + 3)
    removal = []
    for group in range(len(offsets)):
        sign = -1 if group < 2 else 1
        for distance in range(26):
            offsets[group] = sign * distance
            removal.append(ClampStep("remove", group, tuple(offsets)))
    return tuple(removal) + tuple(replace(step, direction="insert") for step in reversed(removal))
