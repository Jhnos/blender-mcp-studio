"""Blender adapter factory — keeps main.py free of concrete imports.

Supported transports (set via BLENDER_TRANSPORT env var):
  - socket  (default): raw TCP socket protocol used by ahujasid/blender-mcp
  - mcp_sse: official MCP SDK SSE/HTTP transport (for FastMCP-based servers)

Usage:
    from src.adapters.mcp.factory import build_blender_adapter
    blender = build_blender_adapter()
    await blender.connect()
"""

from __future__ import annotations

import os

from src.core.ports.blender_port import BlenderPort
from src.core.ports.code_sandbox_port import CodeSandboxPort


def build_blender_adapter(
    host: str | None = None,
    port: int | None = None,
    sandbox: CodeSandboxPort | None = None,
) -> BlenderPort:
    """Instantiate a BlenderPort from environment config.

    Args:
        host: Override BLENDER_HOST env var.
        port: Override BLENDER_PORT env var.
        sandbox: Optional CodeSandboxPort to validate execute_code calls.
    """
    transport = os.environ.get("BLENDER_TRANSPORT", "socket").lower()

    if transport == "mcp_sse":
        from src.adapters.mcp.mcp_client_adapter import MCPClientBlenderAdapter
        sse_url = os.environ.get("BLENDER_MCP_SSE_URL", "http://localhost:8765/sse")
        return MCPClientBlenderAdapter(sse_url=sse_url)

    # Default: raw TCP socket (compatible with ahujasid/blender-mcp add-on)
    from src.adapters.mcp.blender_mcp_adapter import BlenderMCPAdapter
    _host = host or os.environ.get("BLENDER_HOST", "localhost")
    _port = port or int(os.environ.get("BLENDER_PORT", "9876"))
    return BlenderMCPAdapter(host=_host, port=_port, sandbox=sandbox)