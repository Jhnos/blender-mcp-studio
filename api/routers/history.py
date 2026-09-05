"""Undo/redo delivery adapter for the shared Blender session."""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Request

from api.schemas import UndoRedoResponse
from src.adapters.blender_scripts import history_scripts

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


@router.post("/undo", response_model=UndoRedoResponse)
async def undo_action(request: Request) -> UndoRedoResponse:
    """Undo the last operation in the shared Blender session."""
    return await _run_undo_redo(request, "undo")


@router.post("/redo", response_model=UndoRedoResponse)
async def redo_action(request: Request) -> UndoRedoResponse:
    """Redo the last undone operation in the shared Blender session."""
    return await _run_undo_redo(request, "redo")


async def _run_undo_redo(request: Request, action: Literal["undo", "redo"]) -> UndoRedoResponse:
    outcome = await history_scripts.run_history_action(request.app.state.blender, action)
    return UndoRedoResponse(
        success=outcome.success,
        action=action,
        message=(str(outcome.output) if outcome.success else (outcome.error or "Unknown error")),
    )
