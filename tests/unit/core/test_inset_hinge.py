"""The reinforced joint must fit inside its disc, including printed pins."""

import math

import pytest

from src.core.domain.inset_hinge import InsetHingeSpec


def test_reinforced_roots_and_printed_pins_stay_inside_disc() -> None:
    spec = InsetHingeSpec()
    assert spec.body_outer_diameter_mm == 34.0
    assert spec.center_channel_diameter_mm == 10.0
    assert spec.unit_pitch_mm == 20.0
    assert spec.assembly_unit_count == 9
    assert len(spec.tendon_positions_mm) == 4
    assert spec.connector_envelope_radius_mm < spec.body_outer_diameter_mm / 2
    assert 0 < spec.root_transition_angle_deg < 45
    assert 0 < spec.gusset_slope_deg < 45
    assert spec.side_hinge_running_clearance_mm == pytest.approx(0.6)
    assert spec.printed_pin_bore_mm == 4.5
    assert spec.pin_length_mm == pytest.approx(9.2)
    assert spec.pin_tip_inner_radius_mm > spec.center_channel_diameter_mm / 2
    assert spec.printable_part_types == ("inset_hinge_module", "headed_side_pin")
    assert spec.required_pin_count == 16
    for vertex in spec.root_profile_mm:
        assert all(math.isfinite(value) for value in vertex)


@pytest.mark.parametrize(
    "changes",
    [
        {"body_outer_diameter_mm": 28.0},
        {"body_length_mm": 2.0},
        {"side_female_center_mm": 10.8},
        {"pin_shank_length_mm": 10.0},
        {"pin_shank_length_mm": 4.0},
        {"pin_diameter_mm": 9.0},
        {"tendon_radius_mm": 16.0},
        {"joint_center_offset_mm": 13.0},
        {"joint_count": 7},
        {"maximum_articulation_deg": float("nan")},
    ],
)
def test_rejects_incompatible_dimensions(changes: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        InsetHingeSpec(**changes)
