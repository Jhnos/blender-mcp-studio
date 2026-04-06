"""Scene info, pipeline, and refinement REST routers.

Reuses the shared BlenderMCPAdapter from app.state (set by lifespan).
No new TCP connection per request. Business logic delegated to use cases.
"""

from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from api.schemas import SceneInfoResponse
from src.core.use_cases.get_scene_preview import GetScenePreviewUseCase
from src.core.use_cases.iterative_refinement import IterativeRefinementUseCase
from src.core.use_cases.modeling_pipeline import ModelingPipelineUseCase

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)

_PLACEHOLDER_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


class RefineRequest(BaseModel):
    session_id: str
    user_request: str
    max_iterations: int = Field(default=3, ge=1, le=10)


class PipelineRequest(BaseModel):
    pipeline_name: str
    context: dict = Field(default_factory=dict)


@router.get("/scene", response_model=SceneInfoResponse)
async def get_scene(request: Request) -> SceneInfoResponse:
    blender = request.app.state.blender
    try:
        info = await blender.get_scene_info()
    except Exception:
        info = {}
    return SceneInfoResponse(
        objects=info.get("objects", []),  # type: ignore[arg-type]
        description=str(info.get("description", "")),
    )


@router.get("/preview")
async def get_preview(request: Request) -> Response:
    """Return a viewport screenshot from Blender as PNG image."""
    use_case = GetScenePreviewUseCase(blender=request.app.state.blender)
    image_bytes = await use_case.execute()
    return Response(
        content=image_bytes or _PLACEHOLDER_PNG,
        media_type="image/png",
    )


@router.post("/refine")
async def refine_model(body: RefineRequest, request: Request) -> dict:
    """Run iterative vision-guided refinement loop on the current Blender scene.

    Requires a vision adapter to be configured (OPENAI_API_KEY or ANTHROPIC_API_KEY).
    """
    vision = getattr(request.app.state, "vision", None)
    if vision is None:
        raise HTTPException(
            status_code=503,
            detail="No vision provider configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY.",
        )

    # Retrieve session for LLM context
    session_store = getattr(request.app.state, "session_store", None)
    session = None
    if session_store:
        session = await session_store.get(body.session_id)

    if session is None:
        from src.core.domain.session import Session
        session = Session()

    # Build LLM adapter
    adapter_factory = request.app.state.adapter_factory
    llm = adapter_factory.create_llm_adapter()

    use_case = IterativeRefinementUseCase(
        llm=llm,
        blender=request.app.state.blender,
        vision=vision,
        max_iterations=body.max_iterations,
    )

    try:
        result = await use_case.execute(session, user_request=body.user_request)
    except Exception as e:
        logger.exception("Refinement failed")
        raise HTTPException(status_code=500, detail=str(e)) from e

    # Save updated session
    if session_store:
        await session_store.save(result.session)

    return {
        "converged": result.converged,
        "iteration_count": result.iteration_count,
        "iterations": [
            {
                "iteration": it.iteration,
                "vision_analysis": it.vision_analysis,
                "commands_executed": it.commands_executed,
                "converged": it.converged,
            }
            for it in result.iterations
        ],
        "final_screenshot": (
            base64.b64encode(result.final_screenshot).decode()
            if result.final_screenshot
            else None
        ),
    }


@router.post("/pipeline")
async def run_pipeline(body: PipelineRequest, request: Request) -> dict:
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

    blender = request.app.state.blender
    use_case = ModelingPipelineUseCase(blender=blender)

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
async def list_pipelines() -> dict:
    """List all available pipeline names from YAML config."""
    from src.adapters.pipeline.pipeline_loader import PipelineLoader
    loader = PipelineLoader()
    return {"pipelines": loader.list_pipelines()}

