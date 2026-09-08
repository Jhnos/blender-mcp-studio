"""Blender Port — abstract interface for Blender scene operations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.domain.command import Command
from src.core.domain.scene_operations import ObjectDetails, SceneSummary, ViewportImage
from src.core.ports.mcp_port import ToolResult


class BlenderPort(ABC):
    """High-level abstract interface for Blender 3D scene manipulation.

    The contract declares everything consumers actually call. connect /
    disconnect / call_tool were used by api.main and the preview/refinement
    use cases while missing from this interface — the port under-declared what
    it promised, so type checking could not see those calls at all.

    Scene queries come back as domain DTOs, never as the addon's raw mapping.
    Decoding the addon's dialect is the adapter's job (DEFERRALS D-001): when
    the port returned `object`, the use case had to narrow it, duplicating the
    predicates the adapters already had.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Open the connection to Blender."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the connection to Blender."""

    @abstractmethod
    async def execute(self, command: Command) -> ToolResult:
        """Execute a Command in Blender and return the result."""

    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: dict[str, object]) -> ToolResult:
        """Invoke a Blender MCP tool directly by name."""

    @abstractmethod
    async def scene_summary(self) -> SceneSummary:
        """The current scene, decoded; raises SceneOperationError on an unusable reply."""

    @abstractmethod
    async def object_details(self, name: str) -> ObjectDetails:
        """One object's transforms, visibility and materials, decoded."""

    @abstractmethod
    async def viewport_screenshot(self, max_size: int = 800) -> ViewportImage:
        """A PNG of the viewport, bounded to `max_size` on its longer side."""

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if the Blender socket connection is alive."""
