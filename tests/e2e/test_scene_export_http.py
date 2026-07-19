"""HTTP delivery contract for client-neutral scene export."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from src.core.domain.exceptions import SceneExportError
from src.core.domain.scene_export import ExportArtifact, SceneExportSpec
from tests.e2e.test_mcp_streamable_http import make_fake_runtime


class RecordingSceneExport:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.specs: list[SceneExportSpec] = []

    async def export(self, spec: SceneExportSpec) -> ExportArtifact:
        self.specs.append(spec)
        if self.error is not None:
            raise self.error
        return ExportArtifact(b"ply mesh", "blender-scene.ply", "application/octet-stream")


def test_export_endpoint_maps_request_to_application_service() -> None:
    runtime = make_fake_runtime()
    app = create_app(runtime=runtime, require_identity=False)
    service = RecordingSceneExport()
    app.state.scene_export = service

    with TestClient(app) as client:
        response = client.post(
            "/api/export",
            json={
                "format": "ply",
                "selection_only": True,
                "apply_modifiers": False,
                "triangulate": True,
            },
        )

    assert response.status_code == 200
    assert response.content == b"ply mesh"
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-disposition"] == 'attachment; filename="blender-scene.ply"'
    assert service.specs == [
        SceneExportSpec(
            format=service.specs[0].format,
            selection_only=True,
            apply_modifiers=False,
            triangulate=True,
        )
    ]
    assert service.specs[0].format.value == "ply"


def test_export_endpoint_surfaces_domain_failure() -> None:
    app = create_app(runtime=make_fake_runtime(), require_identity=False)
    app.state.scene_export = RecordingSceneExport(SceneExportError("mesh is empty"))

    with TestClient(app) as client:
        response = client.post("/api/export", json={"format": "stl"})

    assert response.status_code == 422
    assert response.json() == {"detail": "mesh is empty"}
