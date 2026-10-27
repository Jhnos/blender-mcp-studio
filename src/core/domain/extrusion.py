"""Declared deposition geometry, independent of G-code, files, printers and solvers.

These are software envelopes of the commanded bead, not measured adhesion or nozzle contact.
Arc radius disagreement is bounded by the adapter's declared coordinate encoding tolerance.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, hypot, isfinite, pi, sin, tau

Point = tuple[float, float, float]


def _finite(values: tuple[float, ...]) -> bool:
    return all(type(value) in (int, float) and isfinite(value) for value in values)


@dataclass(frozen=True, slots=True)
class ExtrusionMetrics:
    minimum_mm: Point
    maximum_mm: Point
    xy_length_mm: float
    arc_radius_disagreement_mm: float = 0.0


@dataclass(frozen=True, slots=True)
class ExtrusionPath:
    start_mm: Point
    end_mm: Point
    width_mm: float
    height_mm: float
    role: str
    layer_index: int
    center_xy_mm: tuple[float, float] | None = None
    clockwise: bool = False
    coordinate_tolerance_mm: float = 0.002
    object_id: int | None = None

    def __post_init__(self) -> None:
        if (
            len(self.start_mm) != 3
            or len(self.end_mm) != 3
            or not _finite((*self.start_mm, *self.end_mm))
        ):
            raise ValueError("extrusion endpoints must contain three finite coordinates")
        if (
            not _finite((self.width_mm, self.height_mm, self.coordinate_tolerance_mm))
            or min(self.width_mm, self.height_mm, self.coordinate_tolerance_mm) <= 0
        ):
            raise ValueError("extrusion width, height and encoding tolerance must be positive")
        if (
            not isinstance(self.role, str)
            or not 0 < len(self.role) <= 128
            or type(self.layer_index) is not int
            or self.layer_index < 0
        ):
            raise ValueError("extrusion requires a bounded feature name and declared layer")
        if self.center_xy_mm is not None and (
            len(self.center_xy_mm) != 2 or not _finite(self.center_xy_mm)
        ):
            raise ValueError("arc center must contain two finite coordinates")

        if self.object_id is not None and (type(self.object_id) is not int or self.object_id < 0):
            raise ValueError("extrusion object identity must be a nonnegative integer")

    def measure(self) -> ExtrusionMetrics:
        xs, ys = [self.start_mm[0], self.end_mm[0]], [self.start_mm[1], self.end_mm[1]]
        length = hypot(xs[1] - xs[0], ys[1] - ys[0])
        disagreement = 0.0
        if self.center_xy_mm is not None:
            cx, cy = self.center_xy_mm
            radius = hypot(xs[0] - cx, ys[0] - cy)
            end_radius = hypot(xs[1] - cx, ys[1] - cy)
            disagreement = abs(radius - end_radius)
            if radius <= 0 or disagreement > self.coordinate_tolerance_mm:
                raise ValueError("arc endpoints do not share the declared center radius")
            start, end = atan2(ys[0] - cy, xs[0] - cx), atan2(ys[1] - cy, xs[1] - cx)
            direction = -1 if self.clockwise else 1
            sweep = ((end - start) * direction) % tau
            if self.start_mm[:2] == self.end_mm[:2]:
                sweep = tau
            elif sweep == 0:
                raise ValueError("arc endpoints exceed finite angular resolution")
            envelope_radius = max(radius, end_radius)
            for angle in (0, pi / 2, pi, 3 * pi / 2):
                if ((angle - start) * direction) % tau <= sweep + 1e-12:
                    xs.append(cx + envelope_radius * cos(angle))
                    ys.append(cy + envelope_radius * sin(angle))
            length = envelope_radius * sweep
        half_width = self.width_mm / 2 + disagreement
        result = ExtrusionMetrics(
            (
                min(xs) - half_width,
                min(ys) - half_width,
                min(self.start_mm[2], self.end_mm[2]) - self.height_mm,
            ),
            (max(xs) + half_width, max(ys) + half_width, max(self.start_mm[2], self.end_mm[2])),
            length,
            disagreement,
        )
        if not _finite(
            (
                *result.minimum_mm,
                *result.maximum_mm,
                result.xy_length_mm,
                result.arc_radius_disagreement_mm,
            )
        ):
            raise ValueError("extrusion geometry exceeds finite numerical range")
        return result


@dataclass(frozen=True, slots=True)
class BuildVolume:
    minimum_mm: Point
    maximum_mm: Point

    def __post_init__(self) -> None:
        if (
            len(self.minimum_mm) != 3
            or len(self.maximum_mm) != 3
            or not _finite((*self.minimum_mm, *self.maximum_mm))
            or any(low >= high for low, high in zip(self.minimum_mm, self.maximum_mm, strict=True))
        ):
            raise ValueError("build volume requires three finite positive dimensions")


@dataclass(frozen=True, slots=True)
class ExtrusionRoleStats:
    role: str
    paths: int
    xy_length_mm: float
    bed_contact_paths: int


@dataclass(frozen=True, slots=True)
class ExtrusionObjectStats:
    object_id: int
    paths: int
    bed_contact_paths: int


@dataclass(frozen=True, slots=True)
class ExtrusionInspection:
    path_count: int
    outside_paths: int
    minimum_mm: Point | None
    maximum_mm: Point | None
    bed_contact_paths: int
    roles: tuple[ExtrusionRoleStats, ...]
    maximum_arc_radius_disagreement_mm: float
    violations: tuple[str, ...]
    objects: tuple[ExtrusionObjectStats, ...] = ()
    unassigned_paths: int = 0

    @property
    def passed(self) -> bool:
        return self.path_count > 0 and not self.violations

    @property
    def support_paths(self) -> int:
        return sum(role.paths for role in self.roles if role.role.startswith("Support"))

    @property
    def brim_paths(self) -> int:
        return sum(role.paths for role in self.roles if role.role == "Brim")

    @property
    def bed_support_paths(self) -> int:
        return sum(role.bed_contact_paths for role in self.roles if role.role.startswith("Support"))

    @property
    def bed_brim_paths(self) -> int:
        return sum(role.bed_contact_paths for role in self.roles if role.role == "Brim")
