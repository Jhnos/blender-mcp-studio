"""Immutable values for incremental multi-object transforms."""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real

from src.core.domain.exceptions import BatchTransformError
from src.core.domain.scene_operations import Vector3

MAX_BATCH_OBJECTS = 100
MAX_TRANSLATION_MM = 100_000.0
MAX_ROTATION_DEG = 3_600.0
MAX_SCALE_PERCENT = 10_000.0


def _components(vector: Vector3) -> tuple[float, float, float]:
    values = (vector.x, vector.y, vector.z)
    if any(isinstance(value, bool) or not isinstance(value, Real) for value in values):
        raise BatchTransformError("Transform values must be finite numbers")
    numbers = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in numbers):
        raise BatchTransformError("Transform values must be finite numbers")
    return numbers[0], numbers[1], numbers[2]


def _validate_symmetric_limit(values: tuple[float, float, float], limit: float, label: str) -> None:
    if any(abs(value) > limit for value in values):
        raise BatchTransformError(f"{label} must be within +/-{limit:g}")


@dataclass(frozen=True, slots=True)
class TransformDelta:
    """Incremental transform values in WebUI-facing print units."""

    translation_mm: Vector3 = Vector3()
    rotation_deg: Vector3 = Vector3()
    scale_percent: Vector3 = Vector3()

    def __post_init__(self) -> None:
        translation = _components(self.translation_mm)
        rotation = _components(self.rotation_deg)
        scale = _components(self.scale_percent)
        _validate_symmetric_limit(translation, MAX_TRANSLATION_MM, "Translation mm")
        _validate_symmetric_limit(rotation, MAX_ROTATION_DEG, "Rotation degrees")
        if any(value <= -100.0 for value in scale):
            raise BatchTransformError("Scale percent must be greater than -100")
        if any(value > MAX_SCALE_PERCENT for value in scale):
            raise BatchTransformError(
                f"Scale percent must be no greater than {MAX_SCALE_PERCENT:g}"
            )

    @property
    def is_zero(self) -> bool:
        return not any(
            value
            for vector in (self.translation_mm, self.rotation_deg, self.scale_percent)
            for value in _components(vector)
        )


@dataclass(frozen=True, slots=True)
class BatchTransformSpec:
    """Complete target set and one incremental transform transaction."""

    object_names: tuple[str, ...]
    delta: TransformDelta

    def __post_init__(self) -> None:
        if not isinstance(
            self.object_names, tuple
        ):  # narrow-ok: invariant check on this dataclass's own declared field, not external data
            raise BatchTransformError("Object names must be an immutable tuple")
        if not self.object_names:
            raise BatchTransformError("Batch transform requires at least one object")
        if len(self.object_names) > MAX_BATCH_OBJECTS:
            raise BatchTransformError(
                f"Batch transform accepts at most {MAX_BATCH_OBJECTS} objects"
            )
        if any(not isinstance(name, str) or not name for name in self.object_names):
            raise BatchTransformError("Object names must be non-empty strings")
        if any(name != name.strip() for name in self.object_names):
            raise BatchTransformError("Object names cannot contain leading or trailing whitespace")
        if len(set(self.object_names)) != len(self.object_names):
            raise BatchTransformError("Object names must be unique")
        if self.delta.is_zero:
            raise BatchTransformError("Batch transform requires at least one non-zero delta")


@dataclass(frozen=True, slots=True)
class BatchTransformReceipt:
    """Outcome returned by a successful batch transaction."""

    object_names: tuple[str, ...]
    affected_count: int
    message: str

    def __post_init__(self) -> None:
        if self.affected_count != len(self.object_names):
            raise BatchTransformError("Affected count must match the returned object names")
