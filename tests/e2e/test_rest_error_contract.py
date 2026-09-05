"""Characterization net for the REST domain-error contract.

Seven endpoints hand-write the same two clauses today: ``BlenderConnectionError``
becomes 503 and the endpoint's own domain error becomes 422, both with
``detail=str(exc)``. This file pins the observable result of all fourteen
combinations *before* that mapping is centralized, so the refactor has to prove
it changed nothing.

It asserts only on the HTTP surface — status code and response body. It cannot
tell whether the mapping came from a try/except inside the endpoint or from an
application-wide exception handler, which is exactly why it survives the move.

Scope note: this covers the *domain-error* mapping only. The explicit guards in
``api/routers/scene.py`` (``not configured`` 503s, 404s, 410, 500s from result
payloads) are a different contract and are deliberately out of scope here.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.main import create_app
from src.core.domain.exceptions import (
    BatchTransformError,
    BlenderConnectionError,
    PrintReadinessError,
    SceneExportError,
    SceneOperationError,
)
from tests.e2e.test_mcp_streamable_http import make_fake_runtime

DETAIL = "characterization probe"


class RaisingService:
    """A service double whose every awaited method raises ``error``.

    Using ``__getattr__`` keeps the double independent of each port's method
    names, so the net does not have to be edited when an endpoint is moved
    between routers.
    """

    def __init__(self, error: Exception) -> None:
        self._error = error

    def __getattr__(self, name: str) -> Callable[..., Any]:
        async def _raise(*args: object, **kwargs: object) -> Any:
            raise self._error

        return _raise


#: ``(id, method, path, json_body, state_attr, domain_error_factory)``
ENDPOINTS: list[tuple[str, str, str, dict[str, object] | None, str, type[Exception]]] = [
    ("get_scene", "GET", "/api/scene", None, "scene_operations", SceneOperationError),
    ("get_preview", "GET", "/api/preview", None, "scene_operations", SceneOperationError),
    (
        "update_object",
        "PUT",
        "/api/object/Cube",
        {"visible": False},
        "scene_operations",
        SceneOperationError,
    ),
    ("delete_object", "DELETE", "/api/object/Cube", None, "scene_operations", SceneOperationError),
    ("print_readiness", "POST", "/api/print-readiness", {}, "print_readiness", PrintReadinessError),
    (
        "batch_transform",
        "POST",
        "/api/scene/batch-transform",
        # A non-zero delta is required: this endpoint builds its DTO inside the
        # same try block, so an all-zero body would fail validation before the
        # service is ever called and would probe the wrong clause.
        {"object_names": ["Cube"], "translation_mm": [1.0, 0.0, 0.0]},
        "batch_transform",
        BatchTransformError,
    ),
    ("scene_export", "POST", "/api/export", {}, "scene_export", SceneExportError),
]


@pytest.fixture
def app() -> Iterator[FastAPI]:
    yield create_app(runtime=make_fake_runtime(), require_identity=False)


def _call(
    app: FastAPI, method: str, path: str, body: dict[str, object] | None
) -> tuple[int, object]:
    with TestClient(app) as client:
        response = client.request(method, path, json=body)
    return response.status_code, response.json()


@pytest.mark.parametrize(
    ("name", "method", "path", "body", "state_attr", "domain_error"),
    ENDPOINTS,
    ids=[row[0] for row in ENDPOINTS],
)
def test_connection_error_maps_to_503(
    app: FastAPI,
    name: str,
    method: str,
    path: str,
    body: dict[str, object] | None,
    state_attr: str,
    domain_error: type[Exception],
) -> None:
    setattr(app.state, state_attr, RaisingService(BlenderConnectionError(DETAIL)))
    status, payload = _call(app, method, path, body)
    assert (status, payload) == (503, {"detail": DETAIL})


@pytest.mark.parametrize(
    ("name", "method", "path", "body", "state_attr", "domain_error"),
    ENDPOINTS,
    ids=[row[0] for row in ENDPOINTS],
)
def test_domain_error_maps_to_422(
    app: FastAPI,
    name: str,
    method: str,
    path: str,
    body: dict[str, object] | None,
    state_attr: str,
    domain_error: type[Exception],
) -> None:
    setattr(app.state, state_attr, RaisingService(domain_error(DETAIL)))
    status, payload = _call(app, method, path, body)
    assert (status, payload) == (422, {"detail": DETAIL})


def test_batch_transform_error_is_a_scene_operation_error() -> None:
    """Guards the MRO assumption the centralized handler will depend on.

    ``BatchTransformError`` inherits from ``SceneOperationError``, which inherits
    from ``DomainError`` — and ``BlenderConnectionError`` inherits from
    ``DomainError`` directly. A handler registered only on ``DomainError`` would
    therefore swallow connection errors and silently drop every 503 to 422. The
    hierarchy is load-bearing, so it is asserted rather than assumed.
    """
    assert issubclass(BatchTransformError, SceneOperationError)
    assert not issubclass(BlenderConnectionError, SceneOperationError)
    for error in (SceneOperationError, SceneExportError, PrintReadinessError):
        assert not issubclass(BlenderConnectionError, error)
