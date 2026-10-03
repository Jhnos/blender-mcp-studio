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


def test_chain_samples_all_segments_with_shared_join_and_length() -> None:
    from src.core.planning.cable_path_plan import sample_chain

    first = candidates(boundary(), RouteSearchSpec(candidate_count=8))[0]
    second = candidates(
        replace(
            boundary(),
            name="second",
            start_mm=(60, 0, 0),
            end_mm=(120, 0, 0),
            start_direction=(0, 0, -1),
            end_direction=(0, 0, 1),
        ),
        RouteSearchSpec(candidate_count=8),
    )[0]
    joined = sample_chain((first, second))
    assert joined.points_mm[0] == first.boundary.start_mm
    assert joined.points_mm[-1] == second.boundary.end_mm
    assert joined.length_lower_mm == pytest.approx(300, abs=0.05)
    assert joined.points_mm.count(first.boundary.end_mm) == 1
    with pytest.raises(ValueError, match="radius"):
        sample_chain((first, replace(second, boundary=replace(second.boundary, cable_radius_mm=4))))
    with pytest.raises(ValueError, match="join"):
        sample_chain((second, first))
    with pytest.raises(ValueError, match="empty"):
        sample_chain(())


def test_continuation_retains_family_and_rejects_identity_or_length_changes() -> None:
    from src.core.planning.cable_path_plan import continue_route

    original = candidates(boundary(), RouteSearchSpec(candidate_count=8))[0]
    assert continue_route(original, original.boundary) == original
    moved = replace(original.boundary, end_mm=(60, 1, 1))
    continued = continue_route(original, moved)
    assert continued is not None
    assert continued.parameters_mm[:4] == original.parameters_mm[:4]
    assert continued.parameters_mm[4] * original.parameters_mm[4] > 0
    measured = sample_path(continued.curves)
    assert measured.points_mm[-1] == moved.end_mm
    assert measured.length_lower_mm == pytest.approx(original.boundary.length_mm, abs=0.05)
    for changed in (
        replace(moved, name="other"),
        replace(moved, length_mm=160),
        replace(moved, cable_radius_mm=4),
        replace(moved, lead_mm=7),
    ):
        with pytest.raises(ValueError, match="same cable"):
            continue_route(original, changed)


def test_continuation_keeps_bend_constraint_and_fails_without_a_length_solution() -> None:
    from src.core.planning.cable_path_plan import continue_route

    original = candidates(boundary(), RouteSearchSpec(candidate_count=8))[0]
    assert continue_route(original, original.boundary, minimum_sampled_radius_mm=1000) is None
    assert continue_route(original, replace(original.boundary, end_mm=(149, 0, 0))) is None
    for invalid in (-1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="radius"):
            continue_route(original, original.boundary, minimum_sampled_radius_mm=invalid)
