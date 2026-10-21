"""Slicing request/result records and tool availability (no I/O, no subprocess)."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.domain.exceptions import DomainError
from src.core.domain.model_spec import PrintTarget


class ToolUnavailableError(DomainError):
    """An external tool the pipeline needs is not installed or not executable."""


@dataclass(frozen=True, slots=True)
class SliceRequest:
    input_3mf: str
    output_dir: str
    printer: str
    material: str
    layer_height_mm: float
    support: bool
    brim_mm: float

    @classmethod
    def from_target(cls, input_3mf: str, output_dir: str, target: PrintTarget) -> SliceRequest:
        """The one place a ``PrintTarget`` becomes a slice request (print defaults live there)."""
        return cls(
            input_3mf=input_3mf,
            output_dir=output_dir,
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
class SupportedTargets:
    """Printer ids and materials the slicer has profiles for (checked at spec submit)."""

    printers: tuple[str, ...]
    materials: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ToolAvailability:
    name: str
    available: bool
    path: str | None
    version: str | None
    install_hint: str
