from dataclasses import FrozenInstanceError

import pytest

from src.core.domain.hinge_chain import HingePhalanxSpec


def test_four_revolute_joints_require_five_identical_phalanx_links() -> None:
    spec = HingePhalanxSpec(joint_count=4)

    assert spec.assembly_unit_count == 5
    assert spec.degrees_of_freedom == 4
    assert spec.printable_part_types == ("hinge_phalanx",)


def test_orthogonal_male_and_female_ports_create_alternating_joint_axes() -> None:
    spec = HingePhalanxSpec()

    assert spec.male_hinge_axis == "X"
    assert spec.female_hinge_axis == "Y"
    assert spec.assembly_rotations_deg == (0.0, 90.0, 0.0, 90.0, 0.0)
    assert spec.axis_names == ("J1_X", "J2_Y", "J3_X", "J4_Y")


def test_finger_like_body_is_slender_and_not_a_disc() -> None:
    spec = HingePhalanxSpec()

    assert spec.body_length_mm > spec.body_width_mm > spec.body_depth_mm
    assert spec.body_slenderness_ratio >= 1.6


def test_printed_pin_bore_and_metal_bearing_seat_share_one_axis() -> None:
    spec = HingePhalanxSpec(pin_diameter_mm=4.0, printed_radial_clearance_mm=0.25)

    assert spec.printed_pin_bore_mm == pytest.approx(4.5)
    assert spec.bearing_seat_diameter_mm == pytest.approx(8.1)
    assert spec.bearing_radial_wall_mm >= spec.minimum_wall_mm
    assert spec.common_hardware == ("4mm_pin", "MR84_4x8x3_bearing")


def test_four_tendon_routes_fit_inside_the_oval_body_wall() -> None:
    spec = HingePhalanxSpec()

    assert spec.tendon_positions_mm == (
        (-7.0, 0.0),
        (0.0, -7.0),
        (0.0, 7.0),
        (7.0, 0.0),
    )
    quarter_turned = {(-y_mm, x_mm) for x_mm, y_mm in spec.tendon_positions_mm}
    assert quarter_turned == set(spec.tendon_positions_mm)
    assert spec.minimum_tendon_edge_wall_mm >= spec.minimum_wall_mm


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"joint_count": 0}, "joint_count"),
        ({"body_length_mm": 25.0}, "phalanx"),
        ({"minimum_wall_mm": 0.7}, "wall"),
        ({"pin_diameter_mm": 2.0}, "pin"),
        ({"bearing_seat_diameter_mm": 12.0}, "bearing"),
        ({"tendon_radius_mm": 10.0}, "tendon"),
        ({"fork_gap_mm": 4.0}, "fork gap"),
    ],
)
def test_unmanufacturable_hinge_specs_fail_loudly(
    overrides: dict[str, float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        HingePhalanxSpec(**overrides)


def test_hinge_spec_is_immutable() -> None:
    spec = HingePhalanxSpec()

    with pytest.raises(FrozenInstanceError):
        spec.pin_diameter_mm = 6.0  # type: ignore[misc]
