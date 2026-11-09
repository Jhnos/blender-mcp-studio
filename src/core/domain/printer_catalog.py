"""Printer and slicer catalog: pure data types. No printer is ever chosen implicitly."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.domain.exceptions import DomainError


class UnknownPrinterError(DomainError):
    """A printer id is not in the catalog; the message lists every valid id."""


class UnknownSlicerError(DomainError):
    """A slicer id is not in the catalog."""


@dataclass(frozen=True, slots=True)
class ExitCode:
    """One documented slicer exit code: its source macro name and the slicer's own hint."""

    code: int
    meaning: str
    name: str = ""
    hint: str = ""


@dataclass(frozen=True, slots=True)
class SlicerSpec:
    id: str
    name: str
    binary_key: str
    profiles_subdir: str
    license: str
    error_codes: tuple[ExitCode, ...]
    install_hint: str
    #: Whether a successful slice is followed by the G-code tool-path inspection
    #: (``print/extrusion.json``); catalog data, so no code branches on the vendor.
    toolpath_inspection: bool


@dataclass(frozen=True, slots=True)
class PrinterProfile:
    id: str
    vendor: str
    model: str
    nozzle_mm: float
    slicer: str
    profile_vendor_dir: str
    machine: str
    processes: tuple[tuple[str, str], ...]  # layer height "0.20" -> process profile name
    filaments: tuple[tuple[str, str], ...]  # material "PLA" -> filament profile name
    bed_type: str
    overrides: str | None  # filename under config/slicer-profiles/


@dataclass(frozen=True, slots=True)
class PrinterCatalog:
    printers: tuple[PrinterProfile, ...]
    slicers: tuple[SlicerSpec, ...]

    def printer(self, printer_id: str) -> PrinterProfile:
        for printer in self.printers:
            if printer.id == printer_id:
                return printer
        known = ", ".join(sorted(p.id for p in self.printers))
        raise UnknownPrinterError(f"unknown printer '{printer_id}'; known printers: {known}")

    def slicer(self, slicer_id: str) -> SlicerSpec:
        for slicer in self.slicers:
            if slicer.id == slicer_id:
                return slicer
        known = ", ".join(sorted(s.id for s in self.slicers))
        raise UnknownSlicerError(f"unknown slicer '{slicer_id}'; known slicers: {known}")
