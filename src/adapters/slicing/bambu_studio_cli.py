"""Bambu Studio command-line slicer (AGPL-3.0, subprocess only, never linked).

The command line is the v80-proven form (``tmp/lab-station-slicing-v80/slice_candidate.py``).
Profiles are read from the installed app bundle at slice time (``bundle_profiles``: the leaf
names live in ``config/slicer-profiles/p2s-pla-profiles.json``) and written, with the v80
override data file and per-request keys applied, into ``output_dir`` (reproduction inputs). The slicer's own ``--datadir`` is a
``tempfile.TemporaryDirectory`` outside ``output_dir``, removed after each run, so the user's
real Bambu profile is never read or modified and scratch state never reaches a package.

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
import tempfile
from collections.abc import Callable
from pathlib import Path

from src.adapters.slicing.bundle_profiles import app_bundle, bundle_profiles
from src.core.domain.slicing import (
    SliceRequest,
    SliceResult,
    SupportedTargets,
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
    bundle = app_bundle(binary)
    plist = None if bundle is None else bundle / "Contents" / "Info.plist"
    if plist is None or not plist.is_file():
        return None
    with plist.open("rb") as handle:
        value = plistlib.load(handle).get("CFBundleShortVersionString")
    return value if isinstance(value, str) else None


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

    @property
    def timeout_s(self) -> float:
        """The subprocess deadline; delivery adapters derive their own timeouts from it."""
        return self._timeout_s

    def supported(self) -> SupportedTargets:
        return SupportedTargets(
            tuple(sorted(_SUPPORTED_PRINTERS)), tuple(sorted(_SUPPORTED_MATERIALS))
        )

    def _usable(self) -> bool:
        return self._binary.is_file()

    async def availability(self) -> ToolAvailability:
        if not self._usable():
            return ToolAvailability("bambu-studio", False, None, None, _INSTALL_HINT)
        return ToolAvailability(
            "bambu-studio", True, str(self._binary), _bundle_version(self._binary), ""
        )

    def _write_profiles(self, request: SliceRequest, out: Path) -> None:
        profiles = bundle_profiles(self._binary, self._profiles_dir)
        process = profiles["process"]
        # Order: bundle profile, then the v80 override data file, then request-derived keys.
        overrides = as_str_keyed(
            json.loads((self._profiles_dir / "p2s-pla-overrides.json").read_text("utf-8")),
            context="p2s-pla-overrides.json",
        )
        if overrides is None:
            raise ToolUnavailableError("p2s-pla-overrides.json is not an object")
        overrides.pop("_source", None)
        process.update(overrides)
        process.update(
            layer_height=_fmt_mm(request.layer_height_mm),
            brim_width=_fmt_mm(request.brim_mm),
            enable_support="1" if request.support else "0",
        )
        for name, data in (
            ("machine", profiles["machine"]),
            ("process", process),
            ("filament", profiles["filament"]),
        ):
            (out / f"{name}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _argv(self, request: SliceRequest, out: Path, export_name: str, datadir: str) -> list[str]:
        return [
            str(self._binary.resolve()),
            "--datadir",
            datadir,
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
            str(Path(request.input_3mf).resolve()),
        ]

    def _run(self, argv: list[str], log_path: Path) -> subprocess.CompletedProcess[str]:
        with log_path.open("w", encoding="utf-8") as log:
            return self._runner(
                argv,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=self._timeout_s,
                cwd=log_path.parent.resolve(),
            )

    async def slice(self, request: SliceRequest) -> SliceResult:
        out = Path(request.output_dir).resolve()
        log_path = out / "slicer.log"
        short = _SUPPORTED_PRINTERS.get(request.printer)
        if short is None or request.material not in _SUPPORTED_MATERIALS:
            msg = (
                f"unsupported printer/material {request.printer}/{request.material}; "
                f"templates exist for {sorted(_SUPPORTED_PRINTERS)}/{sorted(_SUPPORTED_MATERIALS)}"
            )
            return SliceResult(False, None, None, str(log_path), -1, msg)
        if not self._usable():
            # No path: this text reaches remote MCP hosts; availability() reports the path.
            raise ToolUnavailableError(
                f"Bambu Studio is not available on this host. {_INSTALL_HINT}"
            )
        out.mkdir(parents=True, exist_ok=True)
        self._write_profiles(request, out)  # ToolUnavailableError when the bundle has none
        # Export name is "<input stem>-<printer>-<material>.3mf".
        export_name = f"{Path(request.input_3mf).stem}-{short}-{request.material}.3mf"
        # A slicer that exits 0 without writing must not pass on a previous run's files.
        (out / export_name).unlink(missing_ok=True)
        (out / "effective-settings.json").unlink(missing_ok=True)
        try:
            with tempfile.TemporaryDirectory(prefix="bambu-data-") as datadir:
                argv = self._argv(request, out, export_name, datadir)
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
