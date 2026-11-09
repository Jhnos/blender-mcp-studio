"""One-at-a-time lease over the shared Blender scene and the slicer.

Stages that drive Blender or the slicer hold it, so two concurrent runs queue instead of
interleaving inside a stage. MCP tools that change the scene hold it by tool name (a ``str``
holder) through ``try_hold``; a pipeline stage holder is a ``StageName``.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from typing import TypeVar

from src.core.domain.design_run import StageName
from src.core.domain.exceptions import BlenderBusyError

T = TypeVar("T")
Holder = StageName | str


class BlenderLease:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._holder: Holder | None = None
        self._waiting = 0
        self._owner: asyncio.Task[object] | None = None
        self._recovery_ticket: str | None = None

    @property
    def holder(self) -> Holder | None:
        """The stage (or MCP tool name) currently holding the lease; None when it is free."""
        return self._holder

    @property
    def busy(self) -> bool:
        """Held, or free with a queued waiter about to take it."""
        return self._recovery_ticket is not None or self._lock.locked() or self._waiting > 0

    @asynccontextmanager
    async def hold(self, stage: Holder) -> AsyncIterator[None]:
        if self._recovery_ticket is not None:
            raise BlenderBusyError(
                "Blender command completion is unresolved; verified recovery is required"
            )
        self._waiting += 1
        try:
            await self._lock.acquire()
        finally:
            self._waiting -= 1
        if self._recovery_ticket is not None:
            self._lock.release()
            raise BlenderBusyError(
                "Blender command completion is unresolved; verified recovery is required"
            )
        self._holder = stage
        self._owner = asyncio.current_task()
        try:
            yield
        finally:
            self._holder = None
            self._owner = None
            self._lock.release()

    @asynccontextmanager
    async def try_hold(self, stage: Holder) -> AsyncIterator[bool]:
        """Hold the lease if nobody holds or awaits it right now (yields True), else False."""
        if self.busy:
            yield False
            return
        async with self.hold(stage):
            yield True

    @property
    def recovery_ticket(self) -> str | None:
        """Internal correlation for verified recovery; never exposed as a client action."""
        return self._recovery_ticket

    def quarantine(self) -> None:
        if self._owner is not asyncio.current_task():
            raise RuntimeError("only the current mutation owner can quarantine the engine")
        if self._recovery_ticket is None:
            self._recovery_ticket = uuid.uuid4().hex

    def restore_quarantine(self, ticket: str) -> None:
        """Restore unresolved execution ownership before accepting new requests at startup."""
        if self._lock.locked() or self._waiting or not ticket:
            raise BlenderBusyError("cannot restore quarantine while Blender work is active")
        if self._recovery_ticket is not None and self._recovery_ticket != ticket:
            raise BlenderBusyError("a different unresolved Blender command owns quarantine")
        self._recovery_ticket = ticket

    def resolve_quarantine(self, ticket: str) -> None:
        """Called by trusted recovery only after validating remote terminal evidence."""
        if self._recovery_ticket is None or ticket != self._recovery_ticket:
            raise ValueError("recovery ticket does not match the unresolved command")
        self._recovery_ticket = None

    @asynccontextmanager
    async def command(self, operation: str) -> AsyncIterator[None]:
        if self._recovery_ticket is not None:
            raise BlenderBusyError(
                "Blender command completion is unresolved; verified recovery is required"
            )
        if self._owner is asyncio.current_task() and self._lock.locked():
            yield
            return
        async with self.try_hold(operation) as acquired:
            if not acquired:
                raise BlenderBusyError(
                    f"Blender is busy with {self._holder or 'a queued job'}; retry later"
                )
            yield


async def run_to_completion(work: Awaitable[T], *, started: asyncio.Event | None = None) -> T:
    """Await ``work``; if the caller is cancelled, still wait for ``work`` to finish first.

    When supplied, ``started`` distinguishes cancellable queued work from a
    dispatched operation that must drain. Callers set it before the first mutation.

    Used for the slicer inside the lease: cancelling a run must not release the lease while the
    slicer subprocess is still alive (it is bounded by the adapter's own subprocess timeout).
    """
    task = asyncio.ensure_future(work)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        if started is not None and not started.is_set():
            task.cancel()  # Queued, not dispatched: cancellation must prevent later work.
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
