"""Application service for client-neutral batch transforms."""

from __future__ import annotations

from src.core.domain.batch_transform import BatchTransformReceipt, BatchTransformSpec
from src.core.ports.batch_transform_port import SceneBatchCommandPort


class BatchTransformService:
    """Coordinate one batch transaction through an injected command port."""

    def __init__(self, commands: SceneBatchCommandPort) -> None:
        self._commands = commands

    async def apply(self, spec: BatchTransformSpec) -> BatchTransformReceipt:
        return await self._commands.apply_transform(spec)
