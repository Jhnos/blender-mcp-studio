"""Plain-dict payloads for design pipeline records, shared by REST and MCP delivery adapters.

Enums become their ``.value`` and tuples become lists. ``DesignRunReport.passed`` is a property,
so it is added by hand; ``run_dir`` is deliberately omitted (no host path leaves the process).
"""

from __future__ import annotations

from dataclasses import asdict

from src.core.domain.design_run import DesignRunReport, JobRecord, StageReport
from src.core.domain.slicing import ToolAvailability


def job_dict(job: JobRecord) -> dict[str, object]:
    return {
        "job_id": job.job_id,
        "run_id": job.run_id,
        "status": job.status.value,
        "stage": None if job.stage is None else job.stage.value,
        "error": job.error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def _stage_dict(stage: StageReport) -> dict[str, object]:
    return {
        "name": stage.name.value,
        "outcome": stage.outcome.value,
        "metrics": [list(pair) for pair in stage.metrics],
        "evidence": list(stage.evidence),
        "message": stage.message,
    }


def report_dict(report: DesignRunReport) -> dict[str, object]:
    return {
        "run_id": report.run_id,
        "spec_name": report.spec_name,
        "passed": report.passed,
        "stages": [_stage_dict(stage) for stage in report.stages],
    }


def tool_dict(tool: ToolAvailability) -> dict[str, object]:
    """Availability without the binary ``path``: a host path never leaves the process."""
    row = asdict(tool)
    row.pop("path")
    return row
