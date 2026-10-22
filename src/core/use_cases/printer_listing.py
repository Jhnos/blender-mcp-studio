"""What this host can slice for, as facts an LLM can choose a printer from.

Usable printers carry the machine limits (bed, height, layer range) the slicing port reads from
the installed profiles; printers whose slicer is not usable are named with the install hint
instead of being silently left out. No path and no default choice is produced here.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from src.core.domain.printer_catalog import PrinterProfile
from src.core.ports.slicing_port import SlicingPort


@dataclass(frozen=True, slots=True)
class PrinterEntry:
    printer: PrinterProfile
    layer_range: tuple[float, float] | None  # machine (min, max) mm; None = not declared
    bed_mm: tuple[float, float, float] | None  # width, depth, printable height
    slicer_name: str
    slicer_version: str | None


@dataclass(frozen=True, slots=True)
class UnavailablePrinter:
    printer_id: str
    reason: str
    install_hint: str


@dataclass(frozen=True, slots=True)
class PrinterListing:
    printers: tuple[PrinterEntry, ...]
    unavailable: tuple[UnavailablePrinter, ...]


async def list_printers(slicing: SlicingPort) -> PrinterListing:
    """Every catalog printer, split into usable here (with facts) and not (with the reason)."""
    usable = slicing.printers()
    ranges, beds = await asyncio.gather(
        asyncio.to_thread(slicing.layer_ranges), asyncio.to_thread(slicing.bed_sizes)
    )
    entries = tuple(
        PrinterEntry(
            p,
            ranges.get(p.id),
            beds.get(p.id),
            slicing.slicer_name(p.id),
            slicing.tool_for(p.id).version,
        )
        for p in usable
    )
    have = {p.id for p in usable}
    hints = {tool.name: tool.install_hint for tool in await slicing.availability()}
    missing = tuple(
        UnavailablePrinter(
            p.id,
            f"{slicing.slicer_name(p.id)} is not installed or not usable on this host",
            hints.get(slicing.tool_for(p.id).name, ""),
        )
        for p in slicing.catalog_printers()
        if p.id not in have
    )
    return PrinterListing(entries, missing)
