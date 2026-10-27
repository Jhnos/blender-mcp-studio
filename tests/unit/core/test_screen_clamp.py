"""Nominal lead and indexed endpoint contract, independent of Blender."""

import math
from dataclasses import asdict

import pytest

from src.core.domain.lab_station_joints import ScreenFoldSpec
from src.core.domain.screen_clamp import ScreenClampSpec


@pytest.mark.parametrize("target", [0, 15, 30, 45, 60])
def test_indexed_targets_follow_sequence_and_nominal_screw_lead(target: float) -> None:
    motion = ScreenFoldSpec(release_mm=2.2, screw_mm=2.4, target_angle_deg=target)
    spec = ScreenClampSpec(sequence=motion)
    for p in range(101):
        state = spec.pose(p, axial_float_mm=0.28)
        sequence = motion.pose(p)
        assert state.body_x_mm == pytest.approx(-0.2 + sequence["release_mm"])
        assert state.active_x_mm == pytest.approx(sequence["release_mm"] - sequence["screw_mm"])
        assert (state.body_angle_rad - state.active_angle_rad) * spec.pitch_mm / (
            2 * math.pi
        ) == pytest.approx(sequence["screw_mm"])
        assert state.pin_float_mm == 0.28
        evaluated = {
            key: eval(
                expr,
                {"__builtins__": {}, "min": min, "max": max, "pi": math.pi},
                {"progress": p, "pin_float": 0.28},
            )
            for key, expr in spec.driver_expressions().items()
        }
        assert evaluated == pytest.approx(asdict(state))
    assert motion.pose(100)["angle_deg"] == target
    assert spec.pose(0) == spec.pose(100) if target == 60 else spec.pose(0) != spec.pose(100)
    assert [spec.pose(p) for p in range(101)] == list(
        reversed([spec.pose(p) for p in range(100, -1, -1)])
    )


@pytest.mark.parametrize("target", [-1, 61, float("nan"), float("inf")])
def test_fold_rejects_invalid_target(target: float) -> None:
    with pytest.raises(ValueError):
        ScreenFoldSpec(target_angle_deg=target)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"pitch_mm": 0},
        {"pitch_mm": float("nan")},
        {"float_limit_mm": -1},
        {"float_limit_mm": float("inf")},
        {"sequence": ScreenFoldSpec(target_angle_deg=7)},
        {"sequence": ScreenFoldSpec(working_angle_deg=61)},
    ],
)
def test_clamp_rejects_invalid_dimensions_and_nonindexed_endpoints(kwargs) -> None:
    with pytest.raises(ValueError):
        ScreenClampSpec(**kwargs)


def test_clamp_rejects_out_of_range_float_and_progress() -> None:
    spec = ScreenClampSpec()
    for value in (-0.281, 0.281, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            spec.pose(50, axial_float_mm=value)
    for value in (-1, 101, float("nan")):
        with pytest.raises(ValueError):
            spec.pose(value)
