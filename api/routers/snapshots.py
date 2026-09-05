"""Snapshot capture, listing, restore and deletion."""

from __future__ import annotations

import base64
import logging
import os
from datetime import UTC

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.adapters.blender_scripts import snapshot_scripts

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


class SnapshotCreateRequest(BaseModel):
    label: str = "Snapshot"
    session_id: str = ""


@router.post("/snapshot")
async def create_snapshot(body: SnapshotCreateRequest, request: Request) -> dict[str, object]:
    """Save the current Blender scene to a .blend file and record in snapshot store."""
    import uuid
    from datetime import datetime

    snapshot_store = getattr(request.app.state, "snapshot_store", None)
    if snapshot_store is None:
        raise HTTPException(status_code=503, detail="Snapshot store not configured")

    blender = request.app.state.blender

    # Save .blend file inside Blender
    outcome = await snapshot_scripts.save_snapshot(blender)
    if not outcome.success:
        raise HTTPException(status_code=500, detail=f"Snapshot save failed: {outcome.error}")

    blend_path = str(outcome.output or "").strip().splitlines()[-1]
    if not blend_path or not os.path.exists(blend_path):
        raise HTTPException(status_code=500, detail="Blend file not created")

    # Capture thumbnail
    thumbnail_b64 = ""
    import tempfile

    try:
        tmp = tempfile.mktemp(suffix=".png")
        shot = await blender.call_tool("get_viewport_screenshot", {"filepath": tmp})
        if shot.success and os.path.exists(tmp):
            with open(tmp, "rb") as f:
                thumbnail_b64 = base64.b64encode(f.read()).decode()
            os.unlink(tmp)
    except Exception as exc:
        logger.debug("Thumbnail capture failed: %s", exc)

    from src.core.ports.snapshot_store_port import SceneSnapshot

    snap = SceneSnapshot(
        id=str(uuid.uuid4()),
        label=body.label,
        blend_path=blend_path,
        thumbnail_b64=thumbnail_b64,
        created_at=datetime.now(UTC).isoformat(),
        session_id=body.session_id,
    )
    await snapshot_store.save(snap)

    return {
        "id": snap.id,
        "label": snap.label,
        "created_at": snap.created_at,
        "has_thumbnail": bool(thumbnail_b64),
    }


@router.get("/snapshots")
async def list_snapshots(request: Request) -> dict[str, object]:
    """List all saved scene snapshots (newest first)."""
    snapshot_store = getattr(request.app.state, "snapshot_store", None)
    if snapshot_store is None:
        return {"snapshots": []}

    snap_list = await snapshot_store.list_all()
    return {
        "snapshots": [
            {
                "id": s.id,
                "label": s.label,
                "created_at": s.created_at,
                "session_id": s.session_id,
                "thumbnail": s.thumbnail_b64 or None,
            }
            for s in snap_list.snapshots
        ]
    }


@router.post("/snapshot/{snapshot_id}/restore")
async def restore_snapshot(snapshot_id: str, request: Request) -> dict[str, object]:
    """Restore Blender scene from a previously saved snapshot."""
    snapshot_store = getattr(request.app.state, "snapshot_store", None)
    if snapshot_store is None:
        raise HTTPException(status_code=503, detail="Snapshot store not configured")

    snap = await snapshot_store.get(snapshot_id)
    if snap is None:
        raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id!r} not found")

    if not os.path.exists(snap.blend_path):
        raise HTTPException(
            status_code=410,
            detail=f"Blend file missing from disk: {snap.blend_path}",
        )

    outcome = await snapshot_scripts.restore_snapshot(request.app.state.blender, snap.blend_path)
    if not outcome.success:
        raise HTTPException(status_code=500, detail=f"Restore failed: {outcome.error}")

    return {
        "restored": True,
        "snapshot_id": snapshot_id,
        "label": snap.label,
        "blend_path": snap.blend_path,
    }


@router.delete("/snapshot/{snapshot_id}")
async def delete_snapshot(snapshot_id: str, request: Request) -> dict[str, object]:
    """Delete a snapshot record from the store (does not remove .blend file)."""
    snapshot_store = getattr(request.app.state, "snapshot_store", None)
    if snapshot_store is None:
        raise HTTPException(status_code=503, detail="Snapshot store not configured")

    snap = await snapshot_store.get(snapshot_id)
    if snap is None:
        raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id!r} not found")

    await snapshot_store.delete(snapshot_id)
    return {"deleted": True, "snapshot_id": snapshot_id}
