"""Blender Port — abstract interface for Blender scene operations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.domain.command import Command
from src.core.ports.mcp_port import ToolResult


class BlenderPort(ABC):
    """High-level abstract interface for Blender 3D scene manipulation."""

    @abstractmethod
    async def execute(self, command: Command) -> ToolResult:
        """Execute a Command in Blender and return the result."""

    @abstractmethod
    async def get_scene_info(self) -> dict[str, object]:
        """Return metadata about the current Blender scene."""

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if the Blender socket connection is alive."""
