"""Slicing request/result records and tool availability (no I/O, no subprocess)."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.domain.exceptions import DomainError
from src.core.domain.model_spec import PrintTarget


class ToolUnavailableError(DomainError):
    """An external tool the pipeline needs is not installed or not executable."""


@dataclass(frozen=True, slots=True)
class SliceRequest:
    """One slice. ``printer_id`` picks the catalog printer (and so the slicer); ``printer`` is
    the spec's own value, carried for reports. ``material`` keys the printer's filaments."""

    input_3mf: str
    output_dir: str
    printer_id: str
    printer: str
    material: str
    layer_height_mm: float
    support: bool
    brim_mm: float

    @classmethod
    def from_target(
        cls, input_3mf: str, output_dir: str, target: PrintTarget, *, printer_id: str
    ) -> SliceRequest:
        """The one place a ``PrintTarget`` becomes a slice request (print defaults live there)."""
        return cls(
            input_3mf=input_3mf,
            output_dir=output_dir,
            printer_id=printer_id,
            printer=target.printer,
            material=target.material,
            layer_height_mm=target.layer_height_mm,
            support=target.support,
            brim_mm=target.brim_mm,
        )


@dataclass(frozen=True, slots=True)
class SliceResult:
    passed: bool
    output_3mf: str | None
    settings_json: str | None
    log_path: str
    return_code: int
    message: str


@dataclass(frozen=True, slots=True)
class ToolAvailability:
    name: str
    available: bool
    path: str | None
    version: str | None
    install_hint: str
