"""Blender MCP adapter — wraps socket communication with ahujasid/blender-mcp addon."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from src.core.domain.command import Command
from src.core.domain.exceptions import BlenderConnectionError
from src.core.ports.blender_port import BlenderPort
from src.core.ports.mcp_port import MCPPort, ToolDefinition, ToolResult
from src.infrastructure.env_loader import get


class BlenderSocketClient:
    """Low-level TCP socket client for the Blender MCP addon (ahujasid protocol).

    Protocol (from addon source):
      - Send: raw JSON bytes (no newline), e.g. {"type": "execute_code", "params": {"code": "..."}}
      - Recv: raw JSON bytes (no newline terminator) — buffer until parseable
    """

    def __init__(self, host: str, port: int, timeout: float = 30.0) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def connect(self) -> None:
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=10.0,
            )
        except (ConnectionRefusedError, asyncio.TimeoutError, OSError) as e:
            raise BlenderConnectionError(
                f"Cannot connect to Blender at {self._host}:{self._port}"
            ) from e

    async def disconnect(self) -> None:
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
            self._writer = None
            self._reader = None

    async def send_command(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send JSON payload and recv until we have a complete JSON response."""
        if not self._writer or not self._reader:
            raise BlenderConnectionError("Not connected to Blender.")

        data = json.dumps(payload).encode("utf-8")
        self._writer.write(data)
        await self._writer.drain()

        raw = b""
        async with asyncio.timeout(self._timeout):
            while True:
                chunk = await self._reader.read(4096)
                if not chunk:
                    break
                raw += chunk
                try:
                    return json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
        return json.loads(raw.decode("utf-8"))

    @property
    def is_connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()


class BlenderMCPClient(MCPPort):
    """MCPPort implementation over the BlenderSocketClient.

    Single responsibility: translate MCPPort calls to socket addon protocol.
    Composition over multiple inheritance — BlenderMCPAdapter uses this.
    """

    # Known addon tools (addon has no list_tools endpoint)
    _KNOWN_TOOLS = [
        "get_scene_info", "get_object_info", "execute_code",
        "get_viewport_screenshot",
    ]

    def __init__(self, socket: BlenderSocketClient) -> None:
        self._socket = socket

    async def call_tool(
        self, tool_name: str, arguments: dict[str, object]
    ) -> ToolResult:
        try:
            response = await self._socket.send_command(
                {"type": tool_name, "params": arguments}
            )
            if response.get("status") == "error":
                return ToolResult(
                    success=False,
                    output=None,
                    error=response.get("message", "Unknown Blender error"),
                )
            return ToolResult(
                success=True,
                output=response.get("result") or response,
                error=None,
            )
        except BlenderConnectionError:
            raise
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    async def list_tools(self) -> list[ToolDefinition]:
        return [ToolDefinition(name=t, description=t) for t in self._KNOWN_TOOLS]

    async def connect(self) -> None:
        await self._socket.connect()

    async def disconnect(self) -> None:
        await self._socket.disconnect()

    @property
    def is_connected(self) -> bool:
        return self._socket.is_connected


class BlenderMCPAdapter(BlenderPort):
    """BlenderPort implementation — composes BlenderMCPClient (MCPPort).

    Single responsibility: translate BlenderPort calls to MCP tool calls.
    Does NOT inherit MCPPort — uses composition instead.
    """

    def __init__(self, host: str, port: int) -> None:
        self._socket = BlenderSocketClient(host, port)
        self._mcp = BlenderMCPClient(self._socket)

    async def connect(self) -> None:
        await self._socket.connect()

    async def disconnect(self) -> None:
        await self._socket.disconnect()

    async def execute(self, command: Command) -> ToolResult:
        return await self._mcp.call_tool(command.tool_name, dict(command.arguments))

    async def call_tool(
        self, tool_name: str, arguments: dict[str, object]
    ) -> ToolResult:
        """Expose MCP tool calls for routers that need direct access."""
        return await self._mcp.call_tool(tool_name, arguments)

    async def get_scene_info(self) -> dict[str, object]:
        result = await self._mcp.call_tool("get_scene_info", {})
        return result.output if isinstance(result.output, dict) else {}

    async def is_connected(self) -> bool:
        return self._socket.is_connected

