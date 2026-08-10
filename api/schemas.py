"""API request/response schemas (pydantic v2)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    type: str = "chat"
    content: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    type: str = "response"
    content: str
    status: str  # "streaming" | "done" | "error"
    session_id: str


class SceneInfoResponse(BaseModel):
    objects: list[dict[str, object]]
    description: str


class ExportRequest(BaseModel):
    format: Literal["stl", "obj", "ply", "fbx", "glb"] = "stl"
    selection_only: bool = False
    apply_modifiers: bool = True
    triangulate: bool = True


class PrintReadinessRequest(BaseModel):
    selection_only: bool = False
    apply_modifiers: bool = True
    min_wall_thickness_mm: float = Field(default=0.8, gt=0.0, le=10.0)
    overhang_angle_deg: float = Field(default=45.0, ge=0.0, le=90.0)


class BatchTransformRequest(BaseModel):
    object_names: list[str]
    translation_mm: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale_percent: tuple[float, float, float] = (0.0, 0.0, 0.0)


class UndoRedoResponse(BaseModel):
    success: bool
    action: Literal["undo", "redo"]
    message: str
