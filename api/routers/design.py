"""REST surface of the DesignPipeline: submit a ModelSpec, poll the job, read the run evidence."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from api.schemas import DesignRunRequest
from src.core.domain.design_run import DesignRunReport, JobRecord, StageReport
from src.core.domain.slicing import ToolAvailability
from src.core.use_cases.design_pipeline import DesignPipeline

router = APIRouter(prefix="/api/design")

_MEDIA_TYPES = {".3mf": "model/3mf", ".json": "application/json"}


def _pipeline(request: Request) -> DesignPipeline:
    pipeline: DesignPipeline = request.app.state.design_pipeline
    return pipeline


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
    # ``passed`` is a property, so it must be added by hand.
    return {
        "run_id": report.run_id,
        "spec_name": report.spec_name,
        "passed": report.passed,
        "stages": [_stage_dict(stage) for stage in report.stages],
        "run_dir": report.run_dir,
    }


def tool_dict(tool: ToolAvailability) -> dict[str, object]:
    return asdict(tool)


@router.post("/runs", status_code=202)
async def submit_design_run(body: DesignRunRequest, request: Request) -> dict[str, object]:
    return job_dict(await _pipeline(request).submit(body.spec))


@router.get("/jobs/{job_id}")
async def get_design_job(job_id: str, request: Request) -> dict[str, object]:
    job = await _pipeline(request).status(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"unknown job: {job_id}")
    return job_dict(job)


@router.get("/runs/{run_id}/report")
async def get_design_report(run_id: str, request: Request) -> dict[str, object]:
    report = await _pipeline(request).report(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"no report for run: {run_id}")
    return report_dict(report)


@router.get("/runs/{run_id}/files/{name:path}")
async def download_design_file(run_id: str, name: str, request: Request) -> FileResponse:
    try:
        path = _pipeline(request).run_file(run_id, name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"no such file in run: {name}")
    return FileResponse(
        path,
        media_type=_MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream"),
        filename=path.name,
        content_disposition_type="attachment",
    )


@router.get("/tools")
async def list_design_tools(request: Request) -> list[dict[str, object]]:
    return [tool_dict(tool) for tool in await _pipeline(request).tools()]
