"""Side bracing must reach the ear, with room for both retention variants."""

import pytest

from src.core.domain.biaxial_hinge import BiaxialHingeSpec
from src.core.domain.inset_hinge import InsetHingeSpec


def test_biaxial_root_reaches_ear_instead_of_stopping_at_a_shallow_foot() -> None:
    spec = BiaxialHingeSpec()
    base, shoulder, neck = spec.root_profile_mm
    old = InsetHingeSpec()
    assert shoulder[0] - spec.body_length_mm / 2 >= 2.4
    assert base[1] >= 5.0
    assert shoulder[0] >= spec.joint_center_offset_mm - spec.lug_outer_diameter_mm / 2
    assert shoulder[1] == spec.lug_thickness_mm / 2
    assert 0 < spec.root_transition_angle_deg < 45
    assert 0 < spec.gusset_slope_deg < 45
    assert spec.body_outer_diameter_mm == 36
    assert spec.unit_pitch_mm < old.unit_pitch_mm
    assert spec.connector_envelope_radius_mm < 18
    assert neck[0] > shoulder[0]
    assert spec.side_hinge_running_clearance_mm == pytest.approx(0.6)


def test_both_pin_styles_have_positive_retention_without_blocking_sensor_channel() -> None:
    spec = BiaxialHingeSpec()
    assert spec.retention_styles == ("print_in_place_double_head", "separate_pin_and_clip")
    assert spec.retainer_inner_radius_mm > spec.center_channel_diameter_mm / 2 + 0.3
    assert spec.retainer_diameter_mm > spec.printed_pin_bore_mm
    assert spec.retainer_seat_diameter_mm - spec.retainer_diameter_mm >= 0.59
    assert (spec.lug_outer_diameter_mm - spec.retainer_seat_diameter_mm) / 2 >= 2
    assert spec.retainer_seat_depth_mm < spec.lug_thickness_mm
    assert spec.clip_thickness_mm < spec.groove_length_mm
    assert spec.clip_opening_mm < spec.groove_diameter_mm < spec.pin_diameter_mm
    assert spec.clip_inner_diameter_mm > spec.groove_diameter_mm
    assert spec.clip_inner_diameter_mm < spec.pin_diameter_mm


@pytest.mark.parametrize(
    "changes",
    [
        {"lug_outer_diameter_mm": 9.6},
        {"lug_outer_diameter_mm": 11.0},
        {"pin_diameter_mm": 3.0},
    ],
)
def test_retention_revision_rejects_thin_seats_colliding_roots_and_unretained_clips(changes):
    with pytest.raises(ValueError):
        BiaxialHingeSpec(**changes)
