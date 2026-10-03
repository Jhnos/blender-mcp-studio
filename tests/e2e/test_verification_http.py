"""REST publishes the same runtime verification service injected into MCP."""

from dataclasses import replace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from api.main import create_app
from src.core.domain.verification import VerificationError, VerificationReport
from src.verification.cable_route_cases import registered_suites
from tests.e2e.test_mcp_streamable_http import make_fake_runtime


def test_rest_uses_shared_service_for_catalog_run_and_errors() -> None:
    verification = AsyncMock()
    verification.list_suites.return_value = registered_suites()
    verification.run.return_value = VerificationReport(
        "cable-contact-controls", False, (), "test", True
    )
    runtime = replace(make_fake_runtime(), verification=verification)
    app = create_app(runtime=runtime, require_identity=False)
    assert app.state.verification is runtime.verification
    with TestClient(app) as client:
        assert len(client.get("/api/verification/suites").json()) == len(registered_suites())
        result = client.post("/api/verification/suites/cable-contact-controls/run")
        assert result.status_code == 200 and result.json()["passed"] is False
        verification.run.assert_awaited_once_with("cable-contact-controls")
        verification.run.side_effect = VerificationError("Unknown verification suite")
        assert client.post("/api/verification/suites/unknown/run").status_code == 422
