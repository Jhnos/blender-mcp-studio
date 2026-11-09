"""Orca-family CLI adapter: one data-driven adapter for Bambu Studio and OrcaSlicer (fake runner).

The Bambu Studio adapter tests moved here from the deleted Bambu-only adapter (v80 command line,
evidence files, failures); the multi-slicer tests below them are new with the printer catalog.
"""

import json
import plistlib
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

import src.adapters.slicing.orca_family_cli as cli_module
from src.adapters.slicing.bundle_profiles import IncompatibleProfileError
from src.adapters.slicing.orca_family_cli import (
    SLICE_TIMEOUT_S,
    SLOWEST_SLICE_MEASURED_S,
    OrcaFamilyCli,
)
from src.adapters.slicing.slice_targets import process_key as _process_key
from src.core.domain.model_spec import PrintTarget
from src.core.domain.packaging import ToolUse
from src.core.domain.printer_catalog import PrinterCatalog, PrinterProfile
from src.core.domain.slicing import LayerHeightError, SliceRequest, ToolUnavailableError
from src.infrastructure.printer_catalog_loader import load_printer_catalog
from tests.fakes.bambu_bundle import K1C_LEAVES, flattened, make_bundle, make_orca_bundle
from tests.fakes.plate_3mf import translate, write_3mf

_PROFILES = Path(cli_module.__file__).resolve().parents[3] / "config" / "slicer-profiles"
P2S, K1C = "bambu-p2s-0.4", "creality-k1c-0.4"


