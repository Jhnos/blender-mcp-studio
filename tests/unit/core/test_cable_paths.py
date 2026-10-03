"""Curve envelopes must conservatively cover bends between inspection points."""

from math import pi, sqrt

import pytest

from src.core.domain.cable_paths import CubicPath, sample_path


def test_straight_path_has_exact_length_and_bounded_sampling() -> None:
    curve = CubicPath(((0, 0, 0), (10, 0, 0), (20, 0, 0), (30, 0, 0)))
    sampled = sample_path((curve,), step_mm=0.5, deviation_mm=0.01)
    assert sampled.length_lower_mm == pytest.approx(30)
    assert sampled.length_upper_mm == pytest.approx(30)
    assert sampled.points_mm[0] == (0, 0, 0)
    assert sampled.points_mm[-1] == (30, 0, 0)
    assert sampled.max_step_mm <= 0.5
    assert sampled.deviation_mm == pytest.approx(0, abs=1e-12)


def test_quarter_circle_reference_and_curve_between_samples() -> None:
    k = 4 * (sqrt(2) - 1) / 3
    curve = CubicPath(((1, 0, 0), (1, k, 0), (k, 1, 0), (0, 1, 0)))
    sampled = sample_path((curve,), step_mm=0.05, deviation_mm=0.0001)
    assert abs((sampled.length_lower_mm + sampled.length_upper_mm) / 2 - pi / 2) < 0.001
    assert sampled.length_lower_mm <= 1.57102 <= sampled.length_upper_mm
    assert curve.point(0.5) == pytest.approx((sqrt(0.5), sqrt(0.5), 0))
    assert curve.curvature(0.5) == pytest.approx(1, abs=0.01)
    assert sampled.inspection_radius_mm(3) >= 3 + sampled.max_step_mm / 2


def test_disconnected_or_reversed_curve_join_is_rejected() -> None:
    first = CubicPath(((0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0)))
    disconnected = CubicPath(((4, 0, 0), (5, 0, 0), (6, 0, 0), (7, 0, 0)))
    reverse = CubicPath(((3, 0, 0), (2, 0, 0), (1, 0, 0), (0, 0, 0)))
    with pytest.raises(ValueError, match="join"):
        sample_path((first, disconnected))
    with pytest.raises(ValueError, match="tangent"):
        sample_path((first, reverse))


def test_loop_cannot_disappear_when_endpoints_coincide() -> None:
    loop = CubicPath(((0, 0, 0), (20, 20, 0), (-20, 20, 0), (0, 0, 0)))
    sampled = sample_path((loop,))
    assert sampled.length_lower_mm > 30
    assert max(p[1] for p in sampled.points_mm) > 14


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf")])
def test_invalid_sampling_is_rejected(value: float) -> None:
    curve = CubicPath(((0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0)))
    with pytest.raises(ValueError):
        sample_path((curve,), step_mm=value)


def test_nonfinite_geometry_is_rejected() -> None:
    with pytest.raises(ValueError):
        CubicPath(((0, 0, 0), (1, float("nan"), 0), (2, 0, 0), (3, 0, 0)))


def test_three_dimensional_length_and_refinement_bounds() -> None:
    line = CubicPath(((0, 0, 0), (10, 10, 10), (20, 20, 20), (30, 30, 30)))
    assert sample_path((line,)).length_lower_mm == pytest.approx(30 * sqrt(3))
    bend = CubicPath(((0, 0, 0), (20, 30, 10), (-10, 20, 15), (10, 0, 20)))
    coarse = sample_path((bend,), step_mm=2, deviation_mm=0.1)
    fine = sample_path((bend,), step_mm=0.1, deviation_mm=0.001)
    assert coarse.length_lower_mm <= fine.length_lower_mm
    assert fine.length_upper_mm <= coarse.length_upper_mm
    assert fine.length_upper_mm - fine.length_lower_mm < 0.001
