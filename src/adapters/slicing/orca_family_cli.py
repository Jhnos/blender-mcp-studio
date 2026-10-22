"""Orca-family slicer CLIs, Bambu Studio and OrcaSlicer (AGPL-3.0, subprocess only, never linked).

One adapter drives every slicer in the printer catalog; which binary, profiles, bed type,
overrides and exit-code meanings a slice uses all come from catalog data
(``config/slicers.yaml`` and ``config/printers/<vendor>/*.yaml``). Nothing picks a printer
implicitly: every request names its ``printer_id``.

The command line is the v80-proven form (``tmp/lab-station-slicing-v80/slice_candidate.py``);
OrcaSlicer is a Bambu Studio fork and takes the same flags. Profiles are read from the
installed app bundle at slice time (``bundle_profiles``) and written, with the printer's
override data file (if it names one) and then the job-derived keys (``slice_job``) applied,
into ``output_dir`` (reproduction inputs). A plate that cannot fit the printable area is
refused before any slicer starts (``plate_extent.plate_fit``). The slicer's own ``--datadir``
is a ``tempfile.TemporaryDirectory`` outside ``output_dir``, removed after each run, so the
user's real slicer profile is never read or modified and scratch state never reaches a
package; on a failed run its ``*.log`` files are first copied to
``output_dir/slicer-datadir-logs/``.

``result.json`` on macOS (2026-10-22): Bambu Studio 02.08.02.61 wrote it on a passing run;
OrcaSlicer 2.4.2 wrote none, on failed runs or on the passing K1 Max run. Success is judged by
exit code and the 3MF, never by result.json.

Timeouts are 5 x the slowest measured slice per slicer, rounded up to the next second:

- ``bambu-studio``: the v80 69-part plate, ``tmp/lab-station-slicing-v80/first-pass/slicer.log``,
  first to last log timestamp 2026-10-20 21:10:38.13 -> 21:13:28.78 = 170.6 s (other v80 runs
  took 80.6, 101.4, 70.0 and 22.3 s), recorded as 171 s.
- ``orcaslicer``: the v78 69-part plate (``整機69件-單盤排版-v78.3mf``) on ``creality-k1-max-0.4``,
  OrcaSlicer 2.4.2, Mac16,10 (Apple M4), 2026-10-22 controller runs with normal + snug supports:
  33.8 s and 34.2 s, recorded as 34 s.
"""

from __future__ import annotations

import asyncio
import json
import math
import subprocess
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path

from src.adapters.slicing.bundle_profiles import (
    IncompatibleProfileError,
    UnknownProfileError,
    app_bundle,
    bundle_version,
    check_compatible,
    layer_range,
    resolve_printer_profiles,
)
from src.adapters.slicing.plate_extent import bed_size, plate_fit
from src.adapters.slicing.slice_job import (
    exit_head,
    failure,
    job_process_keys,
    keep_datadir_logs,
    with_notes,
)
from src.core.domain.packaging import ToolUse
from src.core.domain.printer_catalog import (
    PrinterCatalog,
    PrinterProfile,
    SlicerSpec,
    UnknownPrinterError,
)
from src.core.domain.slicing import (
    LayerHeightError,
    SliceRequest,
    SliceResult,
    TargetCheck,
    ToolAvailability,
    ToolUnavailableError,
)
from src.infrastructure.narrowing import as_str_keyed

SLOWEST_SLICE_MEASURED_S: dict[str, float] = {"bambu-studio": 171, "orcaslicer": 34}
SLICE_TIMEOUT_S: dict[str, float] = {
    slicer: float(5 * math.ceil(seconds)) for slicer, seconds in SLOWEST_SLICE_MEASURED_S.items()
}

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


def _process_key(printer: PrinterProfile, layer_height_mm: float) -> str:
    """The printer's process profile nearest the requested layer height (a tie takes the lower).

    The request's ``layer_height`` is written over the profile either way, so a 0.28 mm
    request on a printer that offers only "0.20" starts from that profile (v80 behaviour).
    """
    keys = [key for key, _ in printer.processes]
    exact = f"{layer_height_mm:.2f}"
    if exact in keys:
        return exact
    return min(keys, key=lambda key: (round(abs(float(key) - layer_height_mm), 9), float(key)))


