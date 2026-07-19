from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from src.core.domain.exceptions import BlenderConnectionError, PrintReadinessError
from src.core.domain.print_readiness import (
    PrintMetrics,
    PrintReadinessReport,
    PrintReadinessSpec,
    PrintReadinessStatus,
)
from tests.e2e.test_mcp_streamable_http import make_fake_runtime


class RecordingPrintReadiness:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.specs: list[PrintReadinessSpec] = []

    async def check(self, spec: PrintReadinessSpec) -> PrintReadinessReport:
        self.specs.append(spec)
        if self.error is not None:
            raise self.error
        return PrintReadinessReport(
            PrintReadinessStatus.READY,
            PrintMetrics(1, 12, (20.0, 20.0, 20.0), 8000.0, 2400.0),
            (),
            False,
        )


def test_print_readiness_endpoint_maps_request_to_shared_service() -> None:
    app = create_app(runtime=make_fake_runtime(), require_identity=False)
    service = RecordingPrintReadiness()
    app.state.print_readiness = service

    with TestClient(app) as client:
        response = client.post(
            "/api/print-readiness",
            json={
                "selection_only": True,
                "apply_modifiers": False,
                "min_wall_thickness_mm": 0.6,
                "overhang_angle_deg": 50.0,
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["metrics"]["dimensions_mm"] == [20.0, 20.0, 20.0]
    assert service.specs == [PrintReadinessSpec(True, False, 0.6, 50.0)]


def test_print_readiness_endpoint_validates_thresholds() -> None:
    app = create_app(runtime=make_fake_runtime(), require_identity=False)

    with TestClient(app) as client:
        response = client.post(
            "/api/print-readiness",
            json={"min_wall_thickness_mm": 0.0},
        )

    assert response.status_code == 422


def test_print_readiness_endpoint_maps_domain_and_connection_failures() -> None:
    app = create_app(runtime=make_fake_runtime(), require_identity=False)

    with TestClient(app) as client:
        app.state.print_readiness = RecordingPrintReadiness(PrintReadinessError("bad mesh"))
        domain_response = client.post("/api/print-readiness", json={})
        app.state.print_readiness = RecordingPrintReadiness(BlenderConnectionError("offline"))
        connection_response = client.post("/api/print-readiness", json={})

    assert domain_response.status_code == 422
    assert domain_response.json() == {"detail": "bad mesh"}
    assert connection_response.status_code == 503
    assert connection_response.json() == {"detail": "offline"}
