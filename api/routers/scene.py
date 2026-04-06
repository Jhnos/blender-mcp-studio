"""Scene info, pipeline, and refinement REST routers.

Reuses the shared BlenderMCPAdapter from app.state (set by lifespan).
No new TCP connection per request. Business logic delegated to use cases.
"""

from __future__ import annotations

import base64
import logging
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from api.schemas import ExportRequest, SceneInfoResponse
from src.core.domain.command import Command
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


# ---------------------------------------------------------------------------
# V3: Export endpoint — download Blender scene as 3D file
# ---------------------------------------------------------------------------

_EXPORT_MIME = {
    "stl": "model/stl",
    "obj": "text/plain",
    "fbx": "application/octet-stream",
    "glb": "model/gltf-binary",
}

_EXPORT_CODE = {
    "stl": """\
import bpy, tempfile, os
tmp = tempfile.mktemp(suffix='.stl')
bpy.ops.export_mesh.stl(filepath=tmp, use_selection={selection_only})
print(tmp)
""",
    "obj": """\
import bpy, tempfile
tmp = tempfile.mktemp(suffix='.obj')
bpy.ops.wm.obj_export(filepath=tmp, export_selected_objects={selection_only})
print(tmp)
""",
    "fbx": """\
import bpy, tempfile
tmp = tempfile.mktemp(suffix='.fbx')
bpy.ops.export_scene.fbx(filepath=tmp, use_selection={selection_only})
print(tmp)
""",
    "glb": """\
import bpy, tempfile
tmp = tempfile.mktemp(suffix='.glb')
bpy.ops.export_scene.gltf(filepath=tmp, use_selection={selection_only}, export_format='GLB')
print(tmp)
""",
}


@router.post("/export")
async def export_scene(body: ExportRequest, request: Request) -> Response:
    """Export the Blender scene as STL, OBJ, FBX, or GLB for download.

    The file is generated inside Blender's Python environment, read back,
    and returned as a binary HTTP response. No temp files are left on disk.
    """
    fmt = body.format
    code = _EXPORT_CODE.get(fmt)
    if code is None:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}")

    code = code.format(selection_only=str(body.selection_only))
    blender = request.app.state.blender

    cmd = Command(tool_name="execute_code", arguments={"code": code})
    try:
        result = await blender.execute(cmd)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Blender unreachable: {e}") from e

    if not result.success:
        raise HTTPException(status_code=500, detail=f"Export failed: {result.error}")

    filepath = (result.output or "").strip().splitlines()[-1] if result.output else ""
    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=500, detail="Export file not found on disk")

    with open(filepath, "rb") as f:
        file_bytes = f.read()
    os.unlink(filepath)

    filename = f"blender_scene.{fmt}"
    return Response(
        content=file_bytes,
        media_type=_EXPORT_MIME[fmt],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# V3: Undo / Redo endpoints
# ---------------------------------------------------------------------------

@router.post("/undo")
async def undo_action(request: Request) -> dict:
    """Undo the last operation in Blender (bpy.ops.ed.undo)."""
    return await _run_undo_redo(request, "undo")


@router.post("/redo")
async def redo_action(request: Request) -> dict:
    """Redo the last undone operation in Blender (bpy.ops.ed.undo_redo)."""
    return await _run_undo_redo(request, "redo")


async def _run_undo_redo(request: Request, action: str) -> dict:
    blender = request.app.state.blender
    bpy_call = "bpy.ops.ed.undo()" if action == "undo" else "bpy.ops.ed.undo_redo()"
    code = f"import bpy\n{bpy_call}\nprint('{action} ok')"

    cmd = Command(tool_name="execute_code", arguments={"code": code})
    try:
        result = await blender.execute(cmd)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Blender unreachable: {e}") from e

    return {
        "success": result.success,
        "action": action,
        "message": result.output if result.success else (result.error or "Unknown error"),
    }

