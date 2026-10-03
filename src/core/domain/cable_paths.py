"""Framework-free cubic paths and conservative polyline inspection envelopes, in mm."""

from dataclasses import dataclass
from math import dist, isfinite, sqrt

from src.core.domain.lab_station import Point


def add(a: Point, b: Point) -> Point:
    return a[0] + b[0], a[1] + b[1], a[2] + b[2]


def scale(a: Point, value: float) -> Point:
    return a[0] * value, a[1] * value, a[2] * value


def subtract(a: Point, b: Point) -> Point:
    return add(a, scale(b, -1))


def dot(a: Point, b: Point) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def cross(a: Point, b: Point) -> Point:
    return a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]


def unit(a: Point) -> Point:
    length = sqrt(dot(a, a))
    if not isfinite(length) or length < 1e-12:
        raise ValueError("Direction must be finite and nonzero")
    return scale(a, 1 / length)


def mix(a: Point, b: Point, t: float) -> Point:
    return add(scale(a, 1 - t), scale(b, t))


def segment_distance(point: Point, a: Point, b: Point) -> float:
    chord = subtract(b, a)
    squared = dot(chord, chord)
    t = min(1, max(0, dot(subtract(point, a), chord) / squared)) if squared else 0
    return dist(point, mix(a, b, t))


@dataclass(frozen=True, slots=True)
class CubicPath:
    controls_mm: tuple[Point, Point, Point, Point]

    def __post_init__(self) -> None:
        if len(self.controls_mm) != 4 or any(
            len(p) != 3 or not all(isfinite(v) for v in p) for p in self.controls_mm
        ):
            raise ValueError("Cubic controls must be four finite 3D points")

    def point(self, t: float) -> Point:
        if not isfinite(t) or not 0 <= t <= 1:
            raise ValueError("Curve parameter must be within [0, 1]")
        a, b, c, d = self.controls_mm
        s = 1 - t
        return add(
            add(scale(a, s**3), scale(b, 3 * s * s * t)),
            add(scale(c, 3 * s * t * t), scale(d, t**3)),
        )

    def tangent(self, t: float) -> Point:
        if not isfinite(t) or not 0 <= t <= 1:
            raise ValueError("Curve parameter must be within [0, 1]")
        a, b, c, d = self.controls_mm
        return add(
            add(scale(subtract(b, a), 3 * (1 - t) ** 2), scale(subtract(c, b), 6 * (1 - t) * t)),
            scale(subtract(d, c), 3 * t * t),
        )

    def curvature(self, t: float) -> float:
        a, b, c, d = self.controls_mm
        first = self.tangent(t)
        second = scale(
            mix(add(subtract(c, scale(b, 2)), a), add(subtract(d, scale(c, 2)), b), t), 6
        )
        speed = sqrt(dot(first, first))
        if speed < 1e-12:
            raise ValueError("Curve has a singular tangent")
        numerator = cross(first, second)
        return sqrt(dot(numerator, numerator)) / speed**3

    def split(self) -> tuple["CubicPath", "CubicPath"]:
        a, b, c, d = self.controls_mm
        ab, bc, cd = mix(a, b, 0.5), mix(b, c, 0.5), mix(c, d, 0.5)
        abc, bcd = mix(ab, bc, 0.5), mix(bc, cd, 0.5)
        middle = mix(abc, bcd, 0.5)
        return CubicPath((a, ab, abc, middle)), CubicPath((middle, bcd, cd, d))


@dataclass(frozen=True, slots=True)
class SampledPath:
    points_mm: tuple[Point, ...]
    length_lower_mm: float
    length_upper_mm: float
    max_step_mm: float
    deviation_mm: float

    def inspection_radius_mm(self, cable_radius_mm: float) -> float:
        if not isfinite(cable_radius_mm) or cable_radius_mm <= 0:
            raise ValueError("Cable radius must be finite and positive")
        return cable_radius_mm + self.max_step_mm / 2 + self.deviation_mm


def sample_path(
    curves: tuple[CubicPath, ...], *, step_mm: float = 0.15, deviation_mm: float = 0.01
) -> SampledPath:
    """Convex-hull bounds cover unsampled curve positions; length remains an interval."""
    if not curves or not all(isfinite(v) and v > 0 for v in (step_mm, deviation_mm)):
        raise ValueError("Path and finite positive sampling tolerances are required")
    for first, second in zip(curves, curves[1:], strict=False):
        if dist(first.controls_mm[-1], second.controls_mm[0]) > 1e-8:
            raise ValueError("Disconnected path join")
        if dot(unit(first.tangent(1)), unit(second.tangent(0))) < 1 - 1e-8:
            raise ValueError("Discontinuous path tangent")
    points = [curves[0].controls_mm[0]]
    lower = upper = largest_step = deviation = 0.0
    pending = [(curve, 0) for curve in reversed(curves)]
    while pending:
        curve, depth = pending.pop()
        a, b, c, d = curve.controls_mm
        chord = dist(a, d)
        flatness = max(segment_distance(b, a, d), segment_distance(c, a, d))
        if chord > step_mm or flatness > deviation_mm:
            if depth >= 24:
                raise ValueError("Curve subdivision exhausted its bounded depth")
            left, right = curve.split()
            pending.extend(((right, depth + 1), (left, depth + 1)))
            continue
        points.append(d)
        lower += chord
        upper += dist(a, b) + dist(b, c) + dist(c, d)
        largest_step = max(largest_step, chord)
        deviation = max(deviation, flatness)
        if len(points) > 100000:
            raise ValueError("Curve sampling exceeds its point budget")
    return SampledPath(tuple(points), lower, upper, largest_step, deviation)
