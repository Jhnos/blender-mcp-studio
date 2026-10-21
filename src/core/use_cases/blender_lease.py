"""One-at-a-time lease over the shared Blender scene and the slicer.

Stages that drive Blender or the slicer hold it, so two concurrent runs queue instead of
interleaving inside a stage.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from typing import TypeVar

from src.core.domain.design_run import StageName

T = TypeVar("T")


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

    @asynccontextmanager
    async def try_hold(self, stage: StageName) -> AsyncIterator[bool]:
        """Hold the lease if it is free right now (yields True), else yield False at once."""
        if self._lock.locked():
            yield False
            return
        async with self.hold(stage):
            yield True


async def run_to_completion(work: Awaitable[T]) -> T:
    """Await ``work``; if the caller is cancelled, still wait for ``work`` to finish first.

    Used for the slicer inside the lease: cancelling a run must not release the lease while the
    slicer subprocess is still alive (it is bounded by the adapter's own subprocess timeout).
    """
    task = asyncio.ensure_future(work)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        await asyncio.wait([task])
        if not task.cancelled():
            task.exception()  # retrieved: the cancellation is what propagates
        raise