class FakeRunner:
    def __init__(self, returncode: int = 0, write_output: bool = True, log: str = "ok\n") -> None:
        self.returncode, self.write_output, self.log = returncode, write_output, log
        self.argv: list[str] = []
        self.kwargs: dict[str, object] = {}

    def __call__(self, argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.argv, self.kwargs = list(argv), kwargs
        out = Path(argv[argv.index("--outputdir") + 1])
        name = argv[argv.index("--export-3mf") + 1]
        stdout = kwargs["stdout"]
        stdout.write(self.log)  # type: ignore[attr-defined]
        if self.write_output:
            (out / name).write_bytes(b"3mf")
            (out / "effective-settings.json").write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(argv, self.returncode)


def _binary(tmp_path: Path) -> Path:
    # A1: vendor profiles are read from the app bundle, so the fake .app carries a tiny tree.
    return make_bundle(tmp_path)


def _request(tmp_path: Path, printer_id: str = P2S, **over: object) -> SliceRequest:
    if not (tmp_path / "gate.3mf").exists():  # a 10 mm cube at (10, 10): fits every bed
        write_3mf(tmp_path / "gate.3mf", [(10, translate(10, 10))])
    return SliceRequest.from_target(
        str(tmp_path / "gate.3mf"),
        str(tmp_path / "out"),
        PrintTarget(**{"printer": printer_id, "material": "PLA", **over}),  # type: ignore[arg-type]
        printer_id=printer_id,
    )


def _make(
    bambu: Path,
    orca: Path,
    runner: object,
    catalog: PrinterCatalog | None = None,
) -> OrcaFamilyCli:
    return OrcaFamilyCli(
        catalog or load_printer_catalog(),
        {"bambu-studio": bambu, "orcaslicer": orca},
        overrides_dir=_PROFILES,
        runner=runner,  # type: ignore[arg-type]
    )


def _cli(tmp_path: Path, runner: object, binary: Path | None = None) -> OrcaFamilyCli:
    return _make(binary or _binary(tmp_path), tmp_path / "no-orca" / "OrcaSlicer", runner)


def _missing(tmp_path: Path) -> OrcaFamilyCli:
    return _make(tmp_path / "nope", tmp_path / "nope-orca", FakeRunner())


def test_timeout_is_five_times_the_measured_slowest() -> None:
    assert SLOWEST_SLICE_MEASURED_S["bambu-studio"] == 171
    assert SLICE_TIMEOUT_S["bambu-studio"] == 5 * 171
    orca = SLOWEST_SLICE_MEASURED_S["orcaslicer"]
    assert SLICE_TIMEOUT_S["orcaslicer"] == 5 * orca


def test_from_target_carries_every_print_default() -> None:
    req = SliceRequest.from_target(
        "/a.3mf", "/out", PrintTarget(printer=P2S, material="PLA"), printer_id=P2S
    )
    assert (req.printer, req.material, req.layer_height_mm) == (P2S, "PLA", 0.2)
    assert (req.support, req.brim_mm) == (True, 3.0)
    assert (req.input_3mf, req.output_dir, req.printer_id) == ("/a.3mf", "/out", P2S)


async def test_availability_reports_missing_binary(tmp_path: Path) -> None:
    status = {s.name: s for s in await _missing(tmp_path).availability()}["bambu-studio"]
    assert status.available is False
    assert status.path is None
    assert "BAMBU_STUDIO_BIN" in status.install_hint


async def test_availability_reads_version_from_info_plist(tmp_path: Path) -> None:
    binary = _binary(tmp_path)
    plist = binary.parents[1] / "Info.plist"
    plist.write_bytes(plistlib.dumps({"CFBundleShortVersionString": "02.06.00.51"}))
    tools = await _cli(tmp_path, FakeRunner(), binary).availability()
    status = {s.name: s for s in tools}["bambu-studio"]
    assert status.available is True
    assert status.version == "02.06.00.51"
    assert status.path == str(binary)


async def test_availability_version_is_none_without_plist(tmp_path: Path) -> None:
    status = {s.name: s for s in await _cli(tmp_path, FakeRunner()).availability()}
    assert status["bambu-studio"].available is True
    assert status["bambu-studio"].version is None


async def test_slice_reports_missing_binary(tmp_path: Path) -> None:
    with pytest.raises(ToolUnavailableError, match="BAMBU_STUDIO_BIN"):
        await _missing(tmp_path).slice(_request(tmp_path))


async def test_slice_builds_the_v80_command_line(tmp_path: Path) -> None:
    runner = FakeRunner()
    binary = _binary(tmp_path)
    req = _request(tmp_path)
    out = tmp_path / "out"
    await _cli(tmp_path, runner, binary).slice(req)
    flags = [
        "--datadir",
        "--debug",
        "--load-settings",
        "--load-filaments",
        "--curr-bed-type",
        "--arrange",
        "--orient",
        "--slice",
        "--outputdir",
        "--export-3mf",
        "--export-settings",
    ]
    argv = runner.argv
    positions = [argv.index(flag) for flag in flags]
    assert positions == sorted(positions)

    def after(flag: str) -> str:
        return argv[argv.index(flag) + 1]

    assert argv[0] == str(binary)
    assert after("--debug") == "3"  # info: the error-level log said only "run found error, exit"
    assert after("--load-settings") == f"{out}/machine.json;{out}/process.json"
    assert after("--load-filaments") == f"{out}/filament.json"
    assert after("--curr-bed-type") == "Textured PEI Plate"
    assert (after("--arrange"), after("--orient"), after("--slice")) == ("0", "0", "0")
    assert after("--outputdir") == str(out)
    assert after("--export-3mf") == "gate-P2S-PLA.3mf"
    assert after("--export-settings") == f"{out}/effective-settings.json"
    assert argv[-1] == req.input_3mf
    datadir = Path(after("--datadir"))
    assert out not in datadir.parents  # scratch must never end up in a packaged run dir
    assert not datadir.exists()  # removed once slice() returns


async def test_slice_writes_profiles_with_request_overrides(tmp_path: Path) -> None:
    req = _request(tmp_path, layer_height_mm=0.16, support=True, brim_mm=4.0)
    await _cli(tmp_path, FakeRunner()).slice(req)
    process = json.loads((tmp_path / "out" / "process.json").read_text(encoding="utf-8"))
    assert process["layer_height"] == "0.16"
    assert process["enable_support"] == "1"
    assert (process["support_type"], process["support_style"]) == ("normal(auto)", "snug")
    assert (process["brim_type"], process["brim_width"]) == ("outer_only", "4.0")
    assert (tmp_path / "out" / "machine.json").is_file()
    assert (tmp_path / "out" / "filament.json").is_file()


async def test_slice_without_support_disables_it(tmp_path: Path) -> None:
    await _cli(tmp_path, FakeRunner()).slice(_request(tmp_path, support=False))
    process = json.loads((tmp_path / "out" / "process.json").read_text(encoding="utf-8"))
    assert process["enable_support"] == "0"


async def test_slice_reports_nonzero_exit(tmp_path: Path) -> None:
    log = "\n".join(f"line {i}" for i in range(40)) + "\nfatal: bad plate\n"
    runner = FakeRunner(returncode=2, write_output=False, log=log)
    result = await _cli(tmp_path, runner).slice(_request(tmp_path))
    assert result.passed is False
    assert result.return_code == 2
    assert result.output_3mf is None
    assert "fatal: bad plate" in result.message
    assert "line 0" not in result.message


async def test_slice_passes_when_output_3mf_exists(tmp_path: Path) -> None:
    result = await _cli(tmp_path, FakeRunner()).slice(_request(tmp_path))
    assert result.passed is True
    assert result.output_3mf == str(tmp_path / "out" / "gate-P2S-PLA.3mf")
    assert result.settings_json == str(tmp_path / "out" / "effective-settings.json")
    assert Path(result.log_path).is_file()


async def test_slice_exit_zero_without_output_fails(tmp_path: Path) -> None:
    result = await _cli(tmp_path, FakeRunner(write_output=False)).slice(_request(tmp_path))
    assert result.passed is False
    assert "gate-P2S-PLA.3mf" in result.message


async def test_slice_timeout_is_a_failed_result(tmp_path: Path) -> None:
    def hang(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(argv, SLICE_TIMEOUT_S["bambu-studio"])

    result = await _cli(tmp_path, hang).slice(_request(tmp_path))
    assert result.passed is False
    assert result.output_3mf is None
    assert f"slicer did not finish within {SLICE_TIMEOUT_S['bambu-studio']:g}s" in result.message


async def test_slice_rejects_unsupported_printer(tmp_path: Path) -> None:
    req = SliceRequest.from_target(
        str(tmp_path / "a.3mf"),
        str(tmp_path / "out"),
        PrintTarget(printer="other", material="PLA"),
        printer_id="other",
    )
    result = await _cli(tmp_path, FakeRunner()).slice(req)
    assert result.passed is False
    assert "other" in result.message


def _overrides() -> dict[str, object]:
    data = json.loads((_PROFILES / "p2s-pla-overrides.json").read_text(encoding="utf-8"))
    data.pop("_source")
    return data


def test_overrides_file_matches_v80_acceptance() -> None:
    data = _overrides()
    assert data["wall_loops"] == "3"
    assert data["sparse_infill_pattern"] == "gyroid"
    assert "enable_prime_tower" not in data  # job-derived since 2026-11-09 (slice_job)
    assert data["initial_layer_speed"] == ["20", "20", "20"]
    assert data["initial_layer_infill_speed"] == ["30", "30", "30"]


async def test_process_json_applies_v80_overrides(tmp_path: Path) -> None:
    req = _request(tmp_path, layer_height_mm=0.16, support=False, brim_mm=4.0)
    await _cli(tmp_path, FakeRunner()).slice(req)
    process = json.loads((tmp_path / "out" / "process.json").read_text(encoding="utf-8"))
    request_keys = {"layer_height", "enable_support", "brim_width"}
    for key, value in _overrides().items():
        if key not in request_keys:
            assert process[key] == value, key
    assert "_source" not in process
    assert (process["layer_height"], process["enable_support"], process["brim_width"]) == (
        "0.16",
        "0",
        "4.0",
    )


async def test_stale_output_does_not_pass(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    (out / "gate-P2S-PLA.3mf").write_bytes(b"old")
    result = await _cli(tmp_path, FakeRunner(write_output=False)).slice(_request(tmp_path))
    assert result.passed is False
    assert result.output_3mf is None


async def test_unsupported_target_reported_before_missing_binary(tmp_path: Path) -> None:
    req = SliceRequest.from_target(
        "/a.3mf",
        str(tmp_path / "out"),
        PrintTarget(printer="x1c", material="PLA"),
        printer_id="x1c",
    )
    result = await _missing(tmp_path).slice(req)
    assert result.passed is False
    assert "x1c" in result.message


async def test_unsupported_material_reported_before_missing_binary(tmp_path: Path) -> None:
    result = await _missing(tmp_path).slice(_request(tmp_path, material="PETG"))
    assert result.passed is False
    assert "PETG" in result.message and "PLA" in result.message


# ---- one adapter, several slicers, chosen by catalog data ----


def _both(tmp_path: Path, runner: object, catalog: PrinterCatalog | None = None) -> OrcaFamilyCli:
    return _make(make_bundle(tmp_path), make_orca_bundle(tmp_path), runner, catalog)


async def test_each_printer_uses_its_slicer_binary(tmp_path: Path) -> None:
    runner = FakeRunner()
    cli = _both(tmp_path, runner)
    await cli.slice(_request(tmp_path, P2S))
    assert runner.argv[0] == str(tmp_path / "Fake.app" / "Contents" / "MacOS" / "BambuStudio")
    result = await cli.slice(_request(tmp_path, K1C))
    assert runner.argv[0] == str(tmp_path / "Orca.app" / "Contents" / "MacOS" / "OrcaSlicer")
    assert result.passed is True
    assert result.output_3mf == str(tmp_path / "out" / "gate-K1C-PLA.3mf")


@pytest.mark.parametrize(
    ("rc", "meaning"),
    [
        (156, "slicing error"),
        (206, "no suitable objects"),
        (204, "objects partly inside the printable area"),  # the real K1C v78 run, -52
    ],
)
async def test_orca_negative_exit_code_mapped(tmp_path: Path, rc: int, meaning: str) -> None:
    runner = FakeRunner(returncode=rc, write_output=False, log="boom\n")
    result = await _both(tmp_path, runner).slice(_request(tmp_path, K1C))
    assert result.passed is False and result.return_code == rc
    assert meaning in result.message and "boom" in result.message


async def test_exit_code_without_a_mapping_is_reported_bare(tmp_path: Path) -> None:
    runner = FakeRunner(returncode=1, write_output=False)  # 1 is no CLI_* code (1 - 256)
    result = await _both(tmp_path, runner).slice(_request(tmp_path, P2S))
    assert result.message.startswith("slicer exited 1; ")  # no "(meaning)" after the code
    assert "CLI_" not in result.message and "log tail:" in result.message


async def test_bambu_exit_code_maps_with_its_own_hint(tmp_path: Path) -> None:
    runner = FakeRunner(returncode=156, write_output=False)
    result = await _both(tmp_path, runner).slice(_request(tmp_path, P2S))
    assert "CLI_SLICING_ERROR" in result.message and "Bambu Studio" in result.message


async def test_printers_lists_only_installed_slicers(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    assert [p.id for p in _cli(tmp_path / "a", FakeRunner()).printers()] == [P2S]
    both = _both(tmp_path / "b", FakeRunner())
    catalog = load_printer_catalog()
    assert {p.id for p in both.printers()} == {p.id for p in catalog.printers}
    assert _missing(tmp_path).printers() == ()


async def test_availability_has_one_entry_per_slicer(tmp_path: Path) -> None:
    tools = await _both(tmp_path, FakeRunner()).availability()
    assert [t.name for t in tools] == ["bambu-studio", "orcaslicer"]
    assert all(t.available for t in tools)


def test_tool_for_names_the_slicer_that_ran(tmp_path: Path) -> None:
    cli = _both(tmp_path, FakeRunner())
    plist = tmp_path / "Orca.app" / "Contents" / "Info.plist"
    plist.write_bytes(plistlib.dumps({"CFBundleShortVersionString": "2.4.2"}))
    assert cli.tool_for(K1C) == ToolUse("orcaslicer", "2.4.2", "AGPL-3.0-only", "subprocess")
    assert cli.tool_for(P2S) == ToolUse("bambu-studio", None, "AGPL-3.0-only", "subprocess")


def test_timeout_is_per_printer_slicer(tmp_path: Path) -> None:
    cli = _both(tmp_path, FakeRunner())
    assert cli.timeout_s(P2S) == SLICE_TIMEOUT_S["bambu-studio"]
    assert cli.timeout_s(K1C) == SLICE_TIMEOUT_S["orcaslicer"]


async def test_bed_type_from_printer(tmp_path: Path) -> None:
    catalog = load_printer_catalog()
    k1c = replace(catalog.printer(K1C), bed_type="Smooth PEI Plate")
    others = tuple(p for p in catalog.printers if p.id != K1C)
    runner = FakeRunner()
    cli = _both(tmp_path, runner, replace(catalog, printers=(*others, k1c)))
    await cli.slice(_request(tmp_path, K1C))
    assert runner.argv[runner.argv.index("--curr-bed-type") + 1] == "Smooth PEI Plate"


async def test_no_overrides_for_creality(tmp_path: Path) -> None:
    await _both(tmp_path, FakeRunner()).slice(_request(tmp_path, K1C, brim_mm=4.0))
    process = json.loads((tmp_path / "out" / "process.json").read_text(encoding="utf-8"))
    expected = {
        **flattened("process", K1C_LEAVES),
        "layer_height": "0.2",
        "brim_width": "4.0",
        "brim_type": "outer_only",  # job-derived: the job has a brim
        "enable_support": "1",
        "enable_prime_tower": "0",  # job-derived: one filament, so no purge tower
        "support_type": "normal(auto)",  # job-derived: support is on by default
        "support_style": "snug",
    }
    assert process == expected  # nothing from p2s-pla-overrides.json


async def test_compatibility_notes_are_appended_to_the_message(tmp_path: Path) -> None:
    cli = _both(tmp_path, FakeRunner())
    leaf = tmp_path / "Orca.app/Contents/Resources/profiles/Creality/filament"
    path = leaf / f"{K1C_LEAVES['filament']}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["compatible_printers_condition"] = "nozzle_diameter[0]==0.4"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = await cli.slice(_request(tmp_path, K1C))
    assert result.passed is True
    assert result.message.startswith("sliced")
    assert "compatible_printers_condition not evaluated" in result.message


async def test_incompatible_profile_is_a_failed_result_naming_it(tmp_path: Path) -> None:
    runner = FakeRunner()
    cli = _both(tmp_path, runner)
    leaf = tmp_path / "Orca.app/Contents/Resources/profiles/Creality/filament"
    path = leaf / f"{K1C_LEAVES['filament']}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["compatible_printers"] = ["Creality K1 Max 0.4 nozzle"]
    path.write_text(json.dumps(data), encoding="utf-8")
    result = await cli.slice(_request(tmp_path, K1C))
    assert result.passed is False
    assert K1C_LEAVES["filament"] in result.message
    assert runner.argv == []  # the slicer never started


def test_check_target_passes_and_returns_notes_without_slicing(tmp_path: Path) -> None:
    runner = FakeRunner()
    cli = _both(tmp_path, runner)
    check = cli.check_target(K1C, 0.2, "PLA")
    assert check.notes == () and check.process_profile == K1C_LEAVES["process"]
    assert runner.argv == []


def test_check_target_refuses_incompatible_and_missing_slicer(tmp_path: Path) -> None:
    cli = _both(tmp_path, FakeRunner())
    leaf = tmp_path / "Orca.app/Contents/Resources/profiles/Creality/filament"
    path = leaf / f"{K1C_LEAVES['filament']}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["compatible_printers"] = ["Creality K1 Max 0.4 nozzle"]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(IncompatibleProfileError, match=K1C_LEAVES["filament"]):
        cli.check_target(K1C, 0.2, "PLA")
    with pytest.raises(ToolUnavailableError, match="not available"):
        _missing(tmp_path).check_target(K1C, 0.2, "PLA")


def test_every_slicer_has_a_measured_slowest_slice() -> None:
    catalog = load_printer_catalog()
    for slicer in catalog.slicers:
        assert SLOWEST_SLICE_MEASURED_S[slicer.id] > 0, slicer.id  # a zero must never ship
        assert SLICE_TIMEOUT_S[slicer.id] >= 5 * SLOWEST_SLICE_MEASURED_S[slicer.id]


# ---- plate-fit precheck: a layout that cannot fit the bed never reaches the slicer ----


def _k1c_bed(tmp_path: Path, area: list[str]) -> None:
    machine = tmp_path / "Orca.app/Contents/Resources/profiles/Creality/machine"
    path = machine / f"{K1C_LEAVES['machine']}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["printable_area"] = area
    path.write_text(json.dumps(data), encoding="utf-8")


_BED_220 = ["0x0", "220x0", "220x220", "0x220"]


async def test_plate_too_large_for_bed_fails_before_slicer(tmp_path: Path) -> None:
    runner = FakeRunner()
    cli = _both(tmp_path, runner)
    _k1c_bed(tmp_path, _BED_220)
    write_3mf(tmp_path / "gate.3mf", [(10, translate(6, 6)), (10, translate(237, 236.9))])
    result = await cli.slice(_request(tmp_path, K1C))
    assert result.passed is False and result.output_3mf is None
    assert result.message == (
        "layout 241×241 mm does not fit creality-k1c-0.4 printable area 220×220 mm; "
        "choose a larger printer or re-lay out the plate"
    )
    assert runner.argv == []  # the slicer never started


async def test_plate_fits_runs_slicer(tmp_path: Path) -> None:
    runner = FakeRunner()
    cli = _both(tmp_path, runner)
    _k1c_bed(tmp_path, _BED_220)
    write_3mf(tmp_path / "gate.3mf", [(10, translate(6, 6)), (10, translate(200, 200))])
    result = await cli.slice(_request(tmp_path, K1C))
    assert result.passed is True and result.message == "sliced"
    assert runner.argv[0].endswith("OrcaSlicer")


async def test_plate_placed_outside_the_bed_fails_even_if_small(tmp_path: Path) -> None:
    runner = FakeRunner()
    cli = _both(tmp_path, runner)
    _k1c_bed(tmp_path, _BED_220)
    write_3mf(tmp_path / "gate.3mf", [(10, translate(215, 10))])  # 215..225 > 220
    result = await cli.slice(_request(tmp_path, K1C))
    assert result.passed is False and "does not fit" in result.message
    assert runner.argv == []


async def test_unreadable_layout_is_refused_before_slicer(tmp_path: Path) -> None:
    runner = FakeRunner()
    cli = _both(tmp_path, runner)
    _k1c_bed(tmp_path, _BED_220)
    (tmp_path / "gate.3mf").write_bytes(b"not a zip")
    result = await cli.slice(_request(tmp_path, K1C))
    assert runner.argv == []  # what cannot be measured never reaches the slicer
    assert result.passed is False and "plate-fit precheck failed" in result.message
    assert str(tmp_path) not in result.message


async def test_machine_without_printable_area_is_refused_before_slicer(tmp_path: Path) -> None:
    runner = FakeRunner()
    cli = _both(tmp_path, runner)
    _k1c_bed(tmp_path, [])
    result = await cli.slice(_request(tmp_path, K1C))
    assert runner.argv == []
    assert "creality-k1c-0.4 has no printable_area" in result.message


# ---- job-derived keys and readable failures ----


def _set_process_key(tmp_path: Path, printer_id: str, key: str, value: str) -> None:
    if printer_id == K1C:
        app, vendor, leaf = "Orca.app", "Creality", K1C_LEAVES["process"]
    else:
        app, vendor, leaf = "Fake.app", "BBL", "0.20mm Standard @BBL P2S"
    path = tmp_path / app / "Contents/Resources/profiles" / vendor / "process" / f"{leaf}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data[key] = value
    path.write_text(json.dumps(data), encoding="utf-8")


async def test_single_filament_job_disables_prime_tower(tmp_path: Path) -> None:
    cli = _both(tmp_path, FakeRunner())
    _set_process_key(tmp_path, K1C, "enable_prime_tower", "1")  # the K1 Max bundle default
    await cli.slice(_request(tmp_path, K1C))
    process = json.loads((tmp_path / "out" / "process.json").read_text(encoding="utf-8"))
    assert process["enable_prime_tower"] == "0"


@pytest.mark.parametrize("printer_id", [P2S, K1C])
async def test_prime_tower_rule_is_vendor_neutral(tmp_path: Path, printer_id: str) -> None:
    catalog = load_printer_catalog()
    bare = tuple(replace(p, overrides=None) for p in catalog.printers)  # no overrides file
    cli = _both(tmp_path, FakeRunner(), replace(catalog, printers=bare))
    _set_process_key(tmp_path, printer_id, "enable_prime_tower", "1")
    await cli.slice(_request(tmp_path, printer_id))
    process = json.loads((tmp_path / "out" / "process.json").read_text(encoding="utf-8"))
    assert process["enable_prime_tower"] == "0"


async def test_failure_message_names_code_and_hint(tmp_path: Path) -> None:
    lines = [f"info line {i}" for i in range(30)] + ["run found error, exit"]
    runner = FakeRunner(
        returncode=155, write_output=False, log="".join(f"{s}{chr(10)}" for s in lines)
    )
    result = await _both(tmp_path, runner).slice(_request(tmp_path, K1C))
    assert result.passed is False and result.return_code == 155
    assert "CLI_GCODE_PATH_CONFLICTS" in result.message
    assert "G-code path conflicts" in result.message
    assert "try moving the wipe tower further from other models" in result.message
    assert "info line 11" in result.message and "info line 10" not in result.message  # 20 lines
    assert result.message.rstrip().endswith("run found error, exit")


def _bare(tmp_path: Path, runner: object) -> OrcaFamilyCli:
    """Both slicers, with every printer's override file removed (job rules only)."""
    catalog = load_printer_catalog()
    bare = tuple(replace(p, overrides=None) for p in catalog.printers)
    return _both(tmp_path, runner, replace(catalog, printers=bare))


@pytest.mark.parametrize("printer_id", [P2S, K1C])
async def test_support_on_uses_normal_snug_for_every_vendor(
    tmp_path: Path, printer_id: str
) -> None:
    cli = _bare(tmp_path, FakeRunner())
    _set_process_key(tmp_path, printer_id, "support_type", "tree(auto)")
    _set_process_key(tmp_path, printer_id, "support_style", "default")
    await cli.slice(_request(tmp_path, printer_id, support=True))
    process = json.loads((tmp_path / "out" / "process.json").read_text(encoding="utf-8"))
    assert (process["support_type"], process["support_style"]) == ("normal(auto)", "snug")


async def test_support_off_leaves_support_style_alone(tmp_path: Path) -> None:
    cli = _bare(tmp_path, FakeRunner())
    _set_process_key(tmp_path, K1C, "support_style", "default")
    await cli.slice(_request(tmp_path, K1C, support=False))
    process = json.loads((tmp_path / "out" / "process.json").read_text(encoding="utf-8"))
    assert process["support_style"] == "default" and process["enable_support"] == "0"


class DatadirLogRunner(FakeRunner):
    """Writes a log into the slicer's --datadir, as OrcaSlicer keeps its own log there."""

    def __call__(self, argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        datadir = Path(argv[argv.index("--datadir") + 1])
        (datadir / "log").mkdir(parents=True, exist_ok=True)
        (datadir / "log" / "debug_run.log").write_text("conflict at layer 12\n", "utf-8")
        (datadir / "plate").mkdir(exist_ok=True)
        (datadir / "plate" / "debug_run.log").write_text("plate log\n", "utf-8")
        (datadir / "cache.bin").write_bytes(b"not a log")
        return super().__call__(argv, **kwargs)


async def test_failed_run_keeps_datadir_logs(tmp_path: Path) -> None:
    runner = DatadirLogRunner(returncode=155, write_output=False)
    await _both(tmp_path, runner).slice(_request(tmp_path, K1C))
    kept = tmp_path / "out" / "slicer-datadir-logs"
    found = sorted(p.relative_to(kept).as_posix() for p in kept.rglob("*") if p.is_file())
    assert found == ["log/debug_run.log", "plate/debug_run.log"]  # same name, both kept
    assert (kept / "log" / "debug_run.log").read_text("utf-8") == "conflict at layer 12\n"
    assert (kept / "plate" / "debug_run.log").read_text("utf-8") == "plate log\n"


async def test_timed_out_run_keeps_datadir_logs(tmp_path: Path) -> None:
    class HangingRunner(DatadirLogRunner):
        def __call__(self, argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            super().__call__(argv, **kwargs)
            raise subprocess.TimeoutExpired(argv, 1)

    result = await _both(tmp_path, HangingRunner(write_output=False)).slice(_request(tmp_path, K1C))
    assert "did not finish" in result.message
    kept = tmp_path / "out" / "slicer-datadir-logs"
    assert (kept / "log" / "debug_run.log").is_file()


async def test_signal_death_is_named_without_a_cli_hint(tmp_path: Path) -> None:
    runner = FakeRunner(returncode=-9, write_output=False)
    result = await _both(tmp_path, runner).slice(_request(tmp_path, K1C))
    assert result.message.startswith("slicer was killed by signal 9 (SIGKILL)")
    assert "CLI_" not in result.message and result.return_code == -9


async def test_shell_wrapped_code_still_maps(tmp_path: Path) -> None:
    runner = FakeRunner(returncode=155, write_output=False)
    result = await _both(tmp_path, runner).slice(_request(tmp_path, K1C))
    assert "CLI_GCODE_PATH_CONFLICTS" in result.message


async def test_passing_run_keeps_no_datadir_logs(tmp_path: Path) -> None:
    await _both(tmp_path, DatadirLogRunner()).slice(_request(tmp_path, K1C))
    assert not (tmp_path / "out" / "slicer-datadir-logs").exists()


def test_orcaslicer_timeout_is_five_times_the_measured_34_s() -> None:
    assert SLOWEST_SLICE_MEASURED_S["orcaslicer"] == 34
    assert SLICE_TIMEOUT_S["orcaslicer"] == 170


# ---- layer height: nearest base process, bounded by the machine profile's range ----


def _set_machine_range(tmp_path: Path, low: object, high: object) -> None:
    leaf = tmp_path / "Orca.app/Contents/Resources/profiles/Creality/machine"
    path = leaf / f"{K1C_LEAVES['machine']}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["min_layer_height"], data["max_layer_height"] = low, high
    path.write_text(json.dumps(data), encoding="utf-8")


def _two_process_printer() -> PrinterProfile:
    base = load_printer_catalog().printer(K1C)
    return replace(base, processes=(("0.20", "p20"), ("0.12", "p12")))


def test_non_exact_height_uses_nearest_base_process(tmp_path: Path) -> None:
    cli = _both(tmp_path, FakeRunner())
    _set_machine_range(tmp_path, ["0.08"], ["0.3"])  # the real shape: per-extruder string lists
    check = cli.check_target(K1C, 0.28, "PLA")
    assert check.process_profile == K1C_LEAVES["process"]  # the only base process, "0.20"
    printer = _two_process_printer()
    assert _process_key(printer, 0.14) == "0.12" and _process_key(printer, 0.19) == "0.20"
    assert _process_key(printer, 0.2) == "0.20"  # exact key wins


def test_nearest_tie_takes_lower() -> None:
    assert _process_key(_two_process_printer(), 0.16) == "0.12"


async def test_slice_at_non_exact_height_overrides_layer_height_and_names_the_process(
    tmp_path: Path,
) -> None:
    cli = _both(tmp_path, FakeRunner())
    _set_machine_range(tmp_path, ["0.08"], ["0.3"])
    result = await cli.slice(replace(_request(tmp_path, K1C), layer_height_mm=0.28))
    assert result.passed is True and result.process_profile == K1C_LEAVES["process"]
    process = json.loads((tmp_path / "out" / "process.json").read_text(encoding="utf-8"))
    assert process["layer_height"] == "0.28"


def test_height_outside_machine_range_rejected(tmp_path: Path) -> None:
    cli = _both(tmp_path, FakeRunner())
    _set_machine_range(tmp_path, ["0.08"], ["0.3"])
    with pytest.raises(LayerHeightError) as info:
        cli.check_target(K1C, 0.5, "PLA")
    assert str(info.value) == f"layer_height_mm 0.5 is outside {K1C}'s range 0.08–0.3 mm"
    with pytest.raises(LayerHeightError, match="0.05"):
        cli.check_target(K1C, 0.05, "PLA")
    assert cli.check_target(K1C, 0.3, "PLA").process_profile  # the bounds are inclusive


def test_machine_without_a_range_accepts_only_exact_keys(tmp_path: Path) -> None:
    cli = _both(tmp_path, FakeRunner())  # the fake machine profile declares no range
    assert cli.check_target(K1C, 0.2, "PLA").process_profile
    with pytest.raises(LayerHeightError, match="declares no layer-height range.*0.20"):
        cli.check_target(K1C, 0.28, "PLA")


def test_layer_ranges_come_from_the_flattened_machine_profiles(tmp_path: Path) -> None:
    cli = _both(tmp_path, FakeRunner())
    assert cli.machine_facts()[K1C].layer_range is None  # the fake machine declares no range
    _set_machine_range(tmp_path, ["0.08"], ["0.3"])
    assert cli.machine_facts()[K1C].layer_range == (0.08, 0.3)
    assert set(cli.machine_facts()) == {p.id for p in cli.printers()}


def test_machine_facts_name_the_unreadable_profile(tmp_path: Path) -> None:
    catalog = load_printer_catalog()
    k1c = replace(catalog.printer(K1C), processes=(("0.20", "No Such Process @K1C"),))
    others = tuple(p for p in catalog.printers if p.id != K1C)
    cli = _both(tmp_path, FakeRunner(), replace(catalog, printers=(*others, k1c)))
    facts = cli.machine_facts()
    assert set(facts) == {p.id for p in cli.printers()}
    assert isinstance(facts[K1C], str) and "No Such Process @K1C" in facts[K1C]
    assert not isinstance(facts[P2S], str)  # the readable printer keeps its facts
