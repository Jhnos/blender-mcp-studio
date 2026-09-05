"""Measured evidence must match independent limits, never merely be present."""

import pytest

from src.verification.mesh_measurements import measurements_pass


def test_measured_dimensions_holes_slopes_and_hardware_are_all_required() -> None:
    limits = {
        "dimensions_mm": [34, 34, 29.6],
        "radius_mm": 17,
        "slope_angles_deg": [38.66, 34.99],
        "hole_ray_count": 45,
        "hardware_count": 16,
        "hardware_inner_radius_mm": 5.3,
        "hardware_pair_count": 144,
    }
    evidence = {
        "dimensions_mm": [34, 34, 29.6],
        "radius_mm": 17,
        "slope_angles_deg": [38.66, 34.99],
        "hole_hits": [False] * 45,
        "hardware_count": 16,
        "hardware_inner_radius_mm": 5.8,
        "hardware_outer_radius_mm": 15.3,
        "hardware_overlaps": [0] * 144,
    }
    assert measurements_pass(evidence, limits)
    for field in evidence:
        missing = dict(evidence)
        del missing[field]
        assert not measurements_pass(missing, limits), field
    for field, wrong in (
        ("dimensions_mm", [34000, 34000, 29600]),
        ("radius_mm", 17.2),
        ("slope_angles_deg", [90, 35]),
        ("slope_angles_deg", [float("nan"), 35]),
        ("hole_hits", [True] + [False] * 44),
        ("hardware_count", 0),
        ("hardware_overlaps", [0] * 143),
        ("hardware_overlaps", [1] + [0] * 143),
        ("hardware_inner_radius_mm", 4.9),
        ("hardware_outer_radius_mm", 17.2),
    ):
        assert not measurements_pass({**evidence, field: wrong}, limits), field


@pytest.mark.parametrize("bad", [None, [], {}, {"dimensions_mm": []}])
def test_empty_measurements_fail_closed(bad: object) -> None:
    assert not measurements_pass(bad, {})
