"""Bambu Studio command-line slicer (AGPL-3.0, subprocess only, never linked).

The command line is the v80-proven form (``tmp/lab-station-slicing-v80/slice_candidate.py``).
Profiles are the P2S/PLA templates in ``config/slicer-profiles`` with per-request overrides
written into ``output_dir``; the slicer's own ``--datadir`` also lives under ``output_dir`` so
the user's real Bambu profile is never read or modified.

Timeout derivation: the slowest measured slice is the v80 69-part plate,
``tmp/lab-station-slicing-v80/first-pass/slicer.log``, first to last log timestamp
2026-10-20 21:10:38.13 -> 21:13:28.78 = 170.6 s. The other v80 runs took 80.6, 101.4, 70.0 and
22.3 s. ``SLICE_TIMEOUT_S`` is five times the slowest measurement (rounded up to 171 s).
"""

from __future__ import annotations

import asyncio
import json
import plistlib
import subprocess
from collections.abc import Callable
from pathlib import Path

from src.core.domain.slicing import (
    SliceRequest,
    SliceResult,
    ToolAvailability,
    ToolUnavailableError,
)
from src.infrastructure.narrowing import as_str_keyed

SLOWEST_SLICE_MEASURED_S = 171
SLICE_TIMEOUT_S = 5 * SLOWEST_SLICE_MEASURED_S

_INSTALL_HINT = (
    "Install BambuStudio.app (https://bambulab.com/download/studio) and set BAMBU_STUDIO_BIN "
    "to its Contents/MacOS/BambuStudio binary."
)
_SUPPORTED_PRINTERS = {"bambu-p2s": "P2S"}
_SUPPORTED_MATERIALS = {"PLA"}
_LOG_TAIL_LINES = 20

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


def _bundle_version(binary: Path) -> str | None:
    """CFBundleShortVersionString of the enclosing .app (the CLI rejects --version)."""
    for parent in binary.parents:
        if parent.suffix == ".app":
            plist = parent / "Contents" / "Info.plist"
            if not plist.is_file():
                return None
            with plist.open("rb") as handle:
                value = plistlib.load(handle).get("CFBundleShortVersionString")
            return value if isinstance(value, str) else None
    return None


def _log_tail(log_path: Path) -> str:
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-_LOG_TAIL_LINES:])


def _fmt_mm(value: float) -> str:
    return repr(float(value))


class BambuStudioCli:
    def __init__(
        self,
        binary: Path,
        *,
        profiles_dir: Path,
        timeout_s: float = SLICE_TIMEOUT_S,
        runner: Runner = subprocess.run,
    ) -> None:
        self._binary = binary
        self._profiles_dir = profiles_dir
        self._timeout_s = timeout_s
        self._runner = runner

    def _usable(self) -> bool:
        return self._binary.is_file()

    async def availability(self) -> ToolAvailability:
        if not self._usable():
            return ToolAvailability("bambu-studio", False, None, None, _INSTALL_HINT)
        return ToolAvailability(
            "bambu-studio", True, str(self._binary), _bundle_version(self._binary), ""
        )

    def _write_profiles(self, request: SliceRequest, out: Path) -> None:
        def template(kind: str) -> dict[str, object]:
            path = self._profiles_dir / f"{kind}-full.json"
            data = as_str_keyed(json.loads(path.read_text(encoding="utf-8")), context=str(path))
            if data is None:
                raise ToolUnavailableError(f"slicer profile template is not an object: {path}")
            return data

        process = template("process")
        process.update(
            layer_height=_fmt_mm(request.layer_height_mm),
            brim_type="outer_only",
            brim_width=_fmt_mm(request.brim_mm),
            enable_support="1" if request.support else "0",
        )
        if request.support:
            process.update(support_type="normal(auto)", support_style="snug")
        for name, data in (
            ("machine", template("machine")),
            ("process", process),
            ("filament", template("filament")),
        ):
            (out / f"{name}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _argv(self, request: SliceRequest, out: Path, export_name: str) -> list[str]:
        return [
            str(self._binary),
            "--datadir",
            str(out / "bambu-data"),
            "--debug",
            "2",
            "--load-settings",
            f"{out / 'machine.json'};{out / 'process.json'}",
            "--load-filaments",
            str(out / "filament.json"),
            "--curr-bed-type",
            "Textured PEI Plate",
            "--arrange",
            "0",
            "--orient",
            "0",
            "--slice",
            "0",
            "--outputdir",
            str(out),
            "--export-3mf",
            export_name,
            "--export-settings",
            str(out / "effective-settings.json"),
            request.input_3mf,
        ]

    def _run(self, argv: list[str], log_path: Path) -> subprocess.CompletedProcess[str]:
        with log_path.open("w", encoding="utf-8") as log:
            return self._runner(
                argv, stdout=log, stderr=subprocess.STDOUT, text=True, timeout=self._timeout_s
            )

    async def slice(self, request: SliceRequest) -> SliceResult:
        if not self._usable():
            raise ToolUnavailableError(f"Bambu Studio not found at {self._binary}. {_INSTALL_HINT}")
        out = Path(request.output_dir)
        log_path = out / "slicer.log"
        short = _SUPPORTED_PRINTERS.get(request.printer)
        if short is None or request.material not in _SUPPORTED_MATERIALS:
            msg = (
                f"unsupported printer/material {request.printer}/{request.material}; "
                f"templates exist for {sorted(_SUPPORTED_PRINTERS)}/{sorted(_SUPPORTED_MATERIALS)}"
            )
            return SliceResult(False, None, None, str(log_path), -1, msg)
        out.mkdir(parents=True, exist_ok=True)
        self._write_profiles(request, out)
        export_name = f"{Path(request.input_3mf).stem}-{short}-{request.material}.3mf"
        argv = self._argv(request, out, export_name)
        try:
            proc = await asyncio.to_thread(self._run, argv, log_path)
        except subprocess.TimeoutExpired:
            msg = f"slicer did not finish within {self._timeout_s:g}s; log tail:\n{_log_tail(log_path)}"
            return SliceResult(False, None, None, str(log_path), -1, msg)
        output = out / export_name
        settings = out / "effective-settings.json"
        if proc.returncode != 0:
            msg = f"slicer exited {proc.returncode}; log tail:\n{_log_tail(log_path)}"
        elif not output.is_file():
            msg = f"slicer exited 0 but wrote no {export_name}; log tail:\n{_log_tail(log_path)}"
        else:
            msg = "sliced"
        passed = proc.returncode == 0 and output.is_file()
        return SliceResult(
            passed,
            str(output) if output.is_file() else None,
            str(settings) if settings.is_file() else None,
            str(log_path),
            proc.returncode,
            msg,
        )
