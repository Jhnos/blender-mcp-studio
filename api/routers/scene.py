"""Scene info REST router.

Reuses the shared BlenderMCPAdapter from app.state (set by lifespan).
No new TCP connection per request. Business logic delegated to use cases.
"""

from __future__ import annotations

import base64

from fastapi import APIRouter, Request
from fastapi.responses import Response

from api.schemas import SceneInfoResponse
from src.core.use_cases.get_scene_preview import GetScenePreviewUseCase

router = APIRouter(prefix="/api")

_PLACEHOLDER_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


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
