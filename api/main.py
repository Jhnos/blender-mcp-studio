"""FastAPI application entry point with a shared client-neutral MCP runtime."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastmcp.utilities.lifespan import combine_lifespans
from starlette.types import ASGIApp, Receive, Scope, Send

from api.routers import (
    batch_transform,
    chat,
    generate3d,
    history,
    materials,
    objects,
    pipelines,
    print_readiness,
    scene,
    scene_export,
    snapshots,
    vision,
)
from api.routers.ws_manager import ConnectionManager, viewport_broadcast_loop
from api.runtime import AppRuntime, build_runtime
from src.adapters.mcp_server import create_mcp_server
from src.core.domain.exceptions import (
    BlenderConnectionError,
    DomainError,
    LLMConnectionError,
)

logger = logging.getLogger(__name__)
PROJECT_VERSION = (Path(__file__).parents[1] / "VERSION").read_text().strip()


class _NormalizeMcpPath:
    """Serve the canonical no-slash MCP URL without an authority-changing redirect."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"] == "/mcp":
            scope = {**scope, "path": "/mcp/", "raw_path": b"/mcp/"}
        await self._app(scope, receive, send)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Own the single shared Blender connection and viewport task."""
    runtime: AppRuntime = app.state.runtime
    try:
        await runtime.blender.connect()
    except BlenderConnectionError as exc:
        logger.warning("Blender unavailable at API startup: %s", exc)

    push_interval = float(os.environ.get("VIEWPORT_PUSH_INTERVAL", "3"))
    broadcast_task = asyncio.create_task(viewport_broadcast_loop(app.state, interval=push_interval))
    try:
        yield
    finally:
        broadcast_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await broadcast_task
        await runtime.blender.disconnect()


def _origins(cors_origins: list[str] | None) -> list[str]:
    if cors_origins is not None:
        return cors_origins
    return [
        origin.strip()
        for origin in os.environ.get(
            "CORS_ORIGINS",
            "https://bearmacminimac-mini.tail56c751.ts.net",
        ).split(",")
        if origin.strip()
    ]


def _identity_required(require_identity: bool | None) -> bool:
    if require_identity is not None:
        return require_identity
    return os.environ.get("REQUIRE_TAILNET_IDENTITY", "").lower() in {
        "1",
        "true",
        "yes",
    }


def _publish_runtime_state(app: FastAPI, runtime: AppRuntime) -> None:
    """Keep existing route state aliases while exposing the shared runtime."""
    app.state.runtime = runtime
    app.state.blender = runtime.blender
    app.state.scene_operations = runtime.scene_operations
    app.state.batch_transform = runtime.batch_transform
    app.state.scene_export = runtime.scene_export
    app.state.print_readiness = runtime.print_readiness
    app.state.event_bus = runtime.event_bus
    app.state.adapter_factory = runtime.adapter_factory
    app.state.sandbox = runtime.sandbox
    app.state.sanitizer = runtime.sanitizer
    app.state.vision = runtime.vision
    app.state.prompt_builder = runtime.prompt_builder
    app.state.session_store = runtime.session_store
    app.state.snapshot_store = runtime.snapshot_store
    app.state.polyhaven = runtime.polyhaven
    app.state.text3d = runtime.text3d
    app.state.conversational_modeling = runtime.conversational_modeling
    app.state.modeling_pipeline = runtime.modeling_pipeline
    app.state.iterative_refinement = runtime.iterative_refinement
    app.state.ws_manager = ConnectionManager()


def _register_domain_error_handlers(app: FastAPI) -> None:
    """Map domain exceptions to HTTP status in exactly one place.

    Registration order does not matter, but *specificity* does: Starlette walks
    ``type(exc).__mro__`` and takes the first registered class it finds. Because
    ``BlenderConnectionError`` and ``LLMConnectionError`` inherit from
    ``DomainError`` directly, they are found before the base class and keep their
    503. Registering only ``DomainError`` would silently collapse every 503 into
    a 422 — ``tests/e2e/test_rest_error_contract.py`` asserts the hierarchy this
    depends on, so the assumption cannot rot unnoticed.

    Scope: this owns the *domain* mapping only. Endpoint-owned guards — a missing
    adapter, an unknown snapshot, an oversized upload — stay in their endpoint,
    where the status is a real decision rather than a translation.

    ``/ws/chat`` is deliberately not covered: Starlette's exception middleware is
    HTTP-only, so a WebSocket route never reaches these handlers.
    """

    async def _unavailable(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    async def _unprocessable(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    app.add_exception_handler(BlenderConnectionError, _unavailable)
    app.add_exception_handler(LLMConnectionError, _unavailable)
    app.add_exception_handler(DomainError, _unprocessable)


def create_app(
    cors_origins: list[str] | None = None,
    env_file: Path | None = None,
    require_identity: bool | None = None,
    runtime: AppRuntime | None = None,
) -> FastAPI:
    """Create an API whose REST, WebSocket, and MCP adapters share one runtime."""
    origins = _origins(cors_origins)
    shared_runtime = runtime or build_runtime(env_file)
    mcp = create_mcp_server(
        shared_runtime.scene_operations,
        shared_runtime.scene_operations,
        shared_runtime.print_readiness,
    )

    allowed_hosts = {"127.0.0.1", "localhost"}
    for origin in origins:
        hostname = urlparse(origin).hostname
        if hostname is not None:
            allowed_hosts.add(hostname)

    mcp_app = mcp.http_app(
        path="/",
        stateless_http=True,
        host_origin_protection=True,
        allowed_hosts=sorted(allowed_hosts),
        allowed_origins=origins,
    )
    app = FastAPI(
        title="Blender MCP Studio API",
        description="Conversational 3D creation via Blender + MCP + LLM",
        version=PROJECT_VERSION,
        lifespan=combine_lifespans(_lifespan, mcp_app.lifespan),
    )
    app.state.env_file = env_file
    app.state.mcp_server = mcp
    _publish_runtime_state(app, shared_runtime)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(_NormalizeMcpPath)
    if _identity_required(require_identity):
        from api.require_identity import RequireTailnetIdentity

        app.add_middleware(RequireTailnetIdentity)

    _register_domain_error_handlers(app)

    app.include_router(chat.router)
    app.include_router(scene.router)
    app.include_router(objects.router)
    app.include_router(history.router)
    app.include_router(snapshots.router)
    app.include_router(materials.router)
    app.include_router(vision.router)
    app.include_router(pipelines.router)
    app.include_router(generate3d.router)
    app.include_router(batch_transform.router)
    app.include_router(scene_export.router)
    app.include_router(print_readiness.router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        blender_state = "unknown"
        try:
            blender_state = (
                "connected" if await shared_runtime.blender.is_connected() else "disconnected"
            )
        except Exception:
            blender_state = "disconnected"
        return {"status": "ok", "blender": blender_state}

    app.mount("/mcp", mcp_app)
    return app


app = create_app()
