"""Poly Haven asset search and application."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.adapters.blender_scripts import material_scripts

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


class MaterialApplyRequest(BaseModel):
    asset_id: str
    resolution: str = "1k"
    file_format: str = "hdr"
    apply_as: str = "hdri"  # "hdri" | "texture"


@router.get("/materials/search")
async def search_materials(
    q: str = "",
    asset_type: str = "hdri",
    limit: int = 20,
    request: Request = None,  # type: ignore[assignment]
) -> dict[str, object]:
    """Search Poly Haven assets by keyword, type and limit."""
    ph = getattr(request.app.state, "polyhaven", None)
    if ph is None:
        raise HTTPException(status_code=503, detail="Poly Haven adapter not configured")

    assets = await ph.search(query=q, asset_type=asset_type, limit=limit)
    return {
        "query": q,
        "asset_type": asset_type,
        "results": [
            {
                "id": a.id,
                "name": a.name,
                "categories": list(a.categories),
                "tags": list(a.tags),
                "thumbnail_url": a.thumbnail_url,
                "download_count": a.download_count,
            }
            for a in assets
        ],
    }


@router.post("/materials/apply")
async def apply_material(body: MaterialApplyRequest, request: Request) -> dict[str, object]:
    """Download a Poly Haven asset and apply it in Blender.

    apply_as='hdri'    → sets scene World environment lighting
    apply_as='texture' → applies to active object's material Base Color
    """
    ph = getattr(request.app.state, "polyhaven", None)
    if ph is None:
        raise HTTPException(status_code=503, detail="Poly Haven adapter not configured")

    ph_file = await ph.get_download_url(
        body.asset_id,
        resolution=body.resolution,
        file_format=body.file_format,
    )
    if ph_file is None:
        raise HTTPException(
            status_code=404,
            detail=f"No download URL for {body.asset_id!r} @ {body.resolution}/{body.file_format}",
        )

    apply = {
        "hdri": material_scripts.apply_hdri,
        "texture": material_scripts.apply_texture,
    }.get(body.apply_as)
    if apply is None:
        raise HTTPException(status_code=400, detail=f"Unknown apply_as: {body.apply_as!r}")

    outcome = await apply(request.app.state.blender, ph_file.url)
    if not outcome.success:
        raise HTTPException(status_code=500, detail=f"Apply failed: {outcome.error}")

    return {
        "applied": True,
        "asset_id": body.asset_id,
        "resolution": ph_file.resolution,
        "file_format": ph_file.file_format,
        "url": ph_file.url,
        "blender_output": outcome.output,
    }
