"""Per-job slicing rules shared by every slicer: request-derived process keys, readable failure
messages, and the diagnostics kept from a failed run. No subprocess here."""

from __future__ import annotations

import shutil
from pathlib import Path

from src.core.domain.printer_catalog import ExitCode, SlicerSpec
from src.core.domain.slicing import SliceRequest

LOG_TAIL_LINES = 20
DATADIR_LOGS = "slicer-datadir-logs"


def _fmt_mm(value: float) -> str:
    return repr(float(value))


def job_process_keys(request: SliceRequest) -> dict[str, str]:
    """Process keys derived from the job, written over the bundle profile and any overrides.

    The same rules hold for every printer and vendor.
    """
    keys = {
        "layer_height": _fmt_mm(request.layer_height_mm),
        "brim_width": _fmt_mm(request.brim_mm),
        "enable_support": "1" if request.support else "0",
        # A prime/wipe tower only purges between filament changes, and a request carries one
        # material, so one filament profile: no tower. Multi-material support must revisit
        # this rule.
        "enable_prime_tower": "0",
    }
    if request.support:
        # Dense single-plate layouts conflict with default/tree supports — v80 and 2026-10-22
        # K1 Max evidence (OrcaSlicer 2.4.2 exited -101 CLI_GCODE_PATH_CONFLICTS with the
        # Creality default style; normal + snug sliced the v78 69-part plate).
        keys.update(support_type="normal(auto)", support_style="snug")
    return keys


def log_tail(log_path: Path) -> str:
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-LOG_TAIL_LINES:])


def exit_code(slicer: SlicerSpec, rc: int) -> ExitCode | None:
    """The documented exit code for ``rc``; a shell reports a negative code modulo 256."""
    table = {entry.code: entry for entry in slicer.error_codes}
    return table.get(rc, table.get(rc - 256))


def exit_head(slicer: SlicerSpec, rc: int) -> str:
    """``slicer exited 155 (CLI_GCODE_PATH_CONFLICTS: G-code path conflicts). <slicer's hint>``"""
    entry = exit_code(slicer, rc)
    if entry is None:
        return f"slicer exited {rc}"
    label = f"{entry.name}: {entry.meaning}" if entry.name else entry.meaning
    head = f"slicer exited {rc} ({label})"
    return f"{head}. {slicer.name}: {entry.hint}" if entry.hint else head


def with_notes(message: str, notes: tuple[str, ...]) -> str:
    return message if not notes else f"{message}; notes: {'; '.join(notes)}"


def failure(head: str, notes: tuple[str, ...], log_path: Path) -> str:
    """Why first, then notes, then the last log lines (the log tail always ends the message)."""
    return f"{with_notes(head, notes)}; log tail:\n{log_tail(log_path)}"


def keep_datadir_logs(datadir: Path, out: Path) -> None:
    """Copy the slicer's own ``*.log`` files out of its temporary datadir before it is removed.

    OrcaSlicer 2.4.2 on macOS wrote one line to stdout for a failed run even at ``--debug 3``
    (2026-10-22), so its datadir log is the only detail a later diagnosis can have.
    """
    logs = sorted(p for p in datadir.rglob("*.log") if p.is_file())
    if not logs:
        return
    kept = out / DATADIR_LOGS
    kept.mkdir(exist_ok=True)
    for log in logs:
        shutil.copyfile(log, kept / log.name)
