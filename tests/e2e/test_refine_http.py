"""REST contract for the vision-guided refinement endpoint.

``POST /api/refine`` had no test at all, and shipped a call to
``adapter_factory.create_llm_adapter()`` — a method that exists on neither the
port nor the concrete factory. Nothing caught it: ``app.state`` hands back
``Any`` so mypy saw nothing, and the only factory double in the suite was a bare
``MagicMock`` that answers to any attribute name.

Both tests below fail against that version: the configured case raised
``AttributeError`` before reaching the use case. They are the gate the fix owes
(docs/LESSONS_LEARNED.md: a lesson whose prescription never becomes a gate keeps
growing new bugs).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from src.core.domain.session import Session
from src.core.use_cases.iterative_refinement import RefinementResult
from tests.e2e.test_mcp_streamable_http import make_fake_runtime


class _StubRefinement:
    """Stands in for the assembled use case; records the per-call budget."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, int | None]] = []

    async def execute(
        self,
        session: Session,
        user_request: str,
        max_iterations: int | None = None,
    ) -> RefinementResult:
        self.calls.append((user_request, max_iterations))
        return RefinementResult(
            session=session, iterations=[], final_screenshot=None, converged=True
        )


def test_refine_without_a_vision_provider_reports_503() -> None:
    """No vision configured is an endpoint-owned decision, not a domain error."""
    runtime = make_fake_runtime()
    app = create_app(runtime=runtime, require_identity=False)
    app.state.iterative_refinement = None

    with TestClient(app) as client:
        response = client.post(
            "/api/refine", json={"session_id": "s1", "user_request": "make it rounder"}
        )

    assert response.status_code == 503
    assert "vision provider" in response.json()["detail"]


def test_refine_runs_the_assembled_use_case_and_passes_the_budget() -> None:
    """The endpoint must reach the use case, not crash assembling one.

    The pre-fix code called a non-existent factory method here and returned 500.
    """
    app = create_app(runtime=make_fake_runtime(), require_identity=False)
    stub = _StubRefinement()
    app.state.iterative_refinement = stub
    app.state.session_store = None

    with TestClient(app) as client:
        response = client.post(
            "/api/refine",
            json={"session_id": "s1", "user_request": "make it rounder", "max_iterations": 2},
        )

    assert response.status_code == 200, response.text
    assert response.json()["converged"] is True
    assert stub.calls == [("make it rounder", 2)]
