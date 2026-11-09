"""What this host can slice for, as facts an LLM can choose a printer from.

Usable printers carry the machine limits (bed, height, layer range) the slicing port reads from
the installed profiles; printers whose slicer is not usable, or whose bundle profiles cannot be
read, are named with the reason and install hint instead of being silently left out. No path
and no default choice is produced here.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from src.core.domain.printer_catalog import PrinterProfile
from src.core.domain.slicing import MachineFacts
from src.core.ports.slicing_port import SlicingPort


@dataclass(frozen=True, slots=True)
class PrinterEntry:
    printer: PrinterProfile
    layer_range: tuple[float, float] | None  # machine (min, max) mm; None = not declared
    bed_mm: tuple[float, float, float] | None  # width, depth, printable height
    slicer_id: str  # the catalog slicer id, as tool_status and the package manifest name it
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


def readable(
    slicing: SlicingPort, facts: Mapping[str, MachineFacts | str]
) -> tuple[tuple[PrinterProfile, MachineFacts], ...]:
    """Usable printers whose machine profile could be read, with its facts (catalog order)."""
    pairs = ((p, facts.get(p.id)) for p in slicing.printers())
    return tuple((p, known) for p, known in pairs if isinstance(known, MachineFacts))


async def list_printers(
    slicing: SlicingPort, clean: Callable[[str], Awaitable[str]]
) -> PrinterListing:
    """Every catalog printer, split into usable here (with facts) and not (with the reason).

    ``clean`` strips host paths from a reason (the pipeline's single scrub point).
    """
    facts = await asyncio.to_thread(slicing.machine_facts)
    entries = []
    for p, known in readable(slicing, facts):
        tool = slicing.tool_for(p.id)
        name = slicing.slicer_name(p.id)
        entries.append(
            PrinterEntry(p, known.layer_range, known.bed_mm, tool.name, name, tool.version)
        )
    have = {e.printer.id for e in entries}
    hints = {tool.name: tool.install_hint for tool in await slicing.availability()}
    missing = []
    for p in slicing.catalog_printers():
        if p.id in have:
            continue
        error = facts.get(p.id)
        if isinstance(error, str):
            reason = await clean(f"{p.id}: its bundle profiles cannot be read: {error}")
        else:
            reason = f"{slicing.slicer_name(p.id)} is not installed or not usable on this host"
        hint = hints.get(slicing.tool_for(p.id).name, "")
        missing.append(UnavailablePrinter(p.id, reason, hint))
    return PrinterListing(tuple(entries), tuple(missing))
