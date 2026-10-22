"""Port for turning a project 3MF into a print-ready 3MF with machine evidence.

Catalog-aware: one port serves every printer in the catalog, each through its own slicer.
"""

from __future__ import annotations

from typing import Protocol

from src.core.domain.packaging import ToolUse
from src.core.domain.printer_catalog import PrinterProfile
from src.core.domain.slicing import SliceRequest, SliceResult, ToolAvailability


class SlicingPort(Protocol):
    def printers(self) -> tuple[PrinterProfile, ...]:
        """Catalog printers whose slicer binary is usable on this host (no implicit order)."""
        ...

    async def availability(self) -> tuple[ToolAvailability, ...]:
        """One entry per slicer in the catalog, installed or not."""
        ...

    def timeout_s(self, printer_id: str) -> float:
        """How long one slice on ``printer_id`` may run before the adapter gives up (seconds)."""
        ...

    def max_timeout_s(self) -> float:
        """The largest per-slicer deadline in the catalog, installed or not (seconds)."""
        ...

    async def slice(self, request: SliceRequest) -> SliceResult: ...

    def tool_for(self, printer_id: str) -> ToolUse:
        """The slicer that slices ``printer_id``, as the package manifest records it."""
        ...
