"""Tailnet-identity gate for the HTTP API.

The MHH gateway injects a trusted ``x-mes-identity`` header for tailnet HTTP
requests and strips any client-supplied one, so a public/anonymous request
through Tailscale Funnel never carries a valid value. Requiring the header
therefore restricts the HTTP API to tailnet-authenticated callers — closing the
anonymous public reach of endpoints like /api/pipeline (which runs bpy code in
Blender).

BaseHTTPMiddleware runs on HTTP only and passes WebSocket scopes through
untouched. That is deliberate but incomplete: the gateway's own identity
injection is also HTTP-only, so /ws/chat cannot be gated here and needs the
MHH-layer fix (make this host tailnet-only). Tracked separately.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_TRUSTED_HEADER = "x-mes-identity"
# Kept open so the watchdog's direct probe (no gateway, no header) is never
# read as a 401 "service down".
_EXEMPT_PATHS = frozenset({"/api/health"})


class RequireTailnetIdentity(BaseHTTPMiddleware):
    """Reject HTTP requests that lack the gateway-injected tailnet identity."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path not in _EXEMPT_PATHS and not request.headers.get(_TRUSTED_HEADER):
            return JSONResponse(
                {"detail": "tailnet identity required"},
                status_code=401,
            )
        return await call_next(request)