def _require_in_range(
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


class OrcaFamilyCli:
    def __init__(
        self,
        catalog: PrinterCatalog,
        binaries: Mapping[str, Path],
        *,
        overrides_dir: Path,
        runner: Runner = subprocess.run,
        timeouts: Mapping[str, float] | None = None,
    ) -> None:
        """``binaries`` maps slicer id to its executable (from ``config/tools.yaml``)."""
        self._catalog = catalog
        self._binaries = dict(binaries)
        self._overrides_dir = overrides_dir
        self._runner = runner
        self._timeouts = dict(SLICE_TIMEOUT_S if timeouts is None else timeouts)

    def _binary(self, slicer: SlicerSpec) -> Path | None:
        return self._binaries.get(slicer.id)

    def _usable(self, slicer: SlicerSpec) -> bool:
        binary = self._binary(slicer)
        return binary is not None and binary.is_file()

    def _slicer_of(self, printer_id: str) -> SlicerSpec:
        return self._catalog.slicer(self._catalog.printer(printer_id).slicer)

    def printers(self) -> tuple[PrinterProfile, ...]:
        return tuple(
            p for p in self._catalog.printers if self._usable(self._catalog.slicer(p.slicer))
        )

    def timeout_s(self, printer_id: str) -> float:
        return self._timeouts[self._slicer_of(printer_id).id]

    def max_timeout_s(self) -> float:
        return max(self._timeouts[slicer.id] for slicer in self._catalog.slicers)

    async def availability(self) -> tuple[ToolAvailability, ...]:
        return tuple(self._availability(slicer) for slicer in self._catalog.slicers)

    def _availability(self, slicer: SlicerSpec) -> ToolAvailability:
        binary = self._binary(slicer)
        if binary is None or not binary.is_file():
            return ToolAvailability(slicer.id, False, None, None, slicer.install_hint)
        return ToolAvailability(slicer.id, True, str(binary), bundle_version(binary), "")

    def tool_for(self, printer_id: str) -> ToolUse:
        slicer = self._slicer_of(printer_id)
        binary = self._binary(slicer)
        version = None if binary is None or not binary.is_file() else bundle_version(binary)
        return ToolUse(slicer.id, version, slicer.license, "subprocess")

    def _bundle_profiles(
        self, slicer: SlicerSpec, binary: Path, printer: PrinterProfile, layer: str, material: str
    ) -> dict[str, dict[str, object]]:
        bundle = app_bundle(binary)
        root = None if bundle is None else bundle / slicer.profiles_subdir
        if root is None or not root.is_dir():
            raise ToolUnavailableError(
                f"{slicer.name} is installed but its app bundle has no profiles directory "
                f"({slicer.profiles_subdir}); reinstall it. {slicer.install_hint}"
            )
        try:
            return resolve_printer_profiles(root, printer, layer, material)
        except UnknownProfileError as exc:
            raise ToolUnavailableError(str(exc)) from exc

    def _usable_binary(self, slicer: SlicerSpec) -> Path:
        binary = self._binary(slicer)
        if binary is None or not binary.is_file():
            # No path: this text reaches remote MCP hosts; availability() reports the path.
            raise ToolUnavailableError(
                f"{slicer.name} is not available on this host. {slicer.install_hint}"
            )
        return binary

    def _machine(self, p: PrinterProfile) -> dict[str, object] | None:
        """The printer's flattened machine profile; ``None`` when its bundle is unreadable."""
        slicer = self._catalog.slicer(p.slicer)
        try:
            binary = self._usable_binary(slicer)
            return self._bundle_profiles(slicer, binary, p, p.processes[0][0], p.filaments[0][0])[
                "machine"
            ]
        except ToolUnavailableError:
            return None

    def _machines(self) -> dict[str, dict[str, object] | None]:
        return {p.id: self._machine(p) for p in self.printers()}

    def layer_ranges(self) -> dict[str, tuple[float, float] | None]:
        return {k: None if m is None else layer_range(m) for k, m in self._machines().items()}

    def bed_sizes(self) -> dict[str, tuple[float, float, float] | None]:
        return {k: None if m is None else bed_size(m) for k, m in self._machines().items()}

    def catalog_printers(self) -> tuple[PrinterProfile, ...]:
        return self._catalog.printers

    def slicer_name(self, printer_id: str) -> str:
        return self._slicer_of(printer_id).name

    def check_target(self, printer_id: str, layer_height_mm: float, material: str) -> TargetCheck:
        """Submit-time check: profiles exist, are compatible, and the layer height is printable.

        A height with an exact ``processes`` key needs no range. Any other height starts from
        the nearest base process and must lie inside the machine profile's declared range; a
        machine that declares none accepts exact keys only.
        """
        printer = self._catalog.printer(printer_id)
        slicer = self._catalog.slicer(printer.slicer)
        layer = _process_key(printer, layer_height_mm)
        profiles = self._bundle_profiles(
            slicer, self._usable_binary(slicer), printer, layer, material
        )
        if f"{layer_height_mm:.2f}" != layer:
            _require_in_range(printer, layer_height_mm, layer_range(profiles["machine"]))
        notes = check_compatible(profiles, printer.machine)  # IncompatibleProfileError
        return TargetCheck(notes, dict(printer.processes)[layer])

    def _write_profiles(
        self, profiles: dict[str, dict[str, object]], printer: PrinterProfile, request: SliceRequest
    ) -> None:
        out = Path(request.output_dir)
        process = profiles["process"]
        # Order: bundle profile, then the printer's override data file, then job-derived keys.
        if printer.overrides is not None:
            name = printer.overrides
            overrides = as_str_keyed(
                json.loads((self._overrides_dir / name).read_text("utf-8")), context=name
            )
            if overrides is None:
                raise ToolUnavailableError(f"{name} is not an object")
            overrides.pop("_source", None)
            process.update(overrides)
        process.update(job_process_keys(request))
        for kind, data in (
            ("machine", profiles["machine"]),
            ("process", process),
            ("filament", profiles["filament"]),
        ):
            (out / f"{kind}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    @staticmethod
    def _argv(
        binary: Path, printer: PrinterProfile, request: SliceRequest, export: str, datadir: str
    ) -> list[str]:
        out = Path(request.output_dir)
        return [
            str(binary),
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
            request.input_3mf,
        ]

    def _run(
        self, argv: list[str], log_path: Path, timeout_s: float
    ) -> subprocess.CompletedProcess[str]:
        with log_path.open("w", encoding="utf-8") as log:
            return self._runner(
                argv, stdout=log, stderr=subprocess.STDOUT, text=True, timeout=timeout_s
            )

    def _target(self, request: SliceRequest) -> PrinterProfile | str:
        """The catalog printer, or why the request cannot be sliced (checked before the binary)."""
        try:
            printer = self._catalog.printer(request.printer_id)
        except UnknownPrinterError as exc:
            return f"unsupported printer: {exc}"
        materials = [material for material, _ in printer.filaments]
        if request.material not in materials:
            return (
                f"unsupported material {request.material!r} for printer {printer.id}; "
                f"it has: {', '.join(materials)}"
            )
        return printer

    async def slice(self, request: SliceRequest) -> SliceResult:
        out = Path(request.output_dir)
        log_path = out / "slicer.log"
        printer = self._target(request)
        if isinstance(printer, str):
            return SliceResult(False, None, None, str(log_path), -1, printer)
        slicer = self._catalog.slicer(printer.slicer)
        binary = self._usable_binary(slicer)
        out.mkdir(parents=True, exist_ok=True)
        layer = _process_key(printer, request.layer_height_mm)
        profiles = self._bundle_profiles(slicer, binary, printer, layer, request.material)
        try:
            notes = check_compatible(profiles, printer.machine)
        except IncompatibleProfileError as exc:
            return SliceResult(False, None, None, str(log_path), -1, str(exc))
        refusal = plate_fit(Path(request.input_3mf), profiles["machine"], printer.id)
        if refusal is not None:
            return SliceResult(False, None, None, str(log_path), -1, refusal)
        self._write_profiles(profiles, printer, request)
        model = printer.model.replace(" ", "-")
        # Export name is "<input stem>-<printer model>-<material>.3mf".
        export = f"{Path(request.input_3mf).stem}-{model}-{request.material}.3mf"
        # A slicer that exits 0 without writing must not pass on a previous run's files.
        (out / export).unlink(missing_ok=True)
        (out / "effective-settings.json").unlink(missing_ok=True)
        timeout_s = self._timeouts[slicer.id]
        with tempfile.TemporaryDirectory(prefix=f"{slicer.id}-data-") as datadir:
            argv = self._argv(binary, printer, request, export, datadir)
            try:
                proc = await asyncio.to_thread(self._run, argv, log_path, timeout_s)
            except subprocess.TimeoutExpired:
                keep_datadir_logs(Path(datadir), out)
                msg = failure(f"slicer did not finish within {timeout_s:g}s", notes, log_path)
                return SliceResult(False, None, None, str(log_path), -1, msg)
            if proc.returncode != 0:
                keep_datadir_logs(Path(datadir), out)
        result = self._result(proc.returncode, slicer, out, export, log_path, notes)
        return replace(result, process_profile=dict(printer.processes)[layer])

    @staticmethod
    def _result(
        rc: int, slicer: SlicerSpec, out: Path, export: str, log_path: Path, notes: tuple[str, ...]
    ) -> SliceResult:
        output = out / export
        settings = out / "effective-settings.json"
        if rc != 0:
            msg = failure(exit_head(slicer, rc), notes, log_path)
        elif not output.is_file():
            msg = failure(f"slicer exited 0 but wrote no {export}", notes, log_path)
        else:
            msg = with_notes("sliced", notes)
        return SliceResult(
            rc == 0 and output.is_file(),
            str(output) if output.is_file() else None,
            str(settings) if settings.is_file() else None,
            str(log_path),
            rc,
            msg,
        )
