from dataclasses import FrozenInstanceError

import pytest

from src.core.domain.hollow_side_hinge import HollowSideHingeSpec


def test_short_repeated_modules_double_joint_density_and_reduce_total_length() -> None:
    spec = HollowSideHingeSpec()

    assert spec.joint_count == 8
    assert spec.assembly_unit_count == 9
    assert spec.body_length_mm <= 14.0
    assert spec.unit_pitch_mm <= 20.0
    assert spec.assembled_height_mm < 200.0
    assert spec.assembled_height_mm == pytest.approx(188.6)


def test_alternating_modules_accumulate_large_bend_in_both_planes() -> None:
    spec = HollowSideHingeSpec()

    assert spec.axis_names == (
        "J1_X",
        "J2_Y",
        "J3_X",
        "J4_Y",
        "J5_X",
        "J6_Y",
        "J7_X",
        "J8_Y",
    )
    assert spec.assembly_rotations_deg == (0.0, 90.0, 0.0, 90.0, 0.0, 90.0, 0.0, 90.0, 0.0)
    assert spec.cumulative_articulation_x_deg >= 120.0
    assert spec.cumulative_articulation_y_deg >= 120.0
    assert spec.geometric_face_clearance_deg >= spec.maximum_articulation_deg
    assert spec.joint_gap_mm >= (
        spec.bearing_seat_diameter_mm + 2.0 * spec.minimum_running_clearance_mm
    )


def test_annular_body_reserves_a_continuous_central_wire_channel() -> None:
    spec = HollowSideHingeSpec()

    assert spec.center_channel_diameter_mm == pytest.approx(10.0)
    assert spec.center_channel_is_open
    assert spec.minimum_annular_wall_mm >= spec.minimum_wall_mm


def test_each_joint_uses_two_side_pins_without_crossing_the_center_channel() -> None:
    spec = HollowSideHingeSpec()

    assert spec.pins_per_joint == 2
    assert spec.bearings_per_joint == 2
    assert spec.center_hardware_clearance_mm >= spec.minimum_running_clearance_mm
    assert spec.side_lug_body_clearance_mm >= spec.minimum_running_clearance_mm
    assert spec.common_hardware == ("M4_side_pin", "MR84_4x8x3_bearing")


def test_side_lug_bridges_keep_a_printable_load_path_without_hitting_the_mating_lug() -> None:
    spec = HollowSideHingeSpec()

    assert spec.bridge_thickness_mm >= spec.minimum_wall_mm
    assert spec.bridge_to_opposite_lug_clearance_mm >= spec.minimum_running_clearance_mm
    assert spec.bridge_corner_radial_margin_mm >= spec.minimum_running_clearance_mm


def test_four_tendon_routes_clear_both_channel_and_outer_wall() -> None:
    spec = HollowSideHingeSpec()

    quarter_turned = {(-y_mm, x_mm) for x_mm, y_mm in spec.tendon_positions_mm}
    assert quarter_turned == set(spec.tendon_positions_mm)
    assert spec.minimum_tendon_inner_wall_mm >= spec.minimum_wall_mm
    assert spec.minimum_tendon_outer_wall_mm >= spec.minimum_wall_mm


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"joint_count": 3}, "even"),
        ({"body_length_mm": 22.0}, "short"),
        ({"center_channel_diameter_mm": 18.0}, "channel"),
        ({"side_male_center_mm": 5.0}, "hardware"),
        ({"side_female_center_mm": 8.0}, "side hinge"),
        ({"tendon_radius_mm": 7.0}, "tendon"),
        ({"maximum_articulation_deg": 20.0}, "articulation"),
    ],
)
def test_unmanufacturable_hollow_side_hinge_specs_fail_loudly(
    overrides: dict[str, float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        HollowSideHingeSpec(**overrides)


def test_hollow_side_hinge_spec_is_immutable() -> None:
    spec = HollowSideHingeSpec()

    with pytest.raises(FrozenInstanceError):
        spec.center_channel_diameter_mm = 12.0  # type: ignore[misc]
