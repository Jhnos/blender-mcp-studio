"""Closed native execution over the existing runtime, without transport knowledge."""

from typing import Protocol

from src.core.domain.native_revision import NativeRevisionResult, PreparedNativeRevision


class NativeRunnerPort(Protocol):
    @property
    def unresolved_run_ids(self) -> tuple[str, ...]: ...

    async def execute(self, prepared: PreparedNativeRevision) -> NativeRevisionResult: ...

    async def recover_unfinished(self) -> int: ...
