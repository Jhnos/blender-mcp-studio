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


def test_simple_arm_extracts_with_two_fixed_length_links() -> None:
    from math import dist

    from src.core.domain.lab_station import SimpleArmSpec

    spec = SimpleArmSpec()
    for amount in range(101):
        root, elbow, tip = spec.planar_joints(amount)
        assert dist(root, elbow) == pytest.approx(150)
        assert dist(elbow, tip) == pytest.approx(150)
        assert tip[0] == pytest.approx(spec.reach_mm)
        assert tip[1] == pytest.approx(72 + amount)
    assert 108 + spec.planar_joints(100)[2][1] - 125 > 110


def test_simple_arm_rejects_unreachable_pose() -> None:
    from src.core.domain.lab_station import SimpleArmSpec

    with pytest.raises(ValueError, match="reach"):
        SimpleArmSpec().planar_joints(300)


def test_electrode_forearm_closes_and_preserves_two_position_inputs() -> None:
    from math import dist

    from src.core.domain.lab_station import ElectrodeArmSpec

    spec = ElectrodeArmSpec()
    for forward in (-20, 0, 20):
        for lift in (0, 50, 100):
            root, a, b, c, d, tip = spec.joints(forward, lift)
            assert dist(root, a) == pytest.approx(150)
            assert dist(a, c) == pytest.approx(150)
            assert dist(b, d) == pytest.approx(150)
            assert dist(a, b) == pytest.approx(24)
            assert dist(c, d) == pytest.approx(24)
            assert dist(c, tip) == pytest.approx(22)
            assert tip == pytest.approx((spec.reach_mm + forward, 72 + lift))
            assert tuple(d[i] - c[i] for i in (0, 1)) == pytest.approx(
                tuple(b[i] - a[i] for i in (0, 1))
            )
    with pytest.raises(ValueError, match="reach"):
        spec.joints(500, 0)


def test_electrode_indexed_targets_keep_shoulder_and_land_on_real_tooth_angles() -> None:
    from src.core.domain.lab_station import ElectrodeArmSpec

    spec = ElectrodeArmSpec()
    _, a0, _, c0, _, _ = spec.joints()
    angle0 = math.atan2(c0[1] - a0[1], c0[0] - a0[0])
    assert spec.indexed_target(0) == pytest.approx((0, 0))
    for step in (1, 2, 3):
        forward, lift = spec.indexed_target(step)
        _, a, b, c, d, _ = spec.joints(forward, lift)
        assert a == pytest.approx(a0)
        angle = math.atan2(c[1] - a[1], c[0] - a[0])
        assert math.degrees(angle - angle0) == pytest.approx(step * 15)
        assert math.dist(b, d) == pytest.approx(150)
    for invalid in (0.5, True):
        with pytest.raises(ValueError):
            spec.indexed_target(invalid)


def test_shoulder_index_rotates_the_closed_chain_without_changing_elbow_angle() -> None:
    from src.core.domain.lab_station import ElectrodeArmSpec

    spec = ElectrodeArmSpec()
    first = spec.joints(*spec.indexed_target(1))
    second = spec.joints(*spec.indexed_target(1, shoulder_step=1))
    angle = math.radians(15)
    for (x, z), point in zip(first, second, strict=True):
        assert point == pytest.approx(
            (x * math.cos(angle) - z * math.sin(angle), x * math.sin(angle) + z * math.cos(angle))
        )
    for invalid in (True, 0.5):
        with pytest.raises(ValueError):
            spec.indexed_target(1, shoulder_step=invalid)


def test_continuous_shoulder_path_is_a_rigid_arc_not_a_straight_chord() -> None:
    from src.core.domain.lab_station import ElectrodeArmSpec

    spec = ElectrodeArmSpec()
    first = spec.joints(*spec.indexed_target(1))
    for degree in range(16):
        angle = math.radians(degree)
        actual = spec.joints(*spec.angular_target(15, degree))
        for (x, z), point in zip(first, actual, strict=True):
            assert point == pytest.approx(
                (
                    x * math.cos(angle) - z * math.sin(angle),
                    x * math.sin(angle) + z * math.cos(angle),
                )
            )
    assert spec.angular_target(15, 15) == pytest.approx(spec.indexed_target(1, shoulder_step=1))
    for bad in (float("nan"), float("inf")):
        with pytest.raises(ValueError):
            spec.angular_target(15, bad)


def test_wrist_index_tracks_platform_angle_instead_of_assuming_world_vertical() -> None:
    from src.core.domain.lab_station import ElectrodeArmSpec

    spec = ElectrodeArmSpec()
    assert spec.wrist_indexed_angle(0, 0, 0) == pytest.approx(0)
    assert spec.wrist_indexed_angle(0, 100, 1) == pytest.approx(19.313420802420246)
    assert spec.wrist_indexed_angle(*spec.indexed_target(1, shoulder_step=1), -1) == pytest.approx(
        0
    )
    with pytest.raises(ValueError):
        spec.wrist_indexed_angle(0, 100, 0.5)
