"""One-at-a-time lease over the shared Blender scene and the slicer.

Stages that drive Blender or the slicer hold it, so two concurrent runs queue instead of
interleaving inside a stage.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from src.core.domain.design_run import StageName


class BlenderLease:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._holder: StageName | None = None

    @property
    def holder(self) -> StageName | None:
        """The stage currently holding the lease; None when it is free."""
        return self._holder

    @asynccontextmanager
    async def hold(self, stage: StageName) -> AsyncIterator[None]:
        async with self._lock:
            self._holder = stage
            try:
                yield
            finally:
                self._holder = None
