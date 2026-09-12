"""Discrete locking and screen clearance must be supported by geometry, not a render."""

import pytest

from src.core.domain.lab_station_joints import ScreenHingeSpec, SerratedJointSpec


def test_teeth_mesh_at_index_but_block_a_half_step_until_released() -> None:
    joint = SerratedJointSpec()
    assert joint.step_deg == 15
    samples = [i / 4 for i in range(1440)]
    assert min(joint.face_gap(angle, 15) for angle in samples) >= 0.19
    assert min(joint.face_gap(angle, 7.5) for angle in samples) < -0.9
    assert min(joint.face_gap(angle, 7.5, released=True) for angle in samples) > 0.9


def test_screen_back_shell_clears_lid_and_stays_over_chassis_during_fold() -> None:
    hinge = ScreenHingeSpec()
    for angle in range(76):
        points = hinge.envelope(angle)
        assert min(p[2] for p in points) >= 86 - 1e-8
        assert all(-75 <= p[1] <= 75 for p in points)
    assert hinge.default_step * 15 == 60


def test_invalid_locking_parts_are_rejected() -> None:
    with pytest.raises(ValueError):
        SerratedJointSpec(teeth=0)
    with pytest.raises(ValueError):
        SerratedJointSpec(tooth_height_mm=-1)
    with pytest.raises(ValueError):
        SerratedJointSpec(release_mm=0.5)
