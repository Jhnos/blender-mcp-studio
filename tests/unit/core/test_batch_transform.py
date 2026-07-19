"""Batch-transform domain and application contract tests."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError

import pytest

from src.core.domain.batch_transform import (
    BatchTransformReceipt,
    BatchTransformSpec,
    TransformDelta,
)
from src.core.domain.exceptions import BatchTransformError
from src.core.domain.scene_operations import Vector3
from src.core.ports.batch_transform_port import SceneBatchCommandPort
from src.core.use_cases.batch_transform import BatchTransformService


class RecordingBatchCommands:
    def __init__(self) -> None:
        self.specs: list[BatchTransformSpec] = []

    async def apply_transform(self, spec: BatchTransformSpec) -> BatchTransformReceipt:
        self.specs.append(spec)
        return BatchTransformReceipt(
            object_names=spec.object_names,
            affected_count=len(spec.object_names),
            message=f"Updated {len(spec.object_names)} objects",
        )


def test_batch_transform_values_are_frozen() -> None:
    delta = TransformDelta(translation_mm=Vector3(10.0, 0.0, 0.0))
    spec = BatchTransformSpec(("A", "B"), delta)
    receipt = BatchTransformReceipt(("A", "B"), 2, "Updated 2 objects")

    for value, field_name in (
        (delta, "translation_mm"),
        (spec, "object_names"),
        (receipt, "affected_count"),
    ):
        with pytest.raises(FrozenInstanceError):
            setattr(value, field_name, None)


@pytest.mark.parametrize(
    ("names", "message"),
    [
        ((), "at least one"),
        (("",), "non-empty"),
        ((" A ",), "leading or trailing"),
        (("A", "A"), "unique"),
        (tuple(f"Object-{index}" for index in range(101)), "at most 100"),
    ],
)
def test_batch_transform_rejects_invalid_targets(names: tuple[str, ...], message: str) -> None:
    with pytest.raises(BatchTransformError, match=message):
        BatchTransformSpec(
            names,
            TransformDelta(translation_mm=Vector3(1.0, 0.0, 0.0)),
        )


def test_batch_transform_rejects_mutable_target_collection() -> None:
    with pytest.raises(BatchTransformError, match="tuple"):
        BatchTransformSpec(  # type: ignore[arg-type]
            ["A"],
            TransformDelta(translation_mm=Vector3(1.0, 0.0, 0.0)),
        )


def test_batch_transform_rejects_zero_delta() -> None:
    with pytest.raises(BatchTransformError, match="non-zero"):
        BatchTransformSpec(("A",), TransformDelta())


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda: TransformDelta(translation_mm=Vector3(100_000.1, 0.0, 0.0)), "100000"),
        (lambda: TransformDelta(rotation_deg=Vector3(0.0, -3600.1, 0.0)), "3600"),
        (lambda: TransformDelta(scale_percent=Vector3(-100.0, 0.0, 0.0)), "greater than -100"),
        (lambda: TransformDelta(scale_percent=Vector3(0.0, 10_000.1, 0.0)), "10000"),
        (lambda: TransformDelta(translation_mm=Vector3(float("nan"), 0.0, 0.0)), "finite"),
        (lambda: TransformDelta(rotation_deg=Vector3(float("inf"), 0.0, 0.0)), "finite"),
    ],
)
def test_batch_transform_rejects_invalid_numeric_values(
    factory: Callable[[], TransformDelta], message: str
) -> None:
    with pytest.raises(BatchTransformError, match=message):
        factory()


def test_batch_transform_accepts_documented_boundaries() -> None:
    spec = BatchTransformSpec(
        ("A",),
        TransformDelta(
            translation_mm=Vector3(100_000.0, -100_000.0, 0.0),
            rotation_deg=Vector3(3600.0, -3600.0, 0.0),
            scale_percent=Vector3(-99.999, 10_000.0, 0.0),
        ),
    )

    assert spec.delta.translation_mm.x == 100_000.0


def test_batch_transform_receipt_requires_matching_count() -> None:
    with pytest.raises(BatchTransformError, match="match"):
        BatchTransformReceipt(("A", "B"), 1, "Updated")


@pytest.mark.asyncio
async def test_service_delegates_through_narrow_batch_port() -> None:
    commands = RecordingBatchCommands()
    service = BatchTransformService(commands)
    spec = BatchTransformSpec(
        ("A", "B"),
        TransformDelta(rotation_deg=Vector3(0.0, 0.0, 15.0)),
    )

    receipt = await service.apply(spec)

    assert isinstance(commands, SceneBatchCommandPort)
    assert commands.specs == [spec]
    assert receipt == BatchTransformReceipt(("A", "B"), 2, "Updated 2 objects")
