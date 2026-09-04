"""Fail-closed assessment of measured meshes against independent numeric limits."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import cast


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise ValueError("measurement must be a string-keyed object")
    return cast(Mapping[str, object], value)


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("measurement must be finite")
    return float(value)


def _array(value: object) -> tuple[object, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ValueError("measurement array must not be empty")
    return tuple(value)


def _near(actual: object, expected: object, tolerance: float) -> bool:
    values, targets = _array(actual), _array(expected)
    return len(values) == len(targets) and all(
        abs(_number(value) - _number(target)) <= tolerance
        for value, target in zip(values, targets, strict=True)
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
        )
    except (KeyError, ValueError, TypeError):
        # Explicit negative verdict is the verifier's failure result, not a fallback pass.
        return False
