"""MCP Port — abstract interface for MCP tool invocation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolResult:
    success: bool
    output: object
    error: str | None = None


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, object] = field(default_factory=dict)


class MCPPort(ABC):
    """Abstract interface for executing MCP tool calls."""

    @abstractmethod
    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, object],
    ) -> ToolResult:
        """Invoke a named MCP tool with given arguments."""

    @abstractmethod
    async def list_tools(self) -> list[ToolDefinition]:
        """Return all available tools exposed by this MCP server."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the MCP server."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the connection to the MCP server."""
