"""Unit tests for MCPClientBlenderAdapter and MCP factory transport selection."""

from __future__ import annotations

import pytest


def test_factory_returns_socket_adapter_by_default(monkeypatch):
    """Factory returns BlenderMCPAdapter when BLENDER_TRANSPORT is not set."""
    monkeypatch.delenv("BLENDER_TRANSPORT", raising=False)
    monkeypatch.setenv("BLENDER_HOST", "localhost")
    monkeypatch.setenv("BLENDER_PORT", "9876")

    from src.adapters.mcp.blender_mcp_adapter import BlenderMCPAdapter
    from src.adapters.mcp.factory import build_blender_adapter

    adapter = build_blender_adapter()
    assert isinstance(adapter, BlenderMCPAdapter)


def test_factory_returns_socket_adapter_explicitly(monkeypatch):
    """Factory returns socket adapter when BLENDER_TRANSPORT=socket."""
    monkeypatch.setenv("BLENDER_TRANSPORT", "socket")

    from src.adapters.mcp.blender_mcp_adapter import BlenderMCPAdapter
    from src.adapters.mcp.factory import build_blender_adapter

    adapter = build_blender_adapter()
    assert isinstance(adapter, BlenderMCPAdapter)


def test_factory_preserves_registered_script_deadlines(monkeypatch):
    monkeypatch.setenv("BLENDER_TRANSPORT", "socket")
    from src.adapters.mcp.blender_mcp_adapter import BlenderMCPAdapter
    from src.adapters.mcp.factory import build_blender_adapter

    adapter = build_blender_adapter(script_timeouts={"registered": 0.5})
    assert isinstance(adapter, BlenderMCPAdapter)
    assert adapter._mcp._script_timeouts == {"registered": 0.5}
    assert adapter._socket._timeout == 30.0


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
async def test_mcp_client_adapter_scene_query_fails_loudly_when_unreachable():
    """An unreachable transport is a SceneOperationError, never an empty scene (D-001)."""
    from src.adapters.mcp.mcp_client_adapter import MCPClientBlenderAdapter
    from src.core.domain.exceptions import SceneOperationError

    adapter = MCPClientBlenderAdapter(sse_url="http://localhost:19999/sse")

    with pytest.raises(SceneOperationError):
        await adapter.scene_summary()


def test_mcp_client_adapter_implements_blender_port():
    """MCPClientBlenderAdapter satisfies BlenderPort interface."""
    from src.adapters.mcp.mcp_client_adapter import MCPClientBlenderAdapter
    from src.core.ports.blender_port import BlenderPort

    adapter = MCPClientBlenderAdapter()
    assert isinstance(adapter, BlenderPort)


@pytest.mark.parametrize("phase", ["initialize", "call"])
async def test_sse_distinguishes_unsent_failure_from_uncertain_dispatch(monkeypatch, phase):
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock

    from src.adapters.mcp.leased_blender import LeasedBlenderPort
    from src.adapters.mcp.mcp_client_adapter import MCPClientBlenderAdapter
    from src.core.domain.exceptions import BlenderExecutionUncertainError
    from src.core.use_cases.blender_lease import BlenderLease

    session = AsyncMock()
    getattr(
        session, "initialize" if phase == "initialize" else "call_tool"
    ).side_effect = TimeoutError("lost reply")

    @asynccontextmanager
    async def transport(*args):
        yield (None, None)

    @asynccontextmanager
    async def context(*args):
        yield session

    monkeypatch.setattr("mcp.client.sse.sse_client", transport)
    monkeypatch.setattr("mcp.client.session.ClientSession", context)
    lease = BlenderLease()
    port = LeasedBlenderPort(MCPClientBlenderAdapter(), lease)
    if phase == "call":
        with pytest.raises(BlenderExecutionUncertainError):
            await port.call_tool("execute_code", {"code": "pass"})
        assert lease.busy
    else:
        result = await port.call_tool("execute_code", {"code": "pass"})
        assert not result.success and not lease.busy
        session.call_tool.assert_not_awaited()
