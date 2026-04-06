"""Unit tests for MCPClientBlenderAdapter and MCP factory transport selection."""

from __future__ import annotations

import os
import pytest


def test_factory_returns_socket_adapter_by_default(monkeypatch):
    """Factory returns BlenderMCPAdapter when BLENDER_TRANSPORT is not set."""
    monkeypatch.delenv("BLENDER_TRANSPORT", raising=False)
    monkeypatch.setenv("BLENDER_HOST", "localhost")
    monkeypatch.setenv("BLENDER_PORT", "9876")

    from src.adapters.mcp.factory import build_blender_adapter
    from src.adapters.mcp.blender_mcp_adapter import BlenderMCPAdapter

    adapter = build_blender_adapter()
    assert isinstance(adapter, BlenderMCPAdapter)


def test_factory_returns_socket_adapter_explicitly(monkeypatch):
    """Factory returns socket adapter when BLENDER_TRANSPORT=socket."""
    monkeypatch.setenv("BLENDER_TRANSPORT", "socket")

    from src.adapters.mcp.factory import build_blender_adapter
    from src.adapters.mcp.blender_mcp_adapter import BlenderMCPAdapter

    adapter = build_blender_adapter()
    assert isinstance(adapter, BlenderMCPAdapter)


def test_factory_returns_mcp_client_adapter(monkeypatch):
    """Factory returns MCPClientBlenderAdapter when BLENDER_TRANSPORT=mcp_sse."""
    monkeypatch.setenv("BLENDER_TRANSPORT", "mcp_sse")
    monkeypatch.setenv("BLENDER_MCP_SSE_URL", "http://testserver:8765/sse")

    from src.adapters.mcp.factory import build_blender_adapter
    from src.adapters.mcp.mcp_client_adapter import MCPClientBlenderAdapter

    adapter = build_blender_adapter()
    assert isinstance(adapter, MCPClientBlenderAdapter)
    assert adapter._sse_url == "http://testserver:8765/sse"


def test_mcp_client_adapter_default_sse_url(monkeypatch):
    """MCPClientBlenderAdapter uses default SSE URL if not configured."""
    from src.adapters.mcp.mcp_client_adapter import MCPClientBlenderAdapter

    adapter = MCPClientBlenderAdapter()
    assert "localhost" in adapter._sse_url
    assert "8765" in adapter._sse_url


@pytest.mark.asyncio
async def test_mcp_client_adapter_connect_fails_gracefully():
    """MCPClientBlenderAdapter.connect() doesn't raise if server unreachable."""
    from src.adapters.mcp.mcp_client_adapter import MCPClientBlenderAdapter

    adapter = MCPClientBlenderAdapter(sse_url="http://localhost:19999/sse")
    await adapter.connect()  # should NOT raise
    assert await adapter.is_connected() is False


@pytest.mark.asyncio
async def test_mcp_client_adapter_call_tool_returns_error_when_disconnected():
    """MCPClientBlenderAdapter._call_tool returns error ToolResult when server down."""
    from src.adapters.mcp.mcp_client_adapter import MCPClientBlenderAdapter
    from src.core.domain.command import Command

    adapter = MCPClientBlenderAdapter(sse_url="http://localhost:19999/sse")
    command = Command(tool_name="get_scene_info", arguments={})
    result = await adapter.execute(command)

    assert result.success is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_mcp_client_adapter_get_scene_returns_empty_on_failure():
    """MCPClientBlenderAdapter.get_scene_info returns empty dict on connection failure."""
    from src.adapters.mcp.mcp_client_adapter import MCPClientBlenderAdapter

    adapter = MCPClientBlenderAdapter(sse_url="http://localhost:19999/sse")
    info = await adapter.get_scene_info()

    assert isinstance(info, dict)


def test_mcp_client_adapter_implements_blender_port():
    """MCPClientBlenderAdapter satisfies BlenderPort interface."""
    from src.adapters.mcp.mcp_client_adapter import MCPClientBlenderAdapter
    from src.core.ports.blender_port import BlenderPort

    adapter = MCPClientBlenderAdapter()
    assert isinstance(adapter, BlenderPort)
