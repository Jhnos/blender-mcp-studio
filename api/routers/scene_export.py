"""HTTP delivery adapter for downloadable scene exports."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from api.schemas import ExportRequest
from src.core.domain.exceptions import BlenderConnectionError, SceneExportError
from src.core.domain.scene_export import SceneExportFormat, SceneExportSpec

router = APIRouter(prefix="/api")


@router.post("/export")
async def export_scene(body: ExportRequest, request: Request) -> Response:
    spec = SceneExportSpec(
        format=SceneExportFormat(body.format),
        selection_only=body.selection_only,
        apply_modifiers=body.apply_modifiers,
        triangulate=body.triangulate,
    )
    try:
        artifact = await request.app.state.scene_export.export(spec)
    except BlenderConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SceneExportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(
        content=artifact.content,
        media_type=artifact.media_type,
        headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"'},
    )
