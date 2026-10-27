"""One-at-a-time lease over the shared Blender scene and the slicer.

Stages that drive Blender or the slicer hold it, so two concurrent runs queue instead of
interleaving inside a stage. MCP tools that change the scene hold it by tool name (a ``str``
holder) through ``try_hold``; a pipeline stage holder is a ``StageName``.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from typing import TypeVar

from src.core.domain.design_run import StageName

T = TypeVar("T")
Holder = StageName | str


class BlenderLease:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._holder: Holder | None = None
        self._waiting = 0

    @property
    def holder(self) -> Holder | None:
        """The stage (or MCP tool name) currently holding the lease; None when it is free."""
        return self._holder

    @property
    def busy(self) -> bool:
        """Held, or free with a queued waiter about to take it."""
        return self._lock.locked() or self._waiting > 0

    @asynccontextmanager
    async def hold(self, stage: Holder) -> AsyncIterator[None]:
        self._waiting += 1
        try:
            await self._lock.acquire()
        finally:
            self._waiting -= 1
        self._holder = stage
        try:
            yield
        finally:
            self._holder = None
            self._lock.release()

    @asynccontextmanager
    async def try_hold(self, stage: Holder) -> AsyncIterator[bool]:
        """Hold the lease if nobody holds or awaits it right now (yields True), else False."""
        if self.busy:
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
        # A second cancel must not interrupt this drain and release the lease
        # while the shielded subprocess or file worker is still running.
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break  # Work finished with an error; cancellation still propagates.
        if not task.cancelled():
            task.exception()  # retrieved: the cancellation is what propagates
        raise
