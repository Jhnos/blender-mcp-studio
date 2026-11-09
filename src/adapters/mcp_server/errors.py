"""Shared MCP error translation and the Blender lease guard (server.py and design_tools.py)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp.exceptions import ToolError

from src.core.domain.design_run import StageName
from src.core.domain.exceptions import BlenderConnectionError, BlenderExecutionUncertainError
from src.core.use_cases.blender_lease import BlenderLease, Holder


def tool_error(exc: Exception) -> ToolError:
    if isinstance(exc, BlenderExecutionUncertainError):
        return ToolError(str(exc))
    if isinstance(exc, BlenderConnectionError):
        return ToolError("Blender is unavailable. Start Blender and enable the addon on port 9876.")
    return ToolError(str(exc))


def busy_message(holder: Holder | None) -> str:
    if isinstance(holder, StageName):
        return f"Blender is busy with design run stage {holder.value}; retry later"
    if holder is None:
        return "Blender is busy with a queued design run; retry later"
    return f"Blender is busy with {holder}; retry later"


def refuse_during_design_stage(lease: BlenderLease) -> None:
    """Scene-changing tools never queue behind a pipeline stage; they say busy at once."""
    if isinstance(lease.holder, StageName):
        raise ToolError(busy_message(lease.holder))


@asynccontextmanager
async def exclusive(lease: BlenderLease, tool: str) -> AsyncIterator[None]:
    """Hold the lease for a long Blender tool so a later pipeline stage waits, not interleaves."""
    async with lease.try_hold(tool) as acquired:
        if not acquired:
            raise ToolError(busy_message(lease.holder))
        yield
