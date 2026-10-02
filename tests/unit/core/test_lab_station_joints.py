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


def test_elbow_take_up_closes_all_four_faces_without_early_penetration() -> None:
    from src.core.domain.lab_station_joints import ElbowClosureSpec

    spec = ElbowClosureSpec()
    assert spec.stroke_mm == pytest.approx(0.7)
    for travel in (0, 0.1, 0.3, 0.45, 0.6, spec.stroke_mm):
        offsets = spec.offsets(travel)
        gaps = (
            0.2 + offsets["elbow_knob"] - offsets["elbow_bolt"],
            0.1 + offsets["lower"] - offsets["elbow_knob"],
            0.2 - offsets["lower"],
            0.2 + offsets["elbow_nut"],
        )
        assert min(gaps) >= -1e-12
        assert sum(gaps) == pytest.approx(0.7 - travel)
    assert spec.offsets(spec.stroke_mm) == pytest.approx(
        {"elbow_nut": -0.2, "elbow_bolt": 0.5, "elbow_knob": 0.3, "lower": 0.2}
    )
    with pytest.raises(ValueError):
        spec.offsets(0.8)


def test_elbow_closure_rejects_nonphysical_gaps() -> None:
    from src.core.domain.lab_station_joints import ElbowClosureSpec

    with pytest.raises(ValueError):
        ElbowClosureSpec(tooth_gap_mm=-0.1)
    with pytest.raises(ValueError):
        ElbowClosureSpec(head_gap_mm=float("nan"))


def test_shoulder_closure_keeps_base_fixed_and_moves_connected_arm_inward() -> None:
    from src.core.domain.lab_station_joints import ShoulderClosureSpec

    spec = ShoulderClosureSpec()
    for index in range(71):
        travel = spec.stroke_mm * index / 70
        offsets = spec.offsets(travel)
        gaps = (
            0.2 + offsets["shoulder_knob"] - offsets["shoulder_bolt"],
            0.1 - offsets["shoulder_knob"],
            0.2 + offsets["upper"],
            0.2 + offsets["shoulder_nut"] - offsets["upper"],
        )
        assert min(gaps) >= -1e-12
        assert sum(gaps) == pytest.approx(0.7 - travel)
    assert spec.offsets(spec.stroke_mm) == pytest.approx(
        {"shoulder_nut": -0.4, "shoulder_bolt": 0.3, "shoulder_knob": 0.1, "upper": -0.2}
    )
    with pytest.raises(ValueError):
        spec.offsets(float("nan"))
    with pytest.raises(ValueError):
        spec.offsets(0.71)
