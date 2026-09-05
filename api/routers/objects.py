"""Per-object mutations: rename, visibility, selection and deletion."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.adapters.blender_scripts import object_scripts
from src.core.domain.scene_operations import ModifyObjectSpec

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


class ObjectUpdateRequest(BaseModel):
    new_name: str | None = None
    visible: bool | None = None
    selected: bool | None = None


@router.put("/object/{name}")
async def update_object(
    name: str, body: ObjectUpdateRequest, request: Request
) -> dict[str, object]:
    """Rename, show/hide, or select a Blender scene object by name."""
    if body.visible is not None:
        await request.app.state.scene_operations.modify_object(
            ModifyObjectSpec(name=name, visible=body.visible)
        )

    new_name = body.new_name or name
    if body.selected is None and body.new_name is None:
        return {"updated": True, "name": new_name, "original_name": name}

    outcome = await object_scripts.update_object(
        request.app.state.blender,
        name,
        new_name=body.new_name,
        selected=body.selected,
    )
    if not outcome.success:
        raise HTTPException(status_code=500, detail=outcome.error or "Update failed")

    return {"updated": True, "name": new_name, "original_name": name}


@router.delete("/object/{name}")
async def delete_object(name: str, request: Request) -> dict[str, object]:
    """Delete a Blender scene object by name."""
    receipt = await request.app.state.scene_operations.delete_object(name)
    return {
        "deleted": True,
        "name": receipt.object_name,
        "message": receipt.message,
    }


@router.post("/object/{name}/select")
async def select_object(name: str, request: Request) -> dict[str, object]:
    """Select an object and make it the active object in Blender."""
    outcome = await object_scripts.select_object(request.app.state.blender, name)
    if not outcome.success:
        raise HTTPException(status_code=500, detail=outcome.error or "Select failed")
    return {"selected": True, "name": name}
