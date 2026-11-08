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


def section_circle(radius=2.7, midpoint=False):
    import math

    points = [
        (4.0, 10 + radius * math.cos(i * math.tau / 48), 20 + radius * math.sin(i * math.tau / 48))
        for i in range(48)
    ]
    if midpoint:
        points = [
            p
            for i, a in enumerate(points)
            for p in (a, tuple((a[j] + points[(i + 1) % 48][j]) / 2 for j in range(3)))
        ]
    return {"closed": True, "points_mm": points}


@pytest.mark.parametrize("midpoint", [False, True])
def test_section_circle_measures_actual_polygon_clearance_without_changing_input(midpoint):
    import copy
    import math

    from src.verification.mesh_measurements import measure_section_circle

    section = section_circle(midpoint=midpoint)
    before = copy.deepcopy(section)
    result = measure_section_circle(section)
    assert result is not None
    assert result.center_mm == pytest.approx((4, 10, 20), abs=1e-10)
    assert result.radius_mm == pytest.approx(2.7)
    assert result.minimum_radius_mm == pytest.approx(2.7 * math.cos(math.pi / 48))
    assert result.corner_count == 48
    assert section == before


@pytest.mark.parametrize("fault", ["open", "nan", "degenerate", "overflow"])
def test_invalid_section_cannot_yield_circle_evidence(fault):
    from src.verification.mesh_measurements import measure_section_circle

    section = section_circle()
    if fault == "open":
        section["closed"] = False
    if fault == "nan":
        section["points_mm"][0] = (float("nan"), 0, 0)
    if fault == "degenerate":
        section["points_mm"] = [(0, 0, 0), (1, 0, 0), (2, 0, 0)]
    if fault == "overflow":
        section["points_mm"][0] = (1e308, -1e308, 1e308)
    with pytest.raises(ValueError):
        measure_section_circle(section)


@pytest.mark.parametrize("fault", ["oval", "nonplanar"])
def test_non_circular_or_nonplanar_closed_section_is_not_a_round_bore(fault):
    from src.verification.mesh_measurements import measure_section_circle

    section = section_circle()
    p = section["points_mm"][7]
    section["points_mm"][7] = (
        p[0] + (0.02 if fault == "nonplanar" else 0),
        p[1] + (0.02 if fault == "oval" else 0),
        p[2],
    )
    assert measure_section_circle(section) is None


def test_exact_zero_length_observation_edge_is_counted_without_merging_distinct_points():
    from src.verification.mesh_measurements import measure_section_circle

    section = section_circle()
    section["points_mm"].insert(7, section["points_mm"][7])
    measured = measure_section_circle(section)
    assert measured is not None and measured.exact_duplicates_removed == 1
    assert measured.radius_mm == pytest.approx(2.7)


def test_nonconsecutive_repeat_is_not_repaired_into_a_circle():
    from src.verification.mesh_measurements import measure_section_circle

    section = section_circle()
    section["points_mm"][10] = section["points_mm"][4]
    with pytest.raises(ValueError):
        measure_section_circle(section)
