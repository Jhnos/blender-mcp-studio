"""Where the oracle should look, derived from where the bores actually are.

Every probe point in the committed contracts was typed by hand from the spec.
This is the same arithmetic, done once, so a change to the spec moves the
probes with it and a contract can no longer describe a hand that was not built.
"""

import pytest

from src.core.domain.palm_v3 import AnthropomorphicPalmSpec
from src.core.planning.naming import NamingPolicy
from src.core.planning.probe_plan import probe_plan
from src.core.planning.station_plan import station_plan

PALM = AnthropomorphicPalmSpec()
NAMING = NamingPolicy("HJ_", "V3")


def _flat(points: tuple[tuple[float, float], ...]) -> list[float]:
    """pytest.approx does not walk nested tuples; a flat list compares the same numbers."""
    return [value for point in points for value in point]


def test_finger_bores_are_the_tendon_and_its_dorsal_mirror() -> None:
    probes = probe_plan(PALM, NAMING, station_plan(PALM, NAMING))

    assert probes.bore_probe_points_mm == ((0.0, -6.6), (0.0, 6.6))
    assert probes.center_channel_open is False


def test_palm_tendon_channels_are_probed_at_every_station_with_solid_controls() -> None:
    probes = probe_plan(PALM, NAMING, station_plan(PALM, NAMING))
    channel = probes.palm_tendon_probe

    assert channel.object_name == "HJ_V3_PALM"
    assert channel.axis == "Z"
    assert _flat(channel.open_points_mm) == pytest.approx(
        [-45.0, -6.6, -15.0, -6.6, 15.0, -6.6, 45.0, -6.6, -71.0, -6.6]
    )
    # Controls sit midway between row stations, where the plate must be solid.
    assert _flat(channel.solid_points_mm) == pytest.approx([-30.0, -6.6, 0.0, -6.6, 30.0, -6.6])


def test_the_air_port_is_probed_where_the_spec_puts_it_with_plate_above_as_control() -> None:
    probes = probe_plan(PALM, NAMING, station_plan(PALM, NAMING))
    port = probes.air_port_probe

    assert port.object_name == "HJ_V3_PALM"
    assert port.axis == "Y"
    assert _flat(port.open_points_mm) == pytest.approx([0.0, -43.1])
    assert _flat(port.solid_points_mm) == pytest.approx([0.0, -20.0, 0.0, -30.0])


def test_the_sweep_and_closure_follow_the_link_limit_and_the_spring_gradient() -> None:
    probes = probe_plan(PALM, NAMING, station_plan(PALM, NAMING))

    assert probes.sweep_angles_deg == tuple(float(a) for a in range(-50, 51, 10))
    assert probes.pivot_offset_mm == 27.0
    assert probes.hinge_axis == "X"
    assert probes.mating_twist_deg == 0.0
    assert probes.travel_shares == pytest.approx((1.0, 0.625))
    assert probes.full_travel_deg == 50.0
    assert probes.closure_steps == 8


def test_a_link_with_a_wider_limit_widens_the_sweep_without_anyone_editing_a_list() -> None:
    from dataclasses import replace

    from src.core.domain.hinge_chain import HingePhalanxSpec

    wider = replace(
        PALM,
        finger=replace(
            PALM.finger,
            link=HingePhalanxSpec(
                joint_count=2, joint_center_offset_mm=27.0, maximum_articulation_deg=60.0
            ),
        ),
    )

    probes = probe_plan(wider, NAMING, station_plan(wider, NAMING))

    assert probes.sweep_angles_deg[0] == -60.0 and probes.sweep_angles_deg[-1] == 60.0
    assert probes.full_travel_deg == 60.0
