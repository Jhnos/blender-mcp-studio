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


def test_wrist_take_up_closes_head_carrier_chain_without_moving_carrier() -> None:
    from src.core.domain.lab_station_joints import WristClosureSpec

    spec = WristClosureSpec()
    for index in range(71):
        travel = spec.stroke_mm * index / 70
        offsets = spec.offsets(travel)
        gaps = (
            0.2 + offsets["tip_knob"] - offsets["tip_bolt"],
            0.1 + offsets["head"] - offsets["tip_knob"],
            0.2 - offsets["head"],
            0.2 + offsets["tip_nut"],
        )
        assert min(gaps) >= -1e-12
        assert sum(gaps) == pytest.approx(0.7 - travel)
        assert "platform" not in offsets
    assert spec.offsets(spec.stroke_mm) == pytest.approx(
        {"tip_nut": -0.2, "tip_bolt": 0.5, "tip_knob": 0.3, "head": 0.2}
    )
    for invalid in (-0.1, 0.71, float("nan")):
        with pytest.raises(ValueError):
            spec.offsets(invalid)


def test_screen_fold_sequence_releases_screw_before_teeth_and_reseats_before_lock() -> None:
    from src.core.domain.lab_station_joints import ScreenFoldSpec

    spec = ScreenFoldSpec()
    for progress, expected in (
        (0, (60, 0, 0)),
        (10, (60, 0, 1)),
        (20, (60, 0, 2)),
        (30, (60, 1, 2)),
        (40, (60, 2, 2)),
        (50, (30, 2, 2)),
        (60, (0, 2, 2)),
        (70, (0, 1, 2)),
        (80, (0, 0, 2)),
        (90, (0, 0, 1)),
        (100, (0, 0, 0)),
    ):
        assert tuple(spec.pose(progress).values()) == pytest.approx(expected)
    expressions = spec.driver_expressions()
    for progress in [i / 10 for i in range(1001)]:
        pose = spec.pose(progress)
        if 0 < pose["angle_deg"] < 60:
            assert pose["release_mm"] == 2 and pose["screw_mm"] == 2
        if pose["release_mm"] > 0:
            assert pose["screw_mm"] == 2
        evaluated = {
            channel: eval(
                expression, {"__builtins__": {}, "min": min, "max": max}, {"progress": progress}
            )
            for channel, expression in expressions.items()
        }
        assert evaluated == pytest.approx(pose)
    # Reversing progress traverses the same sequence without a hidden state machine.
    assert [spec.pose(i) for i in range(101)] == list(
        reversed([spec.pose(i) for i in range(100, -1, -1)])
    )


def test_screen_fold_rejects_invalid_travel_and_out_of_range_progress() -> None:
    from src.core.domain.lab_station_joints import ScreenFoldSpec

    for kwargs in (
        {"working_angle_deg": 0},
        {"release_mm": 0.5},
        {"screw_mm": 1},
        {"release_mm": float("nan")},
    ):
        with pytest.raises(ValueError):
            ScreenFoldSpec(**kwargs)
    for progress in (-1, 101, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            ScreenFoldSpec().pose(progress)
