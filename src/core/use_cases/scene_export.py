"""Application service for client-neutral scene export."""

from __future__ import annotations

from src.core.domain.scene_export import ExportArtifact, SceneExportSpec
from src.core.ports.scene_export_port import SceneExportPort


class SceneExportService:
    def __init__(self, exporter: SceneExportPort) -> None:
        self._exporter = exporter

    async def export(self, spec: SceneExportSpec) -> ExportArtifact:
        return await self._exporter.export(spec)
