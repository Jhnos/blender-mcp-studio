"""One mutation boundary for every delivery path, over the existing Blender port."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from src.core.domain.command import Command
from src.core.domain.exceptions import BlenderExecutionUncertainError
from src.core.domain.scene_operations import ObjectDetails, SceneSummary, ViewportImage
from src.core.ports.blender_port import BlenderPort
from src.core.ports.mcp_port import ToolResult
from src.core.use_cases.blender_lease import BlenderLease

T = TypeVar("T")
_READ_ONLY = frozenset({"get_scene_info", "get_object_info", "get_viewport_screenshot"})


class LeasedBlenderPort(BlenderPort):
    def __init__(self, backend: BlenderPort, lease: BlenderLease) -> None:
        self._backend, self._lease = backend, lease

    async def connect(self) -> None:
        await self._backend.connect()

    async def disconnect(self) -> None:
        await self._backend.disconnect()

    async def is_connected(self) -> bool:
        return await self._backend.is_connected()

    async def scene_summary(self) -> SceneSummary:
        return await self._backend.scene_summary()

    async def object_details(self, name: str) -> ObjectDetails:
        return await self._backend.object_details(name)

    async def viewport_screenshot(self, max_size: int = 800) -> ViewportImage:
        return await self._backend.viewport_screenshot(max_size)

    async def execute(self, command: Command) -> ToolResult:
        if command.tool_name in _READ_ONLY:
            return await self._backend.execute(command)
        return await self._mutate(command.tool_name, lambda: self._backend.execute(command))

    async def call_tool(self, tool_name: str, arguments: dict[str, object]) -> ToolResult:
        if tool_name in _READ_ONLY:
            return await self._backend.call_tool(tool_name, arguments)
        return await self._mutate(tool_name, lambda: self._backend.call_tool(tool_name, arguments))

    async def _mutate(self, operation: str, work: Callable[[], Awaitable[T]]) -> T:
        async with self._lease.command(operation):
            try:
                return await work()
            except (asyncio.CancelledError, BlenderExecutionUncertainError):
                self._lease.quarantine()
                raise
