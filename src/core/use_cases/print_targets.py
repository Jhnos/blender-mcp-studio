"""Spec ``print_target`` values <-> catalog printers, checked at submit against this host.

Nothing here picks a printer the spec did not name. The parser already translated a spec v1
printer name to its catalog id (``V1_PRINTER_IDS``); a v1 spec that left printer or material
out was filled by the parser from the legacy values, and ``legacy_note`` says so in the report.
"""

from __future__ import annotations

import asyncio

from src.core.domain.exceptions import DomainError
from src.core.domain.model_spec import ModelSpec, ModelSpecError, PrintTarget
from src.core.domain.printer_catalog import PrinterProfile, UnknownPrinterError
from src.core.domain.slicing import LayerHeightError
from src.core.ports.slicing_port import SlicingPort


def legacy_note(spec: ModelSpec) -> str:
    """The report line for a spec v1 whose missing printer/material were filled; else ``""``."""
    if not spec.legacy_default:
        return ""
    used = ", ".join(f"{key} {value}" for key, value in spec.legacy_defaults)
    return f"spec v1 legacy defaults used: {used}"


async def check_print_target(target: PrintTarget, slicing: SlicingPort) -> PrinterProfile:
    """Raise ModelSpecError unless the target can be sliced on this host; else its printer.

    Fixed order: (1) the printer is in the catalog, (2) its slicer is usable here, (3) the
    printer's catalog offers the material, (4) the bundle's profiles are compatible and the
    layer height is printable (an exact process key, or inside the machine's range). Runs
    before any run directory or job exists.
    """
    try:
        slicer_id = slicing.tool_for(target.printer).name
    except UnknownPrinterError as exc:
        raise ModelSpecError(str(exc)) from exc
    usable = {p.id: p for p in slicing.printers()}
    printer = usable.get(target.printer)
    if printer is None:
        tools = {tool.name: tool for tool in await slicing.availability()}
        hint = tools[slicer_id].install_hint if slicer_id in tools else ""
        raise ModelSpecError(
            f"print_target.printer {target.printer!r} needs "
            f"{slicing.slicer_name(target.printer)}, which is not available on this host. "
            f"{hint}".rstrip()
        )
    materials = [material for material, _ in printer.filaments]
    if target.material not in materials:
        raise ModelSpecError(
            f"unsupported print_target.material {target.material!r} for {printer.id}; "
            f"allowed: {', '.join(materials)}"
        )
    try:
        await asyncio.to_thread(
            slicing.check_target, printer.id, target.layer_height_mm, target.material
        )
    except LayerHeightError as exc:
        raise ModelSpecError(str(exc)) from exc
    except DomainError as exc:
        raise ModelSpecError(f"print_target is not sliceable on {printer.id}: {exc}") from exc
    return printer
