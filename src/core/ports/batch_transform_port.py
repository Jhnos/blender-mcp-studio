"""Incoming port for the batch-transform application capability."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.core.domain.batch_transform import BatchTransformReceipt, BatchTransformSpec


@runtime_checkable
class SceneBatchCommandPort(Protocol):
    """Apply one transform transaction to a complete target set."""

    async def apply_transform(self, spec: BatchTransformSpec) -> BatchTransformReceipt: ...
