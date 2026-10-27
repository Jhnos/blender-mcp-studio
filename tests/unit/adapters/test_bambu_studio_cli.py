"""Bambu Studio CLI adapter: v80 command line, evidence files, failures. Fake runner only."""

import json
import plistlib
import subprocess
from pathlib import Path

import pytest

import src.adapters.slicing.bambu_studio_cli as cli_module
from src.adapters.slicing.bambu_studio_cli import (
    SLICE_TIMEOUT_S,
    SLOWEST_SLICE_MEASURED_S,
    BambuStudioCli,
)
from src.core.domain.model_spec import PrintTarget
from src.core.domain.slicing import SliceRequest, ToolUnavailableError
from tests.fakes.bambu_bundle import make_bundle

_PROFILES = Path(cli_module.__file__).resolve().parents[3] / "config" / "slicer-profiles"


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


def _request(tmp_path: Path, **over: object) -> SliceRequest:
    return SliceRequest.from_target(
        str(tmp_path / "gate.3mf"),
        str(tmp_path / "out"),
        PrintTarget(**over),  # type: ignore[arg-type]
    )


def _cli(tmp_path: Path, runner: FakeRunner, binary: Path | None = None) -> BambuStudioCli:
    return BambuStudioCli(binary or _binary(tmp_path), profiles_dir=_PROFILES, runner=runner)


def test_timeout_is_five_times_the_measured_slowest() -> None:
    assert SLOWEST_SLICE_MEASURED_S == 171
    assert SLICE_TIMEOUT_S == 5 * 171


def test_from_target_carries_every_print_default() -> None:
    req = SliceRequest.from_target("/a.3mf", "/out", PrintTarget())
    assert (req.printer, req.material, req.layer_height_mm) == ("bambu-p2s", "PLA", 0.2)
    assert (req.support, req.brim_mm) == (True, 3.0)
    assert (req.input_3mf, req.output_dir) == ("/a.3mf", "/out")


async def test_availability_reports_missing_binary(tmp_path: Path) -> None:
    cli = BambuStudioCli(tmp_path / "nope", profiles_dir=_PROFILES, runner=FakeRunner())
    status = await cli.availability()
    assert status.available is False
    assert status.path is None
    assert "BambuStudio.app" in status.install_hint


async def test_availability_reads_version_from_info_plist(tmp_path: Path) -> None:
    binary = _binary(tmp_path)
    plist = binary.parents[1] / "Info.plist"
    plist.write_bytes(plistlib.dumps({"CFBundleShortVersionString": "02.06.00.51"}))
    status = await _cli(tmp_path, FakeRunner(), binary).availability()
    assert status.available is True
    assert status.version == "02.06.00.51"
    assert status.path == str(binary)


async def test_availability_version_is_none_without_plist(tmp_path: Path) -> None:
    status = await _cli(tmp_path, FakeRunner()).availability()
    assert status.available is True
    assert status.version is None


async def test_slice_reports_missing_binary(tmp_path: Path) -> None:
    cli = BambuStudioCli(tmp_path / "nope", profiles_dir=_PROFILES, runner=FakeRunner())
    with pytest.raises(ToolUnavailableError, match="BambuStudio.app"):
        await cli.slice(_request(tmp_path))


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
    assert after("--debug") == "2"
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
        raise subprocess.TimeoutExpired(argv, SLICE_TIMEOUT_S)

    cli = BambuStudioCli(_binary(tmp_path), profiles_dir=_PROFILES, runner=hang)
    result = await cli.slice(_request(tmp_path))
    assert result.passed is False
    assert result.output_3mf is None
    assert f"slicer did not finish within {SLICE_TIMEOUT_S:g}s" in result.message


async def test_slice_rejects_unsupported_printer(tmp_path: Path) -> None:
    req = SliceRequest.from_target(
        str(tmp_path / "a.3mf"), str(tmp_path / "out"), PrintTarget(printer="other")
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
    assert data["enable_prime_tower"] == "0"
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
    cli = BambuStudioCli(tmp_path / "nope", profiles_dir=_PROFILES, runner=FakeRunner())
    req = SliceRequest.from_target("/a.3mf", str(tmp_path / "out"), PrintTarget(printer="x1c"))
    result = await cli.slice(req)
    assert result.passed is False
    assert "x1c" in result.message


async def test_failed_vendor_sidecars_are_confined_to_the_job_with_relative_inputs(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    class SidecarRunner(FakeRunner):
        def __call__(self, argv, **kwargs):
            (Path(kwargs.get("cwd", Path.cwd())) / "result.json").write_text("vendor failure")
            return super().__call__(argv, **kwargs)

    runner = SidecarRunner(returncode=250, write_output=False)
    request = SliceRequest.from_target("input.3mf", "job", PrintTarget())
    result = await _cli(tmp_path, runner).slice(request)
    assert not result.passed
    assert not (tmp_path / "result.json").exists()
    assert (tmp_path / "job/result.json").read_text() == "vendor failure"
    assert runner.kwargs["cwd"] == tmp_path / "job"
    assert runner.argv[-1] == str(tmp_path / "input.3mf")
