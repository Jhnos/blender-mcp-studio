"""Client-neutral scene export application contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from src.core.domain.scene_export import ExportArtifact, SceneExportFormat, SceneExportSpec
from src.core.use_cases.scene_export import SceneExportService


class RecordingExporter:
    def __init__(self) -> None:
        self.specs: list[SceneExportSpec] = []
        self.artifact = ExportArtifact(b"solid cat", "black-cat.stl", "model/stl")

    async def export(self, spec: SceneExportSpec) -> ExportArtifact:
        self.specs.append(spec)
        return self.artifact


@pytest.mark.asyncio
async def test_export_service_depends_on_scene_export_port() -> None:
    exporter = RecordingExporter()
    service = SceneExportService(exporter)
    spec = SceneExportSpec(
        format=SceneExportFormat.STL,
        selection_only=True,
        apply_modifiers=True,
        triangulate=True,
    )

    result = await service.export(spec)

    assert exporter.specs == [spec]
    assert result == exporter.artifact


def test_scene_export_spec_is_an_immutable_value_object() -> None:
    spec = SceneExportSpec(format=SceneExportFormat.PLY)

    with pytest.raises(FrozenInstanceError):
        spec.selection_only = True  # type: ignore[misc]


def test_export_formats_cover_print_and_interchange_workflows() -> None:
    assert {item.value for item in SceneExportFormat} == {"stl", "obj", "ply", "glb", "fbx"}
