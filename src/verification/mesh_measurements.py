"""Fail-closed assessment of measured meshes against independent numeric limits."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from src.infrastructure.narrowing import (
    as_finite_number,
    as_nonempty_sequence,
    as_str_keyed_exact,
    required,
)


def _mapping(value: object) -> Mapping[str, object]:
    return required(
        value,
        as_str_keyed_exact,
        message="measurement must be a string-keyed object",
        error=ValueError,
    )


def _number(value: object) -> float:
    return required(value, as_finite_number, message="measurement must be finite", error=ValueError)


def _array(value: object) -> tuple[object, ...]:
    return tuple(
        required(
            value,
            as_nonempty_sequence,
            message="measurement array must not be empty",
            error=ValueError,
        )
    )


def _near(actual: object, expected: object, tolerance: float) -> bool:
    values, targets = _array(actual), _array(expected)
    return len(values) == len(targets) and all(
        abs(_number(value) - _number(target)) <= tolerance
        for value, target in zip(values, targets, strict=True)
    )


def _retention_pass(measured: Mapping[str, object], expected: Mapping[str, object]) -> bool:
    if "retention_sample_count" not in expected:
        return True
    counts = _array(measured["retention_overlaps"])
    return len(counts) == _number(expected["retention_sample_count"]) and all(
        type(count) is int and count > 0 for count in counts
    )


def measurements_pass(evidence: object, limits: object) -> bool:
    """No partial report may imply that dimensions, holes, ramps or pins passed."""
    try:
        measured, expected = _mapping(evidence), _mapping(limits)
        hole_hits = _array(measured["hole_hits"])
        overlaps = _array(measured["hardware_overlaps"])
        radius = _number(expected["radius_mm"])
        return (
            _near(measured["dimensions_mm"], expected["dimensions_mm"], 0.01)
            and _number(measured["radius_mm"]) <= radius + 0.001
            and _near(measured["slope_angles_deg"], expected["slope_angles_deg"], 0.1)
            and len(hole_hits) == _number(expected["hole_ray_count"])
            and all(hit is False for hit in hole_hits)
            and _number(measured["hardware_count"]) == _number(expected["hardware_count"])
            and _number(measured["hardware_inner_radius_mm"])
            >= _number(expected["hardware_inner_radius_mm"])
            and _number(measured["hardware_outer_radius_mm"]) <= radius + 0.001
            and len(overlaps) == _number(expected["hardware_pair_count"])
            and all(type(count) is int and count == 0 for count in overlaps)
            and _retention_pass(measured, expected)
        )
    except (KeyError, ValueError, TypeError):
        # Explicit negative verdict is the verifier's failure result, not a fallback pass.
        return False


@dataclass(frozen=True, slots=True)
class SectionCircle:
    center_mm: tuple[float, float, float]
    radius_mm: float
    minimum_radius_mm: float
    maximum_corner_residual_mm: float
    corner_count: int
    exact_duplicates_removed: int


def _point3(value: object) -> tuple[float, float, float]:
    row = _array(value)
    if len(row) != 3:
        raise ValueError("section points require three finite coordinates")
    return _number(row[0]), _number(row[1]), _number(row[2])


def _segment_distance(
    point: tuple[float, float, float],
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> tuple[float, bool]:
    direction = tuple(b - a for a, b in zip(start, end, strict=True))
    length = math.hypot(*direction)
    if not math.isfinite(length) or length == 0:
        raise ValueError("section has a degenerate or unresolved edge")
    unit = tuple(v / length for v in direction)
    distance = sum((p - a) * v for p, a, v in zip(point, start, unit, strict=True))
    if not math.isfinite(distance):
        raise ValueError("section geometry exceeds finite numerical range")
    along = min(length, max(0.0, distance))
    closest = tuple(a + along * v for a, v in zip(start, unit, strict=True))
    return math.dist(point, closest), 0 < distance < length


def measure_section_circle(
    section: object, *, numerical_tolerance_mm: float = 0.0001
) -> SectionCircle | None:
    """Fit corner vertices, but measure clearance against the original closed polygon.

    The numerical resolution only removes collinear subdivision points from the fit;
    no source mesh or clearance polygon changes. A fitted radius is not the minimum
    pin clearance, manufacturing tolerance, hole roundness or assembly acceptance.
    """
    from trimesh.path.arc import arc_center

    tolerance = _number(numerical_tolerance_mm)
    value = _mapping(section)
    if tolerance <= 0 or value.get("closed") is not True:
        raise ValueError("circle measurement requires positive resolution and a closed section")
    observations = [_point3(p) for p in _array(value.get("points_mm"))]
    if len(observations) > 4096:
        raise ValueError("section exceeds its point budget")
    points: list[tuple[float, float, float]] = []
    for point in observations:
        if not points or point != points[-1]:
            points.append(point)
    if points[0] == points[-1]:
        points.pop()
    if len(points) < 3 or len(set(points)) != len(points):
        raise ValueError("section points must be distinct and nondegenerate")
    origin = points[0]
    extent = max(math.dist(origin, p) for p in points)
    if not math.isfinite(extent) or not math.isfinite(extent * extent) or extent <= tolerance * 2:
        raise ValueError("section exceeds finite fitting range or numerical resolution")
    corners = points[:]
    while True:
        keep = []
        for index, point in enumerate(corners):
            distance, interior = _segment_distance(
                point, corners[index - 1], corners[(index + 1) % len(corners)]
            )
            if not interior or distance > tolerance:
                keep.append(point)
        if len(keep) < 3:
            raise ValueError("section collapsed at the declared numerical resolution")
        if len(keep) == len(corners):
            break
        corners = keep
    normalized = [tuple((p[j] - origin[j]) / extent for j in range(3)) for p in corners]
    three = [normalized[i] for i in (0, len(corners) // 3, 2 * len(corners) // 3)]
    try:
        fitted = arc_center(three, return_normal=True, return_angle=False)
    except Exception as exc:
        raise ValueError("circle fit could not be evaluated") from exc
    raw_center: object = fitted.center.tolist()
    raw_normal: object = fitted.normal.tolist() if fitted.normal is not None else None
    local, normal = _point3(raw_center), _point3(raw_normal)
    center = tuple(_number(origin[i] + local[i] * extent) for i in range(3))
    center3 = center[0], center[1], center[2]
    radius = _number(float(fitted.radius) * extent)
    if radius <= tolerance:
        raise ValueError("circle radius is unresolved at the declared numerical resolution")
    residual = max(abs(math.dist(p, center3) - radius) for p in corners)
    nonplanar = max(abs(sum((p[j] - center3[j]) * normal[j] for j in range(3))) for p in points)
    if residual > tolerance or nonplanar > tolerance:
        return None
    minimum = min(
        _segment_distance(center3, p, points[(i + 1) % len(points)])[0]
        for i, p in enumerate(points)
    )
    return SectionCircle(
        center3, radius, minimum, residual, len(corners), len(observations) - len(points)
    )
