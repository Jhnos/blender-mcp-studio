"""Outgoing port for exporting a Blender-independent scene artifact."""

from __future__ import annotations

from typing import Protocol

from src.core.domain.scene_export import ExportArtifact, SceneExportSpec


class SceneExportPort(Protocol):
    async def export(self, spec: SceneExportSpec) -> ExportArtifact: ...
