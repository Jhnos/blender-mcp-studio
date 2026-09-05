"""YAML-driven multi-step modeling pipelines."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


class PipelineRequest(BaseModel):
    pipeline_name: str
    context: dict[str, object] = Field(default_factory=dict)


@router.post("/pipeline")
async def run_pipeline(body: PipelineRequest, request: Request) -> dict[str, object]:
    """Execute a named YAML-defined modeling pipeline in Blender.

    Pipeline names come from config/modeling_pipeline.yaml.
    Context values fill in {{ placeholder }} slots in stage arguments.
    """
    from src.adapters.pipeline.pipeline_loader import PipelineLoader

    loader = PipelineLoader()
    try:
        stages = loader.load(body.pipeline_name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    use_case = request.app.state.modeling_pipeline

    try:
        result = await use_case.execute(
            stages=stages,
            context=body.context,
            pipeline_name=body.pipeline_name,
        )
    except Exception as e:
        logger.exception("Pipeline failed")
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {
        "pipeline": result.pipeline_name,
        "success": result.success,
        "stages": [
            {
                "name": r.stage_name,
                "status": r.status,
                "output": r.output,
                "error": r.error,
            }
            for r in result.stage_results
        ],
        "failed_stage": result.failed_stage.stage_name if result.failed_stage else None,
    }


@router.get("/pipelines")
async def list_pipelines() -> dict[str, object]:
    """List all available pipeline names from YAML config."""
    from src.adapters.pipeline.pipeline_loader import PipelineLoader

    loader = PipelineLoader()
    return {"pipelines": loader.list_pipelines()}
