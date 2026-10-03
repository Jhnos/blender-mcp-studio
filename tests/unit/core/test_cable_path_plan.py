"""One planner accepts route data for any head; it has no Blender dependencies."""

from dataclasses import replace
from math import dist

import pytest

from src.core.domain.cable_paths import sample_path
from src.core.planning.cable_path_plan import RouteBoundary, RouteSearchSpec, candidates


def boundary() -> RouteBoundary:
    return RouteBoundary("example", (0, 0, 0), (60, 0, 0), (0, 0, 1), (0, 0, -1), 150)


def test_one_planner_keeps_terminals_leads_and_target_length() -> None:
    rows = candidates(boundary(), RouteSearchSpec(candidate_count=8))
    assert rows
    path = rows[0]
    measured = sample_path(path.curves)
    assert measured.points_mm[0] == (0, 0, 0)
    assert measured.points_mm[-1] == (60, 0, 0)
    assert dist(path.curves[0].controls_mm[0], path.curves[0].controls_mm[-1]) == 6
    assert abs((measured.length_lower_mm + measured.length_upper_mm) / 2 - 150) < 0.05
    assert candidates(boundary(), RouteSearchSpec(candidate_count=8)) == rows


def test_parallel_terminal_directions_do_not_produce_nan_normal() -> None:
    request = replace(boundary(), end_direction=(0, 0, 1))
    assert candidates(request, RouteSearchSpec(candidate_count=8))


@pytest.mark.parametrize(
    "change",
    [
        dict(length_mm=10),
        dict(cable_radius_mm=0),
        dict(start_direction=(0, 0, 0)),
        dict(length_mm=float("nan")),
    ],
)
def test_invalid_boundaries_are_rejected_before_search(change: dict[str, object]) -> None:
    with pytest.raises((ValueError, TypeError)):
        replace(boundary(), **change)


def test_required_bend_radius_is_a_constraint_not_a_render_setting() -> None:
    assert not candidates(
        boundary(), RouteSearchSpec(candidate_count=8, minimum_sampled_radius_mm=1000)
    )


def test_geometry_inspection_can_reach_beyond_twelve_smooth_candidates() -> None:
    assert len(candidates(boundary(), RouteSearchSpec(candidate_count=256))) > 24
