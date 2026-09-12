"""External-size and reach constraints for the instrument packaging prototype."""

import math

import pytest

from src.core.domain.lab_station import LabStationSpec


def test_touch_glass_not_the_smaller_product_summary_controls_the_pocket() -> None:
    spec = LabStationSpec()
    assert spec.lcd_glass_mm == (127.7, 87.45)
    assert spec.lcd_pocket_mm == pytest.approx((128.5, 88.25))
    assert spec.lcd_window_mm == (110.0, 67.0)


def test_each_separate_base_panel_leaves_room_on_p2s() -> None:
    spec = LabStationSpec()
    assert spec.base_panel_mm == (230.0, 150.0, 6.0)
    assert all(dimension + 12 <= 256 for dimension in spec.base_panel_mm[:2])


def test_two_rigid_links_reach_shared_container_without_stretching() -> None:
    spec = LabStationSpec()
    for side in (-1, 1):
        root, elbow, wrist = spec.arm_points(side)
        assert math.dist(root, elbow) == pytest.approx(130)
        assert math.dist(elbow, wrist) == pytest.approx(130)
        probe = spec.probe_origin(side)
        assert math.dist(root[:2], probe[:2]) == pytest.approx(200, abs=15)
        assert math.dist(probe[:2], spec.vessel_center_mm[:2]) < 25


def test_unreachable_configuration_and_invalid_dimensions_fail_before_blender() -> None:
    with pytest.raises(ValueError, match="reach"):
        LabStationSpec(link_mm=50)
    with pytest.raises(ValueError, match="positive"):
        LabStationSpec(wall_mm=-1)
    with pytest.raises(ValueError, match="finite"):
        LabStationSpec(link_mm=float("nan"))


def test_independent_wrists_leave_gap_between_24_mm_joint_bodies() -> None:
    spec = LabStationSpec()
    left = spec.arm_points(-1)[2]
    right = spec.arm_points(1)[2]
    assert right[0] - left[0] >= 36
    assert abs(left[2] - right[2]) >= 30
    assert abs(left[1] - right[1]) >= 16


def test_straight_extraction_clears_rim_and_keeps_wrist_out_of_the_path() -> None:
    spec = LabStationSpec()
    for side, length in ((-1, 102), (1, 115)):
        probe = spec.probe_origin(side)
        wrist = spec.arm_points(side)[2]
        lowest_tip = probe[2] - 69 - length / 2
        assert lowest_tip + spec.lift_travel_mm >= 120
        assert wrist[1] - probe[1] >= 40
        assert spec.lift_travel_mm == 100


@pytest.mark.parametrize("travel", [-1.0, 35.0, float("nan"), 101.0])
def test_extraction_stroke_cannot_exceed_guide_or_fail_clearance(travel: float) -> None:
    with pytest.raises(ValueError, match="stroke"):
        LabStationSpec(lift_travel_mm=travel)


def test_elbow_necks_leave_the_tooth_plane_before_rejoining_links() -> None:
    spec = LabStationSpec()
    for side in (-1, 1):
        _, elbow, _ = spec.arm_points(side)
        upper, lower = spec.elbow_necks(side)
        assert upper[0] == pytest.approx(elbow[0] - 14)
        assert lower[0] == pytest.approx(elbow[0] + 14)
        for neck in (upper, lower):
            assert math.dist(neck[1:], elbow[1:]) >= 29.99


def test_shoulder_neck_keeps_link_outside_fixed_tooth_half() -> None:
    spec = LabStationSpec()
    for side in (-1, 1):
        root, _, _ = spec.arm_points(side)
        neck = spec.shoulder_neck(side)
        assert neck[0] == pytest.approx(root[0] + 14)
        assert math.dist(neck[1:], root[1:]) == pytest.approx(30)
        assert neck[2] > root[2]


def test_rotary_lift_closes_four_bar_and_keeps_head_vertical() -> None:
    from src.core.domain.lab_station import RotaryLiftSpec

    spec = RotaryLiftSpec()
    for lift in range(101):
        a, b, c, d = spec.joints(lift)
        assert math.dist(a, c) == pytest.approx(130)
        assert math.dist(b, d) == pytest.approx(130)
        assert tuple(d[i] - c[i] for i in range(3)) == pytest.approx((0, 0, 40))
        assert c[2] == pytest.approx(lift)
        assert -10 <= c[1] <= 0
    with pytest.raises(ValueError):
        spec.joints(101)
    with pytest.raises(ValueError):
        RotaryLiftSpec(length_mm=40)
