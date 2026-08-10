"""REST delivery contract for client-neutral batch transforms."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from src.core.domain.batch_transform import (
    BatchTransformReceipt,
    BatchTransformSpec,
)
from src.core.domain.exceptions import BatchTransformError, BlenderConnectionError
from tests.e2e.test_mcp_streamable_http import make_fake_runtime


class RecordingBatchTransform:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.specs: list[BatchTransformSpec] = []

    async def apply(self, spec: BatchTransformSpec) -> BatchTransformReceipt:
        self.specs.append(spec)
        if self.error is not None:
            raise self.error
        return BatchTransformReceipt(
            object_names=spec.object_names,
            affected_count=len(spec.object_names),
            message=f"Updated {len(spec.object_names)} objects",
        )


def request_body() -> dict[str, object]:
    return {
        "object_names": ["CatBody", "CatTail"],
        "translation_mm": [10.0, -20.0, 30.0],
        "rotation_deg": [0.0, 0.0, 15.0],
        "scale_percent": [5.0, 5.0, 5.0],
    }


def test_batch_transform_endpoint_maps_request_to_shared_service() -> None:
    app = create_app(runtime=make_fake_runtime(), require_identity=False)
    service = RecordingBatchTransform()
    app.state.batch_transform = service

    with TestClient(app) as client:
        response = client.post("/api/scene/batch-transform", json=request_body())

    assert response.status_code == 200
    assert response.json() == {
        "object_names": ["CatBody", "CatTail"],
        "affected_count": 2,
        "message": "Updated 2 objects",
    }
    assert service.specs[0].delta.translation_mm.as_list() == [10.0, -20.0, 30.0]
    assert service.specs[0].delta.rotation_deg.as_list() == [0.0, 0.0, 15.0]
    assert service.specs[0].delta.scale_percent.as_list() == [5.0, 5.0, 5.0]


def test_batch_transform_endpoint_rejects_transport_and_domain_errors() -> None:
    app = create_app(runtime=make_fake_runtime(), require_identity=False)
    app.state.batch_transform = RecordingBatchTransform()

    with TestClient(app) as client:
        wrong_vector = client.post(
            "/api/scene/batch-transform",
            json={**request_body(), "translation_mm": [1.0, 2.0]},
        )
        invalid_scale = client.post(
            "/api/scene/batch-transform",
            json={**request_body(), "scale_percent": [-100.0, 0.0, 0.0]},
        )

    assert wrong_vector.status_code == 422
    assert invalid_scale.status_code == 422
    assert "greater than -100" in invalid_scale.json()["detail"]


def test_batch_transform_endpoint_maps_domain_and_connection_failures() -> None:
    app = create_app(runtime=make_fake_runtime(), require_identity=False)

    with TestClient(app) as client:
        app.state.batch_transform = RecordingBatchTransform(
            BatchTransformError("Missing objects: CatTail")
        )
        domain_response = client.post("/api/scene/batch-transform", json=request_body())
        app.state.batch_transform = RecordingBatchTransform(
            BlenderConnectionError("Blender is offline")
        )
        connection_response = client.post("/api/scene/batch-transform", json=request_body())

    assert domain_response.status_code == 422
    assert domain_response.json() == {"detail": "Missing objects: CatTail"}
    assert connection_response.status_code == 503
    assert connection_response.json() == {"detail": "Blender is offline"}
