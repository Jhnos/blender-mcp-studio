"""Tool-path inspection inside the vendor-neutral adapter (ported from main's Bambu-only adapter).

Whether a slicer's output is inspected is catalog data (``toolpath_inspection`` in
``config/slicers.yaml``): Bambu Studio is inspected, OrcaSlicer is not. No test here names a
vendor in a branch of the adapter; each picks a printer whose slicer has the flag it needs.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from src.adapters.slicing.orca_family_cli import SLICE_TIMEOUT_S, OrcaFamilyCli
from src.adapters.slicing.toolpath_evidence import TOOLPATH_INSPECTION_TIMEOUT_S
from src.core.domain.model_spec import PrintTarget
from src.core.domain.slicing import SliceRequest
from src.infrastructure.printer_catalog_loader import load_printer_catalog
from tests.fakes.bambu_bundle import TEST_LIMITS, make_bundle, make_orca_bundle, write_sliced_output
from tests.fakes.plate_3mf import translate, write_3mf
from tests.unit.adapters.test_orca_family_cli import _PROFILES

P2S, K1C = "bambu-p2s-0.4", "creality-k1c-0.4"  # inspected / not inspected (catalog data)


class Runner:
    """Writes a minimal sliced archive (``write_sliced_output``) unless told otherwise."""

    def __init__(self, returncode: int = 0, output: bytes | None = None) -> None:
        self.returncode, self.output = returncode, output
        self.argv: list[str] = []
        self.kwargs: dict[str, object] = {}

    def __call__(self, argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.argv, self.kwargs = list(argv), kwargs
        out = Path(argv[argv.index("--outputdir") + 1])
        target = out / argv[argv.index("--export-3mf") + 1]
        kwargs["stdout"].write("ok\n")  # type: ignore[attr-defined]
        if self.returncode == 0:
            if self.output is None:
                write_sliced_output(target)
            else:
                target.write_bytes(self.output)
            (out / "effective-settings.json").write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(argv, self.returncode)


def _cli(tmp_path: Path, runner: Runner) -> OrcaFamilyCli:
    return OrcaFamilyCli(
        load_printer_catalog(),
        {"bambu-studio": make_bundle(tmp_path), "orcaslicer": make_orca_bundle(tmp_path)},
        overrides_dir=_PROFILES,
        limits=TEST_LIMITS,
        runner=runner,
    )


def _request(tmp_path: Path, printer: str, *, inp: str | None = None, out: str | None = None):
    source = tmp_path / "gate.3mf"
    if not source.exists():
        write_3mf(source, [(10, translate(10, 10))])
    return SliceRequest.from_target(
        inp or str(source),
        out or str(tmp_path / "out"),
        PrintTarget(printer, "PLA"),
        printer_id=printer,
    )


def test_port_deadline_adds_the_inspection_only_where_the_catalog_inspects(tmp_path):
    cli = _cli(tmp_path, Runner())
    assert cli.timeout_s(P2S) == SLICE_TIMEOUT_S["bambu-studio"] + TOOLPATH_INSPECTION_TIMEOUT_S
    assert cli.timeout_s(K1C) == SLICE_TIMEOUT_S["orcaslicer"]
    assert cli.max_timeout_s() == max(cli.timeout_s(P2S), cli.timeout_s(K1C))


async def test_subprocess_deadline_is_the_slicer_command_alone(tmp_path):
    runner = Runner()
    await _cli(tmp_path, runner).slice(_request(tmp_path, P2S))
    assert runner.kwargs["timeout"] == SLICE_TIMEOUT_S["bambu-studio"]


async def test_inspected_slice_writes_extrusion_evidence(tmp_path):
    result = await _cli(tmp_path, Runner()).slice(_request(tmp_path, P2S))
    assert result.passed, result.message
    report = json.loads((tmp_path / "out" / "extrusion.json").read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert report["plates"][0]["print_profile"]["printer_model"] == "Bambu Lab P2S"


async def test_exit_zero_cannot_accept_a_malformed_sliced_archive(tmp_path):
    result = await _cli(tmp_path, Runner(output=b"not a sliced archive")).slice(
        _request(tmp_path, P2S)
    )
    assert not result.passed and "toolpath" in result.message
    assert (tmp_path / "out" / "extrusion.json").is_file()


async def test_previous_extrusion_evidence_is_removed_before_the_run(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "extrusion.json").write_text('{"passed": true}', encoding="utf-8")
    result = await _cli(tmp_path, Runner(returncode=250)).slice(_request(tmp_path, P2S))
    assert not result.passed
    assert not (out / "extrusion.json").exists()


async def test_slicer_without_inspection_writes_no_extrusion_evidence(tmp_path):
    result = await _cli(tmp_path, Runner(output=b"3mf")).slice(_request(tmp_path, K1C))
    assert result.passed, result.message
    assert not (tmp_path / "out" / "extrusion.json").exists()


async def test_vendor_sidecars_stay_in_the_job_with_relative_inputs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    class Sidecar(Runner):
        def __call__(self, argv, **kwargs):
            (Path(kwargs.get("cwd", Path.cwd())) / "result.json").write_text("vendor failure")
            return super().__call__(argv, **kwargs)

    write_3mf(tmp_path / "input.3mf", [(10, translate(10, 10))])
    runner = Sidecar(returncode=250)
    result = await _cli(tmp_path, runner).slice(_request(tmp_path, P2S, inp="input.3mf", out="job"))
    assert not result.passed
    assert not (tmp_path / "result.json").exists()
    assert (tmp_path / "job" / "result.json").read_text() == "vendor failure"
    assert runner.kwargs["cwd"] == tmp_path / "job"
    assert runner.argv[-1] == str(tmp_path / "input.3mf")
    assert Path(runner.argv[0]).is_absolute()


async def test_arc_fitting_is_a_job_key_where_the_output_is_inspected(tmp_path):
    cli = _cli(tmp_path, Runner(output=b"3mf"))
    await cli.slice(_request(tmp_path, P2S, out=str(tmp_path / "p2s")))
    await cli.slice(_request(tmp_path, K1C, out=str(tmp_path / "k1c")))
    p2s = json.loads((tmp_path / "p2s" / "process.json").read_text(encoding="utf-8"))
    k1c = json.loads((tmp_path / "k1c" / "process.json").read_text(encoding="utf-8"))
    assert p2s["enable_arc_fitting"] == "0"
    assert "enable_arc_fitting" not in k1c  # not inspected: the bundle profile's choice stands
