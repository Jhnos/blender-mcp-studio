"""The palm as named solids: plate, boss, roots, routes, port and clamp.

`palm_v3_geometry.py` typed the station labels three ways and the routes as
a literal pair. Here every cut is named by the policy and placed by the spec,
and the ten route bores fall out of five stations times two routes.
"""

import pytest

from src.core.domain.palm_v3 import AnthropomorphicPalmSpec
from src.core.planning.csg import Box, Cylinder
from src.core.planning.naming import NamingPolicy
from src.core.planning.palm_plan import palm_plan
from src.core.planning.route_plan import route_plan
from src.core.planning.station_plan import station_plan

PALM = AnthropomorphicPalmSpec()
NAMING = NamingPolicy("HJ_", "V3")
STATIONS = station_plan(PALM, NAMING)


def test_two_routes_per_station_named_by_the_policy() -> None:
    routes = route_plan(PALM, NAMING, STATIONS)

    assert [(r.route, r.station, r.y_mm) for r in routes][:4] == [
        ("TENDON", "F1", -6.6),
        ("WIRING", "F1", 6.6),
        ("TENDON", "F2", -6.6),
        ("WIRING", "F2", 6.6),
    ]
    assert len(routes) == 10
    assert routes[-1].bore.name == "HJ_V3_CUT_WIRING_T"
    assert routes[-1].bore.center_mm == pytest.approx((-71.0, 6.6, -35.0))


def test_a_route_bore_runs_through_the_whole_plate_with_overrun() -> None:
    bore = route_plan(PALM, NAMING, STATIONS)[0].bore

    assert isinstance(bore, Cylinder)
    assert bore.radius_mm == PALM.finger.link.tendon_hole_diameter_mm / 2
    assert bore.height_mm == pytest.approx(70.0 + 8.0)
    assert bore.axis == "Z" and bore.segments == 24


def test_the_plate_and_boss_are_the_specs_numbers() -> None:
    plan = palm_plan(PALM, NAMING, STATIONS)

    assert plan.name == "HJ_V3_PALM"
    assert plan.plate == Box("HJ_V3_PALM", (114.0, 22.0, 70.0), (0.0, 0.0, -35.0))
    centre, size = PALM.thenar_bridge_mm
    assert plan.thenar == Box("HJ_V3_THENAR", size, centre)


def test_every_station_gets_a_root_placed_by_the_station() -> None:
    plan = palm_plan(PALM, NAMING, STATIONS)

    assert [root.name for root in plan.roots] == [
        "HJ_V3_ROOT_F1",
        "HJ_V3_ROOT_F2",
        "HJ_V3_ROOT_F3",
        "HJ_V3_ROOT_F4",
        "HJ_V3_ROOT_T",
    ]
    root = plan.roots[0]
    assert root.origin_mm == STATIONS[0].origin_mm and root.basis == STATIONS[0].basis
    assert root.stem == Box("HJ_V3_ROOT_F1_STEM", (5.0, 13.0, 27.0), (0.0, 0.0, 13.5))
    assert root.lug.center_mm == (0.0, 0.0, 27.0) and root.lug.axis == "X"
    assert root.bore.height_mm == pytest.approx(9.0) and root.bore.segments == 24
    assert plan.roots[4].basis == STATIONS[4].basis


def test_the_port_and_the_clamp_sit_where_the_spec_puts_them() -> None:
    plan = palm_plan(PALM, NAMING, STATIONS)

    assert plan.air_port.name == "HJ_V3_CUT_AIR_PORT"
    assert plan.air_port.center_mm == pytest.approx((0.0, 0.0, -43.1))
    assert plan.air_port.radius_mm == 3.0 and plan.air_port.axis == "Y"
    assert plan.air_port.height_mm == pytest.approx(22.0 + 8.0)
    outer, inner = plan.clamp
    assert outer == Box("HJ_V3_CUT_CLAMP_OUTER", (122.0, 30.0, 3.0), (0.0, 0.0, -50.0))
    assert inner == Box("HJ_V3_CUT_CLAMP_INNER", (108.0, 16.0, 7.0), (0.0, 0.0, -50.0))


def test_the_operation_order_is_boss_roots_routes_port_clamp() -> None:
    """The boss comes before the roots so the thumb root has something to land on."""
    plan = palm_plan(PALM, NAMING, STATIONS)

    assert plan.operations[0].solid.name == "HJ_V3_THENAR"
    assert plan.operations[0].mode == "UNION"
    assert plan.operations[1].solid.name.startswith("HJ_V3_CUT_TENDON")
    assert plan.operations[-2].solid.name == "HJ_V3_CUT_AIR_PORT"
    assert plan.operations[-1].solid.name == "HJ_V3_CUT_CLAMP_OUTER"
