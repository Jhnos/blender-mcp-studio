"""Declared deposition envelopes include line width and directed arc extrema."""

from math import pi

import pytest

from src.core.domain.extrusion import ExtrusionPath


def path(**changes):
    values = dict(
        start_mm=(1.0, 1.0, 0.2),
        end_mm=(3.0, 1.0, 0.2),
        width_mm=0.5,
        height_mm=0.2,
        role="Support",
        layer_index=0,
    )
    values.update(changes)
    return ExtrusionPath(**values)


def test_straight_extrusion_contains_full_width_and_declared_height():
    measured = path().measure()
    assert measured.minimum_mm == (0.75, 0.75, 0.0)
    assert measured.maximum_mm == (3.25, 1.25, 0.2)
    assert measured.xy_length_mm == 2


def test_counterclockwise_arc_includes_extrema_beyond_both_endpoints():
    measured = path(
        start_mm=(1, 0, 0.2), end_mm=(0, -1, 0.2), center_xy_mm=(0, 0), clockwise=False
    ).measure()
    assert measured.minimum_mm == pytest.approx((-1.25, -1.25, 0))
    assert measured.maximum_mm == pytest.approx((1.25, 1.25, 0.2))
    assert measured.xy_length_mm == pytest.approx(1.5 * pi)


def test_clockwise_arc_uses_the_short_sweep_instead_of_whole_circle():
    measured = path(
        start_mm=(1, 0, 0.2), end_mm=(0, -1, 0.2), center_xy_mm=(0, 0), clockwise=True
    ).measure()
    assert measured.minimum_mm == pytest.approx((-0.25, -1.25, 0))
    assert measured.maximum_mm == pytest.approx((1.25, 0.25, 0.2))
    assert measured.xy_length_mm == pytest.approx(pi / 2)


def test_full_circle_with_same_endpoints_is_not_a_zero_length_move():
    measured = path(start_mm=(2, 1, 0.2), end_mm=(2, 1, 0.2), center_xy_mm=(1, 1)).measure()
    assert measured.xy_length_mm == pytest.approx(2 * pi)
    assert measured.minimum_mm == pytest.approx((-0.25, -0.25, 0))
    assert measured.maximum_mm == pytest.approx((2.25, 2.25, 0.2))


def test_nearly_straight_large_radius_arc_does_not_claim_whole_circle_bounds():
    measured = path(
        start_mm=(100, 100, 0.2),
        end_mm=(101, 100.001, 0.2),
        center_xy_mm=(100, 600),
        clockwise=False,
    ).measure()
    assert measured.maximum_mm[1] < 100.252
    assert measured.minimum_mm[0] > 99.749
    assert measured.xy_length_mm < 1.001


@pytest.mark.parametrize(
    "changes",
    [
        {"width_mm": 0},
        {"height_mm": float("nan")},
        {"start_mm": (float("inf"), 0, 0)},
        {"center_xy_mm": (1, 1)},
        {"role": ""},
        {"layer_index": -1},
        {"end_mm": (2, 0, 0.2), "start_mm": (1, 0, 0.2), "center_xy_mm": (0, 0)},
    ],
)
def test_invalid_or_incoherent_geometry_cannot_return_a_successful_envelope(changes):
    with pytest.raises(ValueError):
        path(**changes).measure()


def test_rounded_arc_inflates_xy_by_measured_radius_disagreement():
    measured = path(
        start_mm=(1, 1, 0.2), end_mm=(1.001, 1, 0.2), center_xy_mm=(0, 0), clockwise=True
    ).measure()
    assert 0 < measured.arc_radius_disagreement_mm < 0.002
    assert measured.minimum_mm[0] <= 0.75 - measured.arc_radius_disagreement_mm


def test_finite_inputs_that_overflow_geometry_cannot_return_infinite_evidence():
    with pytest.raises(ValueError):
        path(start_mm=(1e308, 1e308, 0.2), end_mm=(-1e308, -1e308, 0.2)).measure()


def test_arc_with_numerically_collapsed_distinct_endpoints_is_rejected():
    with pytest.raises(ValueError, match="angular resolution"):
        path(center_xy_mm=(1e30, 1e30)).measure()
