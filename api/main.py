"""FastAPI application entry point.

Use create_app() for library integration:
    from api.main import create_app
    app = create_app(cors_origins=["https://myapp.com"])
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import chat, scene


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Startup/shutdown: load env once, init shared adapters and event bus."""
    from src.infrastructure.env_loader import load_env
    from src.adapters.mcp.factory import build_blender_adapter
    from src.adapters.factory.concrete_adapter_factory import ConcreteAdapterFactory
    from src.adapters.events.in_memory_event_bus import InMemoryEventBus

    env_file = app.state.env_file if hasattr(app.state, "env_file") else None
    load_env(env_file)

    blender = build_blender_adapter()
    try:
        await blender.connect()
    except Exception:
        pass  # Blender may not be running at startup

    event_bus = InMemoryEventBus()
    adapter_factory = ConcreteAdapterFactory()

    app.state.blender = blender
    app.state.event_bus = event_bus
    app.state.adapter_factory = adapter_factory
    yield
    await blender.disconnect()


def create_app(
    cors_origins: list[str] | None = None,
    env_file: Path | None = None,
) -> FastAPI:
    """Factory — safe to import as a library.

    Args:
        cors_origins: Allowed CORS origins. Defaults to CORS_ORIGINS env var.
        env_file: Path to .env file. Defaults to project-root .env.
    """
    origins = cors_origins or [
        o.strip()
        for o in os.environ.get(
            "CORS_ORIGINS", "http://localhost:19147,http://localhost:3000"
        ).split(",")
        if o.strip()
    ]

    app = FastAPI(
        title="Blender MCP Studio API",
        description="Conversational 3D creation via Blender + MCP + LLM",
        version="0.1.0",
        lifespan=_lifespan,
    )
    app.state.env_file = env_file

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat.router)
    app.include_router(scene.router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


# Module-level app for uvicorn entry point
app = create_app()
