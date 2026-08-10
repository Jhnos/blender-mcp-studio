"""Tailnet-identity gate on the HTTP API.

The MHH gateway injects a trusted ``x-mes-identity`` header for tailnet HTTP
requests and strips any client-spoofed one; a public/anonymous request through
Tailscale Funnel carries none. So requiring that header makes the HTTP API
reachable only by tailnet-authenticated callers — closing the anonymous public
exposure of endpoints like /api/pipeline (which runs bpy in Blender).

Gated by env/param so it is OFF in tests and local dev and ON in production
(the plist sets REQUIRE_TAILNET_IDENTITY=1). /api/health stays open so the
watchdog's direct probe (which carries no header) doesn't read a 401 as "down".

Scope: HTTP only. The /ws/chat WebSocket cannot be gated this way — the gateway's
identity injection is BaseHTTPMiddleware, which skips websocket scope — so that
endpoint needs the MHH-layer fix (make M4 tailnet-only). Tracked separately.
"""

from __future__ import annotations

from fastapi import FastAPI
from starlette.testclient import TestClient

from api.main import create_app

_IDENTITY = {"x-mes-identity": "someone@example.com"}


def _client(*, require_identity: bool) -> TestClient:
    app: FastAPI = create_app(require_identity=require_identity)
    return TestClient(app)


def test_health_is_open_without_identity() -> None:
    """The health probe carries no header and must never be gated."""
    r = _client(require_identity=True).get("/api/health")
    assert r.status_code == 200


def test_protected_path_rejects_missing_identity() -> None:
    """A request with no trusted identity is refused before routing."""
    r = _client(require_identity=True).get("/api/scene")
    assert r.status_code == 401


def test_mcp_is_not_an_identity_exemption() -> None:
    """The mounted MCP transport is protected by the same HTTP identity gate."""
    r = _client(require_identity=True).post("/mcp", json={})
    assert r.status_code == 401


def test_protected_path_allows_present_identity() -> None:
    """With the trusted header, the request passes the gate (routing continues)."""
    r = _client(require_identity=True).get("/api/anything-unrouted", headers=_IDENTITY)
    # Past the gate → normal routing → 404 for the unknown path, NOT 401.
    assert r.status_code != 401


def test_disabled_lets_anonymous_through() -> None:
    """With the gate off (test/dev default), no identity is required."""
    r = _client(require_identity=False).get("/api/anything-unrouted")
    assert r.status_code != 401
