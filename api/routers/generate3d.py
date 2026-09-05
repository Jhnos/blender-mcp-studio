"""Text-to-3D generation delivery adapter."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.adapters.blender_scripts import object_scripts

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


class Generate3DRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=500)
    negative_prompt: str = Field(default="")
    steps: int = Field(default=20, ge=5, le=50)
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0)
    import_to_blender: bool = Field(default=True)


@router.post("/generate3d")
async def generate_3d(req: Generate3DRequest, request: Request) -> dict[str, object]:
    """Generate a 3D GLB mesh from a text prompt via Hunyuan3D-2.

    If import_to_blender is True, the GLB is saved to a temp file and
    imported into the active Blender scene via bpy.ops.import_scene.gltf.

    Response: { glb_url, blender_object, generation_time_s, provider }
    """
    text3d = getattr(request.app.state, "text3d", None)
    if text3d is None:
        raise HTTPException(
            status_code=503,
            detail="Hunyuan3D not configured. Set HUNYUAN3D_MODE or HUNYUAN3D_ENDPOINT.",
        )

    try:
        result = await text3d.generate(
            req.prompt,
            negative_prompt=req.negative_prompt,
            steps=req.steps,
            guidance_scale=req.guidance_scale,
        )
    except Exception as e:
        logger.exception("Text-to-3D generation failed")
        raise HTTPException(status_code=500, detail=str(e)) from e

    # Save GLB to disk
    import pathlib
    import time as _time

    glb_dir = pathlib.Path("data/generated3d")
    glb_dir.mkdir(parents=True, exist_ok=True)
    glb_path = glb_dir / f"gen_{int(_time.time())}.glb"
    glb_path.write_bytes(result.glb_bytes)

    blender_object: str | None = None
    if req.import_to_blender:
        outcome = await object_scripts.import_gltf(
            request.app.state.blender, str(glb_path.resolve())
        )
        if outcome.success:
            blender_object = "imported"
        else:
            logger.warning("GLB import to Blender failed: %s", outcome.error)

    return {
        "glb_path": str(glb_path),
        "blender_object": blender_object,
        "generation_time_s": round(result.generation_time_s, 2),
        "provider": result.provider,
        "prompt": result.prompt,
    }
