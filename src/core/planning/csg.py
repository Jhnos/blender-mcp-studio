"""The solids a plan is allowed to ask for, and nothing about how to make them.

An executor turns each of these into one primitive call and one Boolean. The
vocabulary is deliberately small: a box, a cylinder about one axis, an
ellipsoid, and a box with a box taken out of it. Anything a hand needs that is
not one of those is a plan-level composition of them, in a stated order.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.domain.rotation import Axis3


@dataclass(frozen=True, slots=True)
class Box:
    name: str
    size_mm: Axis3
    center_mm: Axis3


@dataclass(frozen=True, slots=True)
class Cylinder:
    name: str
    radius_mm: float
    height_mm: float
    center_mm: Axis3
    axis: str = "Z"
    #: Facets round the circumference; None takes the primitive's default.
    #: Bores ask for fewer, because the readiness check has a triangle budget.
    segments: int | None = None


@dataclass(frozen=True, slots=True)
class Ellipsoid:
    name: str
    size_mm: Axis3
    center_mm: Axis3


@dataclass(frozen=True, slots=True)
class HollowBox:
    """`outer` with `inner` removed: a band, a groove, a frame."""

    name: str
    outer: Box
    inner: Box


Solid = Box | Cylinder | Ellipsoid | HollowBox


@dataclass(frozen=True, slots=True)
class Operation:
    #: `UNION` adds the solid to the body, `DIFFERENCE` cuts it out.
    mode: str
    solid: Solid


def union(solid: Solid) -> Operation:
    return Operation("UNION", solid)


def difference(solid: Solid) -> Operation:
    return Operation("DIFFERENCE", solid)
