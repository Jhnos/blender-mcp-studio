"""Port for turning a project 3MF into a print-ready 3MF with machine evidence."""

from __future__ import annotations

from typing import Protocol

from src.core.domain.slicing import SliceRequest, SliceResult, ToolAvailability


class SlicingPort(Protocol):
    @property
    def timeout_s(self) -> float:
        """How long one slice may run before the adapter gives up (seconds)."""
        ...

    async def availability(self) -> ToolAvailability: ...

    async def slice(self, request: SliceRequest) -> SliceResult: ...
