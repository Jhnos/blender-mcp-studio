"""MCPClientBlenderAdapter — uses the official MCP SDK for SSE/HTTP transport.

This adapter connects to any MCP-compliant server (including blender-mcp when
run with SSE transport, or any FastMCP-based Blender server) using the official
Model Context Protocol Python SDK.

Transport: HTTP/SSE (server-sent events) — standard MCP transport.
Fallback: The original BlenderMCPAdapter (raw TCP socket) remains the default.

Usage (configure via environment):
    BLENDER_TRANSPORT=mcp_sse
    BLENDER_MCP_SSE_URL=http://localhost:8765/sse

Architecture: Implements BlenderPort — zero changes in use cases or routers.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.core.domain.command import Command
from src.core.ports.blender_port import BlenderPort
from src.core.ports.mcp_port import ToolResult

logger = logging.getLogger(__name__)


class MCPClientBlenderAdapter(BlenderPort):
    """BlenderPort implementation via MCP SDK SSE client.

    Connects to an MCP server that exposes Blender tools (e.g., a FastMCP-based
    server or blender-mcp running in SSE mode).

    Falls back gracefully: if the MCP server is unreachable, operations return
    error ToolResults without raising exceptions.
    """

    def __init__(self, sse_url: str = "http://localhost:8765/sse") -> None:
        self._sse_url = sse_url
        self._connected = False
        self._available_tools: list[str] = []

    async def connect(self) -> None:
        """Probe the MCP server to verify connectivity and list available tools."""
        try:
            tools = await self._list_tools()
            self._available_tools = [t.name for t in tools]
            self._connected = True
            logger.info(
                "MCPClientBlenderAdapter connected to %s — %d tools available: %s",
                self._sse_url,
                len(self._available_tools),
                self._available_tools,
            )
        except Exception as e:
            self._connected = False
            logger.warning("MCPClientBlenderAdapter: cannot connect to %s — %s", self._sse_url, e)

    async def disconnect(self) -> None:
        self._connected = False

    async def is_connected(self) -> bool:
        return self._connected

    async def get_scene_info(self) -> dict:
        result = await self._call_tool("get_scene_info", {})
        if result.success and result.output:
            try:
                return json.loads(result.output)
            except json.JSONDecodeError:
                return {"raw": result.output}
        return {}

    async def execute(self, command: Command) -> ToolResult:
        return await self._call_tool(command.tool_name, dict(command.arguments))

    async def call_tool(self, tool_name: str, arguments: dict) -> ToolResult:
        return await self._call_tool(tool_name, arguments)

    # ------------------------------------------------------------------
    # Internal: MCP SDK calls
    # ------------------------------------------------------------------

    async def _list_tools(self) -> list[Any]:
        """List tools available on the MCP server."""
        from mcp.client.session import ClientSession
        from mcp.client.sse import sse_client

        async with sse_client(self._sse_url) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return result.tools

    async def _call_tool(self, tool_name: str, arguments: dict) -> ToolResult:
        """Call a tool on the MCP server and return the result."""
        from mcp.client.session import ClientSession
        from mcp.client.sse import sse_client

        try:
            async with sse_client(self._sse_url) as (read, write), ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)

                if result.isError:
                    error_text = " ".join(
                        c.text for c in result.content if hasattr(c, "text")
                    )
                    return ToolResult(success=False, output=None, error=error_text)

                output_text = " ".join(
                    c.text for c in result.content if hasattr(c, "text")
                )
                return ToolResult(success=True, output=output_text, error=None)

        except Exception as e:
            logger.error("MCPClientBlenderAdapter._call_tool(%s) failed: %s", tool_name, e)
            self._connected = False
            return ToolResult(success=False, output=None, error=str(e))
