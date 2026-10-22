"""Spec ``print_target`` values <-> catalog printers, checked against the slicer's usable printers.

A spec names its printer either by a catalog id (``creality-k1c-0.4``) or by a spec-v1 name
(``bambu-p2s``), which maps to exactly one catalog id. The v1 table is a translation of the
v1 vocabulary, not a default: nothing here picks a printer the spec did not name.
"""

from __future__ import annotations

from src.core.domain.model_spec import ModelSpecError, PrintTarget
from src.core.domain.printer_catalog import PrinterProfile

#: Spec v1 printer names -> catalog ids (transitional; spec v2 names catalog ids only).
V1_PRINTER_IDS: dict[str, str] = {"bambu-p2s": "bambu-p2s-0.4"}


def printer_id_for(spec_printer: str) -> str:
    """The catalog id a spec printer value names (v1 names translated, ids unchanged)."""
    return V1_PRINTER_IDS.get(spec_printer, spec_printer)


def spec_printer_names(printers: tuple[PrinterProfile, ...]) -> tuple[str, ...]:
    """Each usable printer once, under the name a spec uses for it (v1 name if it has one)."""
    v1_names = {catalog_id: name for name, catalog_id in V1_PRINTER_IDS.items()}
    return tuple(v1_names.get(p.id, p.id) for p in printers)


def materials(printers: tuple[PrinterProfile, ...]) -> tuple[str, ...]:
    """Every material at least one usable printer offers, sorted."""
    return tuple(sorted({material for p in printers for material, _ in p.filaments}))


def check_target(target: PrintTarget, printers: tuple[PrinterProfile, ...]) -> None:
    """Raise ModelSpecError unless the printer is usable here and offers the material."""
    printer_id = printer_id_for(target.printer)
    usable = {p.id: p for p in printers}
    printer = usable.get(printer_id)
    if printer is None:
        names = ", ".join(spec_printer_names(printers))
        raise ModelSpecError(
            f"unsupported print_target.printer {target.printer!r}; supported: {names}"
        )
    offered = [material for material, _ in printer.filaments]
    if target.material not in offered:
        raise ModelSpecError(
            f"unsupported print_target.material {target.material!r}; "
            f"supported: {', '.join(offered)}"
        )
