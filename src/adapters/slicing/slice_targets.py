"""Which base process a requested layer height uses, and whether that height is printable.

Pure rules over a catalog printer and its resolved bundle profiles; no binary, no subprocess.
"""

from __future__ import annotations

from src.adapters.slicing.bundle_profiles import check_compatible, layer_range
from src.core.domain.printer_catalog import PrinterProfile
from src.core.domain.slicing import LayerHeightError, TargetCheck


def process_key(printer: PrinterProfile, layer_height_mm: float) -> str:
    """The printer's process profile nearest the requested layer height (a tie takes the lower).

    The request's ``layer_height`` is written over the profile either way, so a 0.28 mm
    request on a printer that offers only "0.20" starts from that profile (v80 behaviour).
    """
    keys = [key for key, _ in printer.processes]
    exact = f"{layer_height_mm:.2f}"
    if exact in keys:
        return exact
    return min(keys, key=lambda key: (round(abs(float(key) - layer_height_mm), 9), float(key)))


def require_in_range(
    printer: PrinterProfile, layer_height_mm: float, bounds: tuple[float, float] | None
) -> None:
    if bounds is None:
        keys = ", ".join(key for key, _ in printer.processes)
        raise LayerHeightError(
            f"layer_height_mm {layer_height_mm:g} is not a process of {printer.id} and its "
            f"machine profile declares no layer-height range; allowed: {keys}"
        )
    low, high = bounds
    if not low - 1e-9 <= layer_height_mm <= high + 1e-9:
        raise LayerHeightError(
            f"layer_height_mm {layer_height_mm:g} is outside {printer.id}'s range "
            f"{low:g}–{high:g} mm"
        )


def check_target(
    printer: PrinterProfile,
    layer_height_mm: float,
    layer: str,
    profiles: dict[str, dict[str, object]],
) -> TargetCheck:
    """Submit-time check on profiles resolved for base process ``layer``.

    A height with an exact ``processes`` key needs no range. Any other height starts from
    the nearest base process and must lie inside the machine profile's declared range; a
    machine that declares none accepts exact keys only.
    """
    if f"{layer_height_mm:.2f}" != layer:
        require_in_range(printer, layer_height_mm, layer_range(profiles["machine"]))
    notes = check_compatible(profiles, printer.machine)  # IncompatibleProfileError
    return TargetCheck(notes, dict(printer.processes)[layer])
