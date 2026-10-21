"""Immutable records for a design pipeline run: stages, report and async job."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class StageName(StrEnum):
    IMPORT = "import"
    GEOMETRY = "geometry"
    MECHANISM = "mechanism"
    PRINT = "print"
    PACKAGE = "package"


class StageOutcome(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class StageReport:
    name: StageName
    outcome: StageOutcome
    metrics: tuple[tuple[str, str], ...]
    evidence: tuple[str, ...]
    message: str


@dataclass(frozen=True, slots=True)
class DesignRunReport:
    run_id: str
    spec_name: str
    stages: tuple[StageReport, ...]
    run_dir: str

    @property
    def passed(self) -> bool:
        """True only for a complete run: every stage once, in order, none FAILED."""
        return tuple(stage.name for stage in self.stages) == tuple(StageName) and all(
            stage.outcome in (StageOutcome.PASSED, StageOutcome.NOT_APPLICABLE)
            for stage in self.stages
        )


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class JobRecord:
    job_id: str
    run_id: str
    status: JobStatus
    stage: StageName | None
    error: str | None
    created_at: float
    updated_at: float
