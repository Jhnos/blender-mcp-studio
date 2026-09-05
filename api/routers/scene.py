"""Read-only scene queries backed by the shared SceneOperationsService."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import Response

from api.schemas import SceneInfoResponse

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


@router.get("/scene", response_model=SceneInfoResponse)
async def get_scene(request: Request) -> SceneInfoResponse:
    scene = await request.app.state.scene_operations.get_scene_info()
    return SceneInfoResponse(
        objects=[
            {
                "name": obj.name,
                "type": obj.object_type,
                "location": obj.location.as_list(),
            }
            for obj in scene.objects
        ],
        description=scene.name,
    )


@router.get("/preview")
async def get_preview(request: Request) -> Response:
    """Return a viewport screenshot from Blender as PNG image."""
    screenshot = await request.app.state.scene_operations.get_viewport_screenshot()
    return Response(content=screenshot.png_bytes, media_type="image/png")
