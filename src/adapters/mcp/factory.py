"""Blender adapter factory — keeps main.py free of concrete imports.

Usage:
    from src.adapters.mcp.factory import build_blender_adapter
    blender = build_blender_adapter()
    await blender.connect()
"""

from __future__ import annotations

import os

from src.core.ports.blender_port import BlenderPort


def build_blender_adapter(host: str | None = None, port: int | None = None) -> BlenderPort:
    """Instantiate a BlenderPort from environment config.

    Args:
        host: Override BLENDER_HOST env var.
        port: Override BLENDER_PORT env var.
    """
    from src.adapters.mcp.blender_mcp_adapter import BlenderMCPAdapter
    _host = host or os.environ.get("BLENDER_HOST", "localhost")
    _port = port or int(os.environ.get("BLENDER_PORT", "9876"))
    return BlenderMCPAdapter(host=_host, port=_port)