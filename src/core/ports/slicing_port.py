"""Port for turning a project 3MF into a print-ready 3MF with machine evidence.

Catalog-aware: one port serves every printer in the catalog, each through its own slicer.
"""

from __future__ import annotations

from typing import Protocol

from src.core.domain.packaging import ToolUse
from src.core.domain.printer_catalog import PrinterProfile
from src.core.domain.slicing import SliceRequest, SliceResult, TargetCheck, ToolAvailability


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

    def slicer_name(self, printer_id: str) -> str:
        """Display name of the slicer that slices ``printer_id`` (installed or not)."""
        ...

    def check_target(self, printer_id: str, layer_height_mm: float, material: str) -> TargetCheck:
        """Resolve the bundle profiles for ``printer_id`` at ``layer_height_mm`` and ``material``
        without slicing. Returns the notes and the base process profile used; raises a
        DomainError when the profiles are missing, not declared compatible, or the height is
        not printable (``LayerHeightError``: outside the machine's range)."""
        ...

    async def slice(self, request: SliceRequest) -> SliceResult: ...

    def tool_for(self, printer_id: str) -> ToolUse:
        """The slicer that slices ``printer_id``, as the package manifest records it."""
        ...
