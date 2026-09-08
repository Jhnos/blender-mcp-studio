"""Where the oracle should look, derived from where the bores actually are.

Every probe point in the committed V3 contracts was typed from the spec by
hand: `±6.6`, `±15/45`, `-71`, `-43.1`, `27.0`, `[1.0, 0.625]`. Each is one
line of arithmetic on the spec, done here once, so a spec change moves the
probes with it and a contract can no longer describe a hand that was not built.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.domain.palm_v3 import AnthropomorphicPalmSpec
from src.core.planning.naming import NamingPolicy
from src.core.planning.station_plan import Station

#: The per-joint sweep samples every this many degrees out to the link's limit.
#: Coarse on purpose: it asks whether the arc is clear, not by what path.
SWEEP_STEP_DEG = 10.0
#: Steps of the coordinated closure. Enough that two joints half-flexed are
#: visited between the postures the per-joint sweep already covers.
CLOSURE_STEPS = 8

Point = tuple[float, float]


@dataclass(frozen=True, slots=True)
class ChannelProbePlan:
    object_name: str
    axis: str
    open_points_mm: tuple[Point, ...]
    solid_points_mm: tuple[Point, ...]


@dataclass(frozen=True, slots=True)
class ProbePlan:
    #: Bores through a phalanx, (x, y) in its own frame: the tendon and its mirror.
    bore_probe_points_mm: tuple[Point, ...]
    #: This hinge's pin runs through the axis, so the axis is solid by design.
    center_channel_open: bool
    palm_tendon_probe: ChannelProbePlan
    air_port_probe: ChannelProbePlan
    sweep_angles_deg: tuple[float, ...]
    pivot_offset_mm: float
    hinge_axis: str
    mating_twist_deg: float
    travel_shares: tuple[float, ...]
    full_travel_deg: float
    closure_steps: int


def probe_plan(
    palm: AnthropomorphicPalmSpec, naming: NamingPolicy, stations: tuple[Station, ...]
) -> ProbePlan:
    finger = palm.finger
    link = finger.link
    tendon_y = finger.tendon_bore_offset_mm

    # One ray down every station's tendon channel; controls midway between row
    # stations, where the plate has no reason to be anything but solid.
    open_z = tuple((station.origin_mm[0], tendon_y) for station in stations)
    row_x = palm.row_finger_x_mm
    solid_z = tuple(
        ((left + right) / 2, tendon_y) for left, right in zip(row_x, row_x[1:], strict=False)
    )

    # The port goes through along Y; the controls are plate heights above it —
    # half a body below the knuckle line, and the thumb root's own height.
    port_x, port_z = palm.air_port_center_mm
    port_controls = ((port_x, -link.body_length_mm / 2), (port_x, -palm.thumb_base_drop_mm))

    limit = link.maximum_articulation_deg
    half_steps = round(limit / SWEEP_STEP_DEG)
    sweep = tuple(-limit + index * SWEEP_STEP_DEG for index in range(2 * half_steps + 1))

    plan = ProbePlan(
        bore_probe_points_mm=((0.0, tendon_y), (0.0, finger.wiring_bore_offset_mm)),
        center_channel_open=False,
        palm_tendon_probe=ChannelProbePlan(naming.palm(), "Z", open_z, solid_z),
        air_port_probe=ChannelProbePlan(naming.palm(), "Y", ((port_x, port_z),), port_controls),
        sweep_angles_deg=sweep,
        pivot_offset_mm=link.joint_center_offset_mm,
        hinge_axis=finger.hinge_axis,
        mating_twist_deg=finger.joint_rotations_deg[1],
        travel_shares=finger.joint_travel_shares,
        full_travel_deg=limit,
        closure_steps=CLOSURE_STEPS,
    )
    findings = probe_soundness(palm, plan)
    if findings:
        raise ValueError("the probe plan would measure empty air: " + "; ".join(findings))
    return plan


def probe_soundness(palm: AnthropomorphicPalmSpec, plan: ProbePlan) -> list[str]:
    """Every open point inside the solid it probes, every control on plate with no bore
    under it, every finger bore between the pin and the wall. Empty means sound.

    A ray aimed past the part misses too, which is how this project once
    reported five open bores through empty air. The oracle's solid controls
    guard that at run time; this guards the plan before anything is built.
    """
    link = palm.finger.link
    findings: list[str] = []
    hole = link.tendon_hole_diameter_mm / 2
    wall = link.minimum_wall_mm

    for _, y_mm in plan.bore_probe_points_mm:
        if abs(y_mm) + hole > link.body_depth_mm / 2 - wall:
            findings.append(f"finger bore at y={y_mm} breaks the body wall")
        if abs(y_mm) - hole < link.printed_pin_bore_mm / 2 + wall:
            findings.append(f"finger bore at y={y_mm} runs into the pin's wall")

    half_width = palm.palm_width_mm / 2
    boss_centre, boss_size = palm.thenar_bridge_mm
    boss_low = boss_centre[0] - boss_size[0] / 2
    boss_high = boss_centre[0] + boss_size[0] / 2
    station_x = (*palm.row_finger_x_mm, palm.thumb_root_mm[0])
    for x_mm, _ in plan.palm_tendon_probe.open_points_mm:
        on_plate = -half_width <= x_mm <= half_width
        on_boss = boss_low <= x_mm <= boss_high
        if not (on_plate or on_boss):
            findings.append(f"palm channel probe at x={x_mm} is past the plate")
    for x_mm, _ in plan.palm_tendon_probe.solid_points_mm:
        if not -half_width <= x_mm <= half_width:
            findings.append(f"palm control at x={x_mm} is past the plate")
        if any(abs(x_mm - station) < hole + wall for station in station_x):
            findings.append(f"palm control at x={x_mm} sits over a bore")

    plate_height = palm.plate_height_mm
    port_x, port_z = palm.air_port_center_mm
    port_radius = palm.air_port_diameter_mm / 2
    clamp_z = palm.cuff_clamp_center_z_mm
    clamp_half = palm.cuff_clamp_wall_mm / 2
    for _, z_mm in plan.air_port_probe.open_points_mm:
        if not -plate_height <= z_mm <= 0.0:
            findings.append(f"air port probe at z={z_mm} is past the plate")
    for _, z_mm in plan.air_port_probe.solid_points_mm:
        if not -plate_height <= z_mm <= 0.0:
            findings.append(f"air port control at z={z_mm} is past the plate")
        if abs(z_mm - port_z) < port_radius + wall:
            findings.append(f"air port control at z={z_mm} sits over the port")
        if abs(z_mm - clamp_z) < clamp_half + wall:
            findings.append(f"air port control at z={z_mm} sits in the clamp groove")
    return findings
