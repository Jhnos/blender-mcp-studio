"""Per-job slicing rules shared by every slicer: request-derived process keys, the command line
and its logged run, readable failure messages, and the diagnostics kept from a failed run.
"""

from __future__ import annotations

import shutil
import signal
import subprocess
from collections.abc import Callable
from pathlib import Path

from src.core.domain.printer_catalog import ExitCode, PrinterProfile, SlicerSpec
from src.core.domain.slicing import SliceRequest

LOG_TAIL_LINES = 20
DATADIR_LOGS = "slicer-datadir-logs"


def _fmt_mm(value: float) -> str:
    return repr(float(value))


def job_process_keys(request: SliceRequest, *, inspected: bool) -> dict[str, str]:
    """Process keys derived from the job, written over the bundle profile and any overrides.

    The same rules hold for every printer and vendor. ``inspected`` is the slicer's catalog
    ``toolpath_inspection`` flag: when its output is inspected, arc fitting is off.
    """
    keys = {
        "layer_height": _fmt_mm(request.layer_height_mm),
        "brim_width": _fmt_mm(request.brim_mm),
        "brim_type": "outer_only" if request.brim_mm > 0 else "no_brim",
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
    if inspected:
        # Re-fitted arcs from a CLI re-slice exceeded the inspector's arc-radius disagreement
        # threshold on real output (main, LESSONS 2026-11 "製造設定檔可正常切片，輸出仍可能超出
        # 驗證器支援的數值範圍"); straight segments keep the output inspectable.
        keys["enable_arc_fitting"] = "0"
    return keys


def slicer_argv(
    binary: Path, printer: PrinterProfile, request: SliceRequest, export: str, datadir: str
) -> list[str]:
    """The v80-proven command line (every Orca-family slicer takes the same flags).

    Every path is absolute (resolved), so the slicer never depends on the caller's cwd.
    """
    out = Path(request.output_dir).resolve()
    return [
        str(binary.resolve()),
        "--datadir",
        datadir,
        "--debug",
        "3",  # info: at 2 a failed OrcaSlicer run logs only "run found error, exit"
        "--load-settings",
        f"{out / 'machine.json'};{out / 'process.json'}",
        "--load-filaments",
        str(out / "filament.json"),
        "--curr-bed-type",
        printer.bed_type,
        "--arrange",
        "0",
        "--orient",
        "0",
        "--slice",
        "0",
        "--outputdir",
        str(out),
        "--export-3mf",
        export,
        "--export-settings",
        str(out / "effective-settings.json"),
        str(Path(request.input_3mf).resolve()),
    ]


def run_logged(
    runner: Callable[..., subprocess.CompletedProcess[str]],
    argv: list[str],
    log_path: Path,
    timeout_s: float,
) -> subprocess.CompletedProcess[str]:
    """Run the slicer with stdout and stderr in ``log_path`` (blocking: call it in a thread).

    The working directory is the output dir, so a sidecar the slicer writes next to itself
    (``result.json``) stays inside the job.
    """
    with log_path.open("w", encoding="utf-8") as log:
        return runner(
            argv,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_s,
            cwd=log_path.parent.resolve(),
        )


def log_tail(log_path: Path) -> str:
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-LOG_TAIL_LINES:])


def exit_code(slicer: SlicerSpec, rc: int) -> ExitCode | None:
    """The documented code behind exit status ``rc``.

    The CLIs ``exit()`` negative codes, which the OS reports modulo 256 (-101 -> 155), so only
    128 < rc < 256 is looked up, as ``rc - 256``. A negative ``rc`` from ``subprocess`` is a
    signal death, never a CLI code.
    """
    if not 128 < rc < 256:
        return None
    return next((entry for entry in slicer.error_codes if entry.code == rc - 256), None)


def exit_head(slicer: SlicerSpec, rc: int) -> str:
    """``slicer exited 155 (CLI_GCODE_PATH_CONFLICTS: G-code path conflicts). <slicer's hint>``"""
    if rc < 0:
        try:
            name = signal.Signals(-rc).name
        except ValueError:
            name = "unknown signal"
        return f"slicer was killed by signal {-rc} ({name})"
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
        target = kept / log.relative_to(datadir)  # same-named logs in two dirs both survive
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(log, target)
