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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp.utilities.lifespan import combine_lifespans

from api.routers import chat, scene
from api.routers.ws_manager import ConnectionManager, viewport_broadcast_loop
from api.runtime import AppRuntime, build_runtime
from src.adapters.mcp_server import create_mcp_server
from src.core.domain.exceptions import BlenderConnectionError

logger = logging.getLogger(__name__)


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
    app.state.ws_manager = ConnectionManager()


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
        version="0.1.0",
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
    if _identity_required(require_identity):
        from api.require_identity import RequireTailnetIdentity

        app.add_middleware(RequireTailnetIdentity)

    app.include_router(chat.router)
    app.include_router(scene.router)

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
