"""One phalanx as a list of named solids, checkable without Blender.

Every magic number in `finger_v3_geometry.py` — the 0.72 neck ratio, the 9 mm
neck, the ±1 mm overlap, the +4/+6 drill overrun, the 24 bore segments — has a
field here with the V3 value as its default, and the order of operations is
part of the plan because it is load-bearing: the bores are drilled last, after
the lug that would otherwise fill them straight back in.
"""

import pytest

from src.core.domain.compact_link import CompactHingeLinkSpec
from src.core.domain.finger_v3 import SingleTendonFingerSpec
from src.core.domain.palm_v3 import AnthropomorphicPalmSpec
from src.core.planning.csg import Box, Cylinder, Ellipsoid
from src.core.planning.naming import NamingPolicy
from src.core.planning.phalanx_plan import finger_plan, phalanx_plan

V3 = AnthropomorphicPalmSpec().finger
NAMING = NamingPolicy("HJ_", "V3")
GRADIENT = SingleTendonFingerSpec(
    link=CompactHingeLinkSpec(), moment_arms_mm=(5.5, 3.6), spring_stiffness_ratio=(1.0, 1.6)
)


def test_the_body_and_the_operation_order_are_the_generators() -> None:
    plan = phalanx_plan(V3, NAMING, part_index=1, tendon_offset_mm=6.6)

    assert plan.name == "HJ_V3_PHALANX_1"
    assert plan.body == Ellipsoid("HJ_V3_PHALANX_1", (24.0, 22.0, 40.0), (0.0, 0.0, 0.0))
    assert [(op.mode, op.solid.name) for op in plan.operations] == [
        ("UNION", "HJ_MALE_CONNECTOR"),
        ("UNION", "HJ_MALE_LUG"),
        ("DIFFERENCE", "HJ_CUT_MALE_PIN_BORE"),
        ("UNION", "HJ_FEMALE_CONNECTOR_-1"),
        ("UNION", "HJ_FEMALE_LUG_-1"),
        ("UNION", "HJ_FEMALE_CONNECTOR_+1"),
        ("UNION", "HJ_FEMALE_LUG_+1"),
        ("DIFFERENCE", "HJ_CUT_FEMALE_PIN_BORE"),
        ("DIFFERENCE", "HJ_CUT_BEARING_SEAT_0"),
        ("DIFFERENCE", "HJ_CUT_BEARING_SEAT_1"),
        ("DIFFERENCE", "HJ_CUT_TENDON"),
        ("DIFFERENCE", "HJ_CUT_WIRING"),
    ]


def test_the_male_end_is_the_ledgers_numbers() -> None:
    ops = {op.solid.name: op.solid for op in phalanx_plan(V3, NAMING, 1, 6.6).operations}
    link = V3.link

    neck = ops["HJ_MALE_CONNECTOR"]
    assert isinstance(neck, Box)
    assert neck.size_mm == pytest.approx((5.0, 13.0 * 0.72, 9.0))
    assert neck.center_mm == pytest.approx((0.0, 0.0, 19.0))
    lug = ops["HJ_MALE_LUG"]
    assert isinstance(lug, Cylinder)
    assert (lug.radius_mm, lug.height_mm, lug.axis) == (6.5, 5.0, "X")
    assert lug.center_mm == (0.0, 0.0, 27.0) and lug.segments is None
    bore = ops["HJ_CUT_MALE_PIN_BORE"]
    assert isinstance(bore, Cylinder)
    assert bore.radius_mm == link.printed_pin_bore_mm / 2
    assert bore.height_mm == pytest.approx(5.0 + 4.0) and bore.segments == 24


def test_the_female_end_straddles_along_the_same_axis() -> None:
    ops = {op.solid.name: op.solid for op in phalanx_plan(V3, NAMING, 1, 6.6).operations}
    link = V3.link
    lug_x = link.fork_gap_mm / 2 + link.fork_lug_thickness_mm / 2

    for side, sign in (("-1", -1.0), ("+1", 1.0)):
        connector = ops[f"HJ_FEMALE_CONNECTOR_{side}"]
        lug = ops[f"HJ_FEMALE_LUG_{side}"]
        assert isinstance(connector, Box) and isinstance(lug, Cylinder)
        assert connector.size_mm == pytest.approx((4.5, 13.0 * 0.72, 9.0))
        assert connector.center_mm == pytest.approx((sign * lug_x, 0.0, -19.0))
        assert lug.center_mm == pytest.approx((sign * lug_x, 0.0, -27.0)) and lug.axis == "X"
    bore = ops["HJ_CUT_FEMALE_PIN_BORE"]
    assert isinstance(bore, Cylinder)
    assert bore.height_mm == pytest.approx(link.fork_total_width_mm + 4.0)
    seat = ops["HJ_CUT_BEARING_SEAT_0"]
    assert isinstance(seat, Cylinder)
    assert seat.radius_mm == link.bearing_seat_diameter_mm / 2
    assert seat.height_mm == link.bearing_width_mm


def test_the_bores_run_the_whole_unit_on_the_side_they_belong() -> None:
    ops = {op.solid.name: op.solid for op in phalanx_plan(V3, NAMING, 1, 6.6).operations}
    link = V3.link
    reach = 2.0 * (link.joint_center_offset_mm + link.lug_outer_diameter_mm / 2) + 6.0

    tendon, wiring = ops["HJ_CUT_TENDON"], ops["HJ_CUT_WIRING"]
    assert isinstance(tendon, Cylinder) and isinstance(wiring, Cylinder)
    assert tendon.center_mm == (0.0, -6.6, 0.0) and wiring.center_mm == (0.0, 6.6, 0.0)
    assert tendon.height_mm == pytest.approx(reach) == wiring.height_mm
    assert tendon.radius_mm == link.tendon_hole_diameter_mm / 2
    assert tendon.axis == "Z" and tendon.segments == 24


def test_a_bearingless_link_plans_no_seat_cuts() -> None:
    names = [op.solid.name for op in phalanx_plan(GRADIENT, NAMING, 1, 5.5).operations]

    assert not any(name.startswith("HJ_CUT_BEARING_SEAT") for name in names)


def test_v3s_finger_is_one_part_copied_three_times_one_pitch_apart() -> None:
    finger = finger_plan(V3, NAMING)

    assert [part.name for part in finger.parts] == ["HJ_V3_PHALANX_1"]
    assert [(u.name, u.part_index, u.lift_mm, u.rotation_deg) for u in finger.units] == [
        ("HJ_V3_PHALANX_1", 0, 0.0, 0.0),
        ("HJ_V3_PHALANX_2", 0, 54.0, 0.0),
        ("HJ_V3_PHALANX_3", 0, 108.0, 0.0),
    ]


def test_a_gradient_finger_plans_one_part_per_distinct_arm() -> None:
    """The base unit carries the base arm; every unit after carries its joint's arm."""
    finger = finger_plan(GRADIENT, NAMING)

    assert [part.name for part in finger.parts] == ["HJ_V3_PHALANX_1", "HJ_V3_PHALANX_2"]
    assert [u.part_index for u in finger.units] == [0, 1, 1]
    tendons = [
        next(op.solid for op in part.operations if op.solid.name == "HJ_CUT_TENDON")
        for part in finger.parts
    ]
    assert [t.center_mm[1] for t in tendons] == [-5.5, -3.6]
