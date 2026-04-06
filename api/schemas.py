"""API request/response schemas (pydantic v2)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


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
    format: Literal["stl", "obj", "fbx", "glb"] = "stl"
    selection_only: bool = False


class UndoRedoResponse(BaseModel):
    success: bool
    action: Literal["undo", "redo"]
    message: str
