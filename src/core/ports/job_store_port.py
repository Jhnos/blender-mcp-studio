"""Port for persisting design-run job records across API restarts."""

from __future__ import annotations

from typing import Protocol

from src.core.domain.design_run import JobRecord, JobStatus, StageName


class JobStorePort(Protocol):
    async def create(self, run_id: str) -> JobRecord: ...

    async def update(
        self,
        job_id: str,
        *,
        status: JobStatus,
        stage: StageName | None = None,
        error: str | None = None,
    ) -> JobRecord: ...

    async def get(self, job_id: str) -> JobRecord | None: ...

    async def list_unfinished(self) -> tuple[JobRecord, ...]:
        """Jobs still QUEUED or RUNNING (after a restart these are orphans)."""
        ...
