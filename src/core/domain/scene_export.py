"""Immutable scene-export value objects shared by all delivery adapters."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SceneExportFormat(StrEnum):
    STL = "stl"
    OBJ = "obj"
    PLY = "ply"
    GLB = "glb"
    FBX = "fbx"


@dataclass(frozen=True, slots=True)
class SceneExportSpec:
    format: SceneExportFormat
    selection_only: bool = False
    apply_modifiers: bool = True
    triangulate: bool = True


@dataclass(frozen=True, slots=True)
class ExportArtifact:
    content: bytes
    filename: str
    media_type: str
