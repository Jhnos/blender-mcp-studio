"""Final fix round: spec v1 contract, openable evidence, checksummed sources, clean messages."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.core.domain.design_run import StageName, StageOutcome
from src.core.domain.mesh_integrity import MeshIntegrityReport, MeshVerdict
from src.core.domain.model_spec import ModelSpecError, parse_model_spec
from src.core.use_cases import design_stages as stages
from tests.unit.core.test_design_pipeline import _payload, _rig, _run

_CONTRACT = (
    Path(__file__).resolve().parents[3] / "scripts/verify/contracts/design_pipeline_v78.json"
)


def _spec(tmp_path: Path, **extra: object) -> dict[str, object]:
    (tmp_path / "v78").mkdir(exist_ok=True)
    return {"spec_version": "1", "name": "n", "source": {"root_dir": "v78"}, **extra}


def test_spec_v1_rejects_mechanism_suites(tmp_path):
    with pytest.raises(ModelSpecError) as info:
        parse_model_spec(
            _spec(tmp_path, mechanism={"suites": ["hand"]}), artifact_roots=(tmp_path,)
        )
    assert str(info.value) == (
        "mechanism suites are not supported in spec v1: Phase 1 verifies imported artifacts "
        "only; suites run against the open Blender scene, not this model"
    )
    spec = parse_model_spec(_spec(tmp_path, mechanism={"suites": []}), artifact_roots=(tmp_path,))
    assert spec.mechanism.suites == ()


async def test_mechanism_not_applicable_message_names_phase1(tmp_path):
    rig = _rig(tmp_path)
    _, _, report = await _run(rig, _payload(rig))
    mechanism = report.stages[2]
    assert mechanism.outcome is StageOutcome.NOT_APPLICABLE
    assert mechanism.message == "mechanism not evaluated in Phase 1 (import path)"


@pytest.mark.parametrize(
    ("section", "allowed"),
    [
        (None, "spec_version, name, source, print_target, mechanism"),
        ("source", "root_dir, stl_glob, project_3mf"),
        ("print_target", "printer, material, layer_height_mm, support, brim_mm"),
        ("mechanism", "suites"),
    ],
)
def test_unknown_key_error_lists_allowed_keys(tmp_path, section, allowed):
    payload = _spec(tmp_path)
    if section is None:
        payload["bogus"] = 1
    else:
        payload.setdefault(section, {})
        payload[section] = {**payload[section], "bogus": 1}  # type: ignore[dict-item]
    with pytest.raises(ModelSpecError) as info:
        parse_model_spec(payload, artifact_roots=(tmp_path,))
    where = section or "spec"
    assert str(info.value) == f"unknown keys in {where}: bogus (allowed: {allowed})"


@pytest.mark.parametrize(
    ("target", "message"),
    [
        ({"printer": "x1c"}, "unsupported print_target.printer 'x1c'; supported: bambu-p2s"),
        ({"material": "PETG"}, "unsupported print_target.material 'PETG'; supported: PLA"),
    ],
)
async def test_unsupported_printer_rejected_at_submit(tmp_path, target, message):
    rig = _rig(tmp_path)
    payload = {**_payload(rig), "print_target": target}
    with pytest.raises(ModelSpecError) as info:
        await rig.pipeline.submit(payload)
    assert str(info.value) == message
    assert rig.jobs.records == {} and not rig.runs.exists()


async def test_every_passed_stage_has_openable_evidence(tmp_path):
    rig = _rig(tmp_path)
    job, _, report = await _run(rig, _payload(rig))
    passed = [s for s in report.stages if s.outcome is StageOutcome.PASSED]
    assert [s.name for s in passed] == [
        StageName.IMPORT,
        StageName.GEOMETRY,
        StageName.PRINT,
        StageName.PACKAGE,
    ]
    for stage in passed:
        assert stage.evidence, stage.name
        for name in stage.evidence:
            assert not Path(name).is_absolute(), (stage.name, name)
            assert rig.pipeline.run_file(job.run_id, name).is_file(), (stage.name, name)


async def test_import_json_checksums_every_source(tmp_path):
    rig = _rig(tmp_path)
    (rig.root / "STL" / "notes.txt").write_text("skip me")
    job, _, report = await _run(rig, _payload(rig))
    assert report.stages[0].evidence == ("import.json",)
    doc = json.loads((rig.runs / job.run_id / "import.json").read_text(encoding="utf-8"))
    assert [row["path"] for row in doc["stls"]] == ["STL/a.stl", "STL/b.stl"]
    for row in (*doc["stls"], doc["project_3mf"]):
        data = (rig.root / row["path"]).read_bytes()
        assert row["sha256"] == hashlib.sha256(data).hexdigest() and row["bytes"] == len(data)
    assert doc["project_3mf"]["path"] == "p.3mf"
    assert doc["skipped"] == []  # the glob is STL/*.stl, so notes.txt never matched
    files = rig.packaging.calls[0][3]
    assert "import.json" in files and "geometry.json" in files
    assert str(tmp_path) not in json.dumps(doc)


async def test_geometry_json_holds_relative_verdicts(tmp_path):
    rig = _rig(tmp_path, geometry_ok=False)
    job, _, report = await _run(rig, _payload(rig))
    geometry = report.stages[1]
    assert geometry.evidence == ("geometry.json",)
    doc = json.loads((rig.runs / job.run_id / "geometry.json").read_text(encoding="utf-8"))
    assert doc["passed"] is False
    assert [v["path"] for v in doc["verdicts"]] == ["STL/a.stl", "STL/b.stl"]
    assert str(tmp_path) not in json.dumps(doc)


async def test_geometry_message_names_the_path_once(tmp_path):
    root = tmp_path / "art"
    stl = root / "STL" / "a.stl"

    class PrefixedIntegrity:
        async def check(self, stl_paths):
            return MeshIntegrityReport(
                (MeshVerdict(str(stl), 0, 0, False, None, f"{stl}: cannot read STL: short"),)
            )

    state = stages.RunState(root=str(root), stls=(str(stl),))
    report = await stages.geometry_stage(PrefixedIntegrity(), state, tmp_path)
    assert report.message == "STL/a.stl: cannot read STL: short"


async def test_submit_store_failure_error_is_scrubbed(tmp_path):
    rig = _rig(tmp_path)
    rig.runs.write_text("not a directory")  # run_dir.mkdir fails with a host path in the text
    with pytest.raises(OSError):
        await rig.pipeline.submit(_payload(rig))
    (record,) = rig.jobs.records.values()
    assert record.error and str(tmp_path) not in record.error


def test_contract_spec_is_the_documented_example():
    from src.core.domain.model_spec_schema import V1_EXAMPLE

    contract = json.loads(_CONTRACT.read_text(encoding="utf-8"))
    assert contract["spec"] == V1_EXAMPLE
