"""Deterministic two-cubic route candidates; geometry and material qualification are separate."""

from dataclasses import dataclass
from math import dist, isfinite
from random import Random

from src.core.domain.cable_paths import (
    CubicPath,
    SampledPath,
    add,
    cross,
    dot,
    mix,
    sample_path,
    scale,
    subtract,
    unit,
)
from src.core.domain.lab_station import Point


@dataclass(frozen=True, slots=True)
class RouteBoundary:
    name: str
    start_mm: Point
    end_mm: Point
    start_direction: Point
    end_direction: Point
    length_mm: float
    cable_radius_mm: float = 3.0
    lead_mm: float = 6.0

    def __post_init__(self) -> None:
        vectors = (self.start_mm, self.end_mm, self.start_direction, self.end_direction)
        if not self.name or any(len(p) != 3 or not all(isfinite(v) for v in p) for p in vectors):
            raise ValueError("Route requires a name and finite 3D endpoints/directions")
        if not all(
            isfinite(v) and v > 0 for v in (self.length_mm, self.cable_radius_mm, self.lead_mm)
        ):
            raise ValueError("Route dimensions must be finite and positive")
        if self.length_mm <= max(dist(self.start_mm, self.end_mm), 2 * self.lead_mm):
            raise ValueError("Route length leaves no bend allowance")
        unit(self.start_direction)
        unit(self.end_direction)


@dataclass(frozen=True, slots=True)
class RouteSearchSpec:
    candidate_count: int = 128
    seed: int = 603
    minimum_sampled_radius_mm: float = 0
    handle_range_mm: tuple[float, float] = (12, 90)
    middle_range_mm: tuple[float, float] = (5, 100)

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_count, int) or not 1 <= self.candidate_count <= 2048:
            raise ValueError("Candidate count must be within 1–2048")
        if not isfinite(self.minimum_sampled_radius_mm) or self.minimum_sampled_radius_mm < 0:
            raise ValueError("Minimum sampled radius must be finite and nonnegative")
        for low, high in (self.handle_range_mm, self.middle_range_mm):
            if not all(isfinite(v) for v in (low, high)) or not 0 < low <= high:
                raise ValueError("Search ranges must be positive and ordered")


@dataclass(frozen=True, slots=True)
class RouteCandidate:
    boundary: RouteBoundary
    curves: tuple[CubicPath, ...]
    parameters_mm: tuple[float, float, float, float, float]
    estimated_length_mm: float
    sampled_min_radius_mm: float


def sample_chain(segments: tuple[RouteCandidate, ...]) -> SampledPath:
    """One wire keeps a uniform radius and connected, co-directed segment joins."""
    if not segments:
        raise ValueError("Cable chain cannot be empty")
    radius = segments[0].boundary.cable_radius_mm
    if any(segment.boundary.cable_radius_mm != radius for segment in segments):
        raise ValueError("Cable chain radius must be uniform")
    return sample_path(tuple(curve for segment in segments for curve in segment.curves))


def straight(a: Point, b: Point) -> CubicPath:
    return CubicPath((a, mix(a, b, 1 / 3), mix(a, b, 2 / 3), b))


def loop_curves(
    request: RouteBoundary, handles: tuple[float, float, float, float], bulge: float
) -> tuple[CubicPath, CubicPath]:
    u, v = unit(request.start_direction), unit(request.end_direction)
    a = add(request.start_mm, scale(u, request.lead_mm))
    b = subtract(request.end_mm, scale(v, request.lead_mm))
    w = unit(subtract(b, a))
    normal = cross(u, v)
    if dot(normal, normal) < 1e-12:
        axis = min(
            ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)), key=lambda p: abs(dot(p, u))
        )
        normal = cross(u, axis)
    normal = unit(normal)
    elbow = subtract(u, v)
    elbow = unit(elbow if dot(elbow, elbow) > 1e-12 else cross(normal, u))
    first, last, middle_handle, offset = handles
    middle = add(add(mix(a, b, 0.5), scale(elbow, offset)), scale(normal, bulge))
    return (
        CubicPath((a, add(a, scale(u, first)), subtract(middle, scale(w, middle_handle)), middle)),
        CubicPath((middle, add(middle, scale(w, middle_handle)), subtract(b, scale(v, last)), b)),
    )


def estimated_length(curves: tuple[CubicPath, ...], samples: int) -> float:
    total = 0.0
    for curve in curves:
        previous = curve.point(0)
        for step in range(1, samples + 1):
            point = curve.point(step / samples)
            total += dist(previous, point)
            previous = point
    return total


def candidates(
    request: RouteBoundary, search: RouteSearchSpec | None = None
) -> tuple[RouteCandidate, ...]:
    """Keep every feasible sampled candidate, so smoothness ranking cannot hide obstacle-free paths."""
    search = search or RouteSearchSpec()
    rng = Random(search.seed)
    result = []
    target = request.length_mm - 2 * request.lead_mm
    for _ in range(search.candidate_count):
        handles = (
            rng.uniform(*search.handle_range_mm),
            rng.uniform(*search.handle_range_mm),
            rng.uniform(*search.handle_range_mm),
            rng.uniform(*search.middle_range_mm),
        )
        for sign in (-1, 1):
            lo, hi = 0.0, request.length_mm
            if estimated_length(loop_curves(request, handles, 0), 32) > target:
                continue
            for _ in range(20):
                mid = (lo + hi) / 2
                if estimated_length(loop_curves(request, handles, sign * mid), 32) < target:
                    lo = mid
                else:
                    hi = mid
            lo, hi = max(0, lo - 2), hi + 2
            for _ in range(14):
                mid = (lo + hi) / 2
                if estimated_length(loop_curves(request, handles, sign * mid), 128) < target:
                    lo = mid
                else:
                    hi = mid
            bulge = sign * (lo + hi) / 2
            curves = loop_curves(request, handles, bulge)
            length = estimated_length(curves, 256) + 2 * request.lead_mm
            if abs(length - request.length_mm) > 0.05:
                continue
            try:
                maximum_curvature = max(
                    curve.curvature(i / 128) for curve in curves for i in range(129)
                )
            except ValueError:
                continue
            if maximum_curvature < 1e-12 or 1 / maximum_curvature < max(
                search.minimum_sampled_radius_mm, request.cable_radius_mm
            ):
                continue
            path = (
                straight(request.start_mm, curves[0].controls_mm[0]),
                *curves,
                straight(curves[-1].controls_mm[-1], request.end_mm),
            )
            result.append(
                RouteCandidate(request, path, (*handles, bulge), length, 1 / maximum_curvature)
            )
    return tuple(sorted(result, key=lambda row: -row.sampled_min_radius_mm))
