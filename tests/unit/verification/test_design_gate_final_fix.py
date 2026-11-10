"""Design gate after the final fix round: stage evidence files and the configured artifact root."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.verify import design_gate_checks as gate
from scripts.verify import design_pipeline_verify_real as real
from src.infrastructure.tools_config import load_tools_config

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = json.loads(
    (ROOT / "scripts/verify/contracts/archive/design_pipeline_v78.json").read_text()
)
EXPECT = CONTRACT["expect"]


def _import_doc(stls: int, project: bool = True) -> dict:
    row = {"path": "x", "sha256": "0" * 64, "bytes": 1}
    return {"stls": [row] * stls, "project_3mf": row if project else None, "skipped": []}


def test_contract_manifest_grows_by_the_two_stage_evidence_files() -> None:
    files = EXPECT["manifest_files"]
    assert "import.json" in files and "geometry.json" in files and len(files) == 8
    assert (EXPECT["stl_count"], EXPECT["import_3mf"]) == (69, 1)


def test_import_json_must_list_69_stls_and_the_3mf() -> None:
    assert gate.check_import_json(_import_doc(69), EXPECT) == []
    assert gate.check_import_json(_import_doc(68), EXPECT) == [
        "import.json lists 68 STL(s), expected 69"
    ]
    assert gate.check_import_json(_import_doc(69, project=False), EXPECT) == [
        "import.json lists 0 project 3MF(s), expected 1"
    ]


def test_import_and_geometry_stages_need_evidence() -> None:
    report = {
        "passed": True,
        "stages": [
            {"name": n, "outcome": o, "metrics": [], "evidence": [], "message": ""}
            for n, o in (
                ("import", "passed"),
                ("geometry", "passed"),
                ("mechanism", "not_applicable"),
                ("print", "passed"),
                ("package", "passed"),
            )
        ],
    }
    failures = gate.check_report(report, EXPECT)
    assert "import stage lists no evidence paths" in failures
    assert "geometry stage lists no evidence paths" in failures


def test_artifact_root_comes_from_tools_config_with_override(tmp_path: Path) -> None:
    assert real.artifact_root(None) == load_tools_config().artifact_roots[0]
    assert real.artifact_root(tmp_path) == tmp_path


async def test_native_source_oracle_detects_stale_and_incomplete_receipts(tmp_path):
    import copy
    from dataclasses import asdict

    from tests.unit.adapters.test_native_source import fixture

    root, manifest, spec, reader = fixture(tmp_path)
    receipt = {
        **asdict(await reader.resolve(spec)),
        "available": True,
        "scope": "file_identity_only",
    }
    selected = {
        "name": spec.name,
        "source": {
            "root_dir": "models/selected",
            "stl_glob": spec.source.stl_glob,
            "project_3mf": "plate.3mf",
        },
    }
    assert gate.check_native_source(tmp_path, selected, receipt) == []
    for field, value in (
        ("available", False),
        ("scope", "manufacturing_ready"),
        ("model_name", "old"),
        ("root_dir", "old"),
        ("manifest_sha256", "0" * 64),
        ("verified_files", 4),
        ("parts", receipt["parts"][:1]),
        ("project_3mf", None),
    ):
        damaged = copy.deepcopy(receipt)
        damaged[field] = value
        assert gate.check_native_source(tmp_path, selected, damaged), field
    damaged = copy.deepcopy(receipt)
    damaged["native"]["sha256"] = "0" * 64
    assert gate.check_native_source(tmp_path, selected, damaged)
    (root / "native.blend").write_bytes(b"changed")
    assert gate.check_native_source(tmp_path, selected, receipt)


async def test_real_session_rejects_native_provenance_before_submitting(monkeypatch, tmp_path):
    from unittest.mock import AsyncMock

    class Context:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *_):
            pass

    selected = {
        "selection": "current",
        "spec": {"source": {"root_dir": "models/selected"}},
        "native": {"available": False},
    }
    monkeypatch.setattr(real, "Client", lambda _: Context())
    monkeypatch.setattr(real, "_selected_contract", AsyncMock(return_value=selected))
    monkeypatch.setattr(gate, "check_deliverable", lambda *_: [])

    def oracle(*_):
        return ["native source rejected"]

    monkeypatch.setattr(gate, "check_native_source", oracle, raising=False)
    monkeypatch.setattr(
        real,
        "_tool",
        AsyncMock(side_effect=AssertionError("native oracle must precede tool probe")),
    )
    submit = AsyncMock(side_effect=AssertionError("must reject before submission"))
    monkeypatch.setattr(real, "_positive", submit)
    failures = await real._session({}, "https://unused", tmp_path)
    assert failures == ["native source rejected"]
    submit.assert_not_awaited()


async def test_public_job_observation_failure_never_replays_a_submission(monkeypatch, tmp_path):
    from unittest.mock import AsyncMock

    class Context:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *_):
            pass

    monkeypatch.setattr(real, "Client", lambda _: Context())
    monkeypatch.setattr(
        real,
        "_selected_contract",
        # Rule change (task 18): a gate names its printer and list_printers must list it, so
        # the resolved contract carries a print_target and both printer checks are stubbed.
        AsyncMock(
            return_value={
                "spec": {"source": {"root_dir": "selected"}},
                "native": {},
                "print_target": {"printer": "bambu-p2s-0.4", "material": "PLA"},
            }
        ),
    )
    monkeypatch.setattr(gate, "check_deliverable", lambda *_: [])
    monkeypatch.setattr(gate, "check_native_source", lambda *_: [])
    monkeypatch.setattr(gate, "check_slicer", lambda *_: [])
    monkeypatch.setattr(gate, "check_printer_listed", lambda *_: [])
    monkeypatch.setattr(real, "_tool", AsyncMock(return_value={}))
    submitted = AsyncMock(side_effect=ConnectionError("job reply lost after submission"))
    monkeypatch.setattr(real, "_positive", submitted)
    failures = await real._session(
        {"expect": {"slicer_tool": "slicer"}}, "https://unused", tmp_path
    )
    assert failures and submitted.await_count == 1


async def test_current_gate_counts_verified_parts_after_a_catalog_change(tmp_path):
    import hashlib
    from dataclasses import asdict

    import pytest

    from tests.unit.adapters.test_native_source import fixture

    root, manifest, spec, reader = fixture(tmp_path)
    selected = {
        "name": spec.name,
        "source": {
            "root_dir": "models/selected",
            "stl_glob": spec.source.stl_glob,
            "project_3mf": "plate.3mf",
        },
    }
    contract = {"selection": "current", "expect": {"plates": 1}}

    async def read():
        return {
            "available": True,
            "scope": "file_identity_only",
            **asdict(await reader.resolve(spec)),
        }

    initial = await read()
    resolved = real._verified_delivery(tmp_path, {**contract, "spec": selected, "native": initial})
    assert resolved["expect"] == {"plates": 1, "stl_count": 2, "geometry_checked": 2}

    part = "STL/列印零件/c.stl"
    (root / part).write_bytes(b"new real part")
    manifest[part] = hashlib.sha256(b"new real part").hexdigest()
    (root / "SHA256.json").write_text(json.dumps(manifest))
    with pytest.raises(gate.GateError, match="provenance"):
        real._verified_delivery(tmp_path, {**contract, "spec": selected, "native": initial})

    updated = await read()
    resolved = real._verified_delivery(tmp_path, {**contract, "spec": selected, "native": updated})
    assert resolved["expect"] == {"plates": 1, "stl_count": 3, "geometry_checked": 3}
    assert contract["expect"] == {"plates": 1}
    with pytest.raises(gate.GateError, match="derive"):
        real._verified_delivery(
            tmp_path,
            {**contract, "spec": selected, "native": updated, "expect": {"stl_count": 2}},
        )


def test_import_identity_rejects_substitution_even_if_counts_match():
    native = {
        "parts": [
            {"path": "parts/a.stl", "size_bytes": 100, "sha256": "a" * 64},
            {"path": "parts/b.stl", "size_bytes": 100, "sha256": "b" * 64},
        ],
        "project_3mf": {"path": "plate.3mf", "size_bytes": 200, "sha256": "c" * 64},
    }
    a, b = ({"path": f"parts/{part}.stl", "bytes": 100, "sha256": part * 64} for part in "ab")
    plate = {"path": "plate.3mf", "bytes": 200, "sha256": "c" * 64}
    assert gate.check_import_source({"stls": [b, a], "project_3mf": plate}, native) == []
    assert gate.check_import_source({"stls": [a, a], "project_3mf": plate}, native)
    assert gate.check_import_source(
        {"stls": [a, {**b, "sha256": "x" * 64}], "project_3mf": plate}, native
    )
    assert gate.check_import_source(
        {"stls": [a, b], "project_3mf": {**plate, "bytes": 201}}, native
    )


async def test_current_workstation_gate_rejects_stale_evidence_even_with_updated_checksums(
    tmp_path,
):
    import hashlib
    import shutil
    from dataclasses import asdict

    import pytest

    from src.adapters.artifacts.native_source import FilesystemNativeSource
    from src.core.domain.model_spec import parse_model_spec

    contract = json.loads(
        (ROOT / "scripts/verify/contracts/design_pipeline_current.json").read_text()
    )
    selected = json.loads((ROOT / "models/lab-station/model-spec.json").read_text())
    relative = Path(selected["source"]["root_dir"])
    delivery = tmp_path / relative
    shutil.copytree(ROOT / relative, delivery)
    tools = load_tools_config()
    spec = parse_model_spec(selected, artifact_roots=(tmp_path,))
    reader = FilesystemNativeSource((tmp_path,), tools.import_limits)

    async def verify():
        native = {
            **asdict(await reader.resolve(spec)),
            "available": True,
            "scope": "file_identity_only",
        }
        return real._verified_delivery(tmp_path, {**contract, "spec": selected, "native": native})

    assert (await verify())["expect"]["stl_count"] == len(list(delivery.glob(spec.source.stl_glob)))
    manifest_path = delivery / "SHA256.json"
    original_manifest = json.loads(manifest_path.read_bytes())
    synchronization = "驗證/synchronized-native-result.json"
    evidence = json.loads((delivery / synchronization).read_bytes())
    if evidence.get("format_version") == 2:
        part = next(iter(evidence["slice"]["input_stl_sha256_by_owner"]))
        stale_stl = ("slice", "input_stl_sha256_by_owner", part)
        stale_stl_message = "sliced STL inventory"
    else:
        stale_stl = ("slice", "revised_surface_sha256")
        stale_stl_message = "sliced revised STL"
    cases = (
        ("驗證/motion-dense.json", ("native_sha256",), "motion native source"),
        (synchronization, ("render_native_sha256",), "render native source"),
        (synchronization, ("slice", "sliced_sha256"), "sliced project"),
        (synchronization, stale_stl, stale_stl_message),
        ("驗證/extrusion.json", ("source", "sha256"), "extrusion project"),
        ("驗證/fit-toolpath.json", ("source_sha256",), "fit toolpath project"),
    )
    if "驗證/rear-service.json" in original_manifest:
        cases += (("驗證/rear-service.json", ("native_sha256",), "rear-service native source"),)
    if "驗證/rear-support-clearance.json" in original_manifest:
        cases += (
            (
                "驗證/rear-support-clearance.json",
                ("sliced_sha256",),
                "rear-support-clearance sliced project",
            ),
        )
    for name, keys, expected in cases:
        path = delivery / name
        original = path.read_bytes()
        doc = json.loads(original)
        row = doc
        for key in keys[:-1]:
            row = row[key]
        row[keys[-1]] = "0" * 64
        path.write_text(json.dumps(doc))
        manifest = {**original_manifest, name: hashlib.sha256(path.read_bytes()).hexdigest()}
        manifest_path.write_text(json.dumps(manifest))
        with pytest.raises(gate.GateError, match=expected):
            await verify()
        path.write_bytes(original)
        manifest_path.write_text(json.dumps(original_manifest))

    published_project = selected["source"]["project_3mf"]
    stale_project = next((ROOT / "models/lab-station-v80").glob("*.3mf"))
    shutil.copyfile(stale_project, delivery / published_project)
    manifest = {
        **original_manifest,
        published_project: hashlib.sha256(stale_project.read_bytes()).hexdigest(),
    }
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(gate.GateError, match="sliced project"):
        await verify()
    shutil.copyfile(ROOT / relative / published_project, delivery / published_project)

    renders = [name for name in original_manifest if name.endswith(".png")]
    replaced, other = renders[:2]
    shutil.copyfile(delivery / other, delivery / replaced)
    manifest = {**original_manifest, replaced: original_manifest[other]}
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(gate.GateError, match="render inventory"):
        await verify()


def test_workstation_inventory_evidence_requires_every_part_at_each_step(tmp_path: Path) -> None:
    from scripts.verify.lab_station_delivery_checks import check_delivery

    selected = tmp_path / "selected"
    directory = selected / "驗證"
    directory.mkdir(parents=True)
    parts = {"lid": "a" * 64, "rear": "b" * 64, "original_pin": "c" * 64}
    native_sha, plate_sha, render_sha = ("d" * 64, "e" * 64, "f" * 64)
    evidence = {
        "format_version": 2,
        "native": {
            "native_sha256": native_sha,
            "stl_sha256_by_owner": dict(parts),
            "reopened_stl_sha256_by_owner": dict(parts),
        },
        "slice": {"sliced_sha256": plate_sha, "parts": 3, "input_stl_sha256_by_owner": dict(parts)},
        "render_native_sha256": native_sha,
        "render_sha256": {"assembly.png": render_sha},
    }
    files = {
        "synchronized-native-result": evidence,
        "motion-dense": {"native_sha256": native_sha},
        "extrusion": {"source": {"sha256": plate_sha}},
        "fit-toolpath": {
            "source_sha256": plate_sha,
            "bed_model_paths_by_part": dict.fromkeys(parts, 1),
        },
    }
    manifest = {
        **dict.fromkeys((f"驗證/{name}.json" for name in files), "0" * 64),
        "assembly.png": render_sha,
    }
    manifest_path = selected / "SHA256.json"
    manifest_path.write_text(json.dumps(manifest))
    for name, payload in files.items():
        (directory / f"{name}.json").write_text(json.dumps(payload))
    receipt = {
        "root_dir": "selected",
        "native": {"sha256": native_sha},
        "project_3mf": {"sha256": plate_sha},
        "parts": [{"path": f"parts/{name}.stl", "sha256": sha} for name, sha in parts.items()],
    }
    assert check_delivery(tmp_path, receipt) == []

    path = directory / "synchronized-native-result.json"
    for stage, field, message in (
        ("native", "stl_sha256_by_owner", "exported STL inventory"),
        ("native", "reopened_stl_sha256_by_owner", "reopened STL inventory"),
        ("slice", "input_stl_sha256_by_owner", "sliced STL inventory"),
    ):
        for corrupted in (
            {name: value for name, value in parts.items() if name != "original_pin"},
            {**parts, "rear": parts["lid"]},
            {**parts, "unexpected": parts["lid"]},
        ):
            damaged = {**evidence, stage: {**evidence[stage], field: corrupted}}
            path.write_text(json.dumps(damaged))
            assert any(message in error for error in check_delivery(tmp_path, receipt))
    path.write_text(json.dumps({**evidence, "format_version": 3}))
    assert any("unsupported" in error for error in check_delivery(tmp_path, receipt))
    path.write_text(json.dumps(evidence))

    gcode_sha = "1" * 64
    (directory / "extrusion.json").write_text(
        json.dumps({**files["extrusion"], "plates": [{"gcode_sha256": gcode_sha}]})
    )
    bore = {
        "native_sha256": native_sha,
        "source_sha256": plate_sha,
        "gcode_sha256": gcode_sha,
        "checked_early_depositions": 20,
        "clear_radius_lower_mm": 7.48,
    }
    bore_path = directory / "bulkhead-bore.json"
    bore_path.write_text(json.dumps(bore))
    manifest_path.write_text(json.dumps({**manifest, "驗證/bulkhead-bore.json": "0" * 64}))
    assert check_delivery(tmp_path, receipt) == []
    for field, stale, message in (
        ("native_sha256", "2" * 64, "bulkhead-bore native source"),
        ("source_sha256", "2" * 64, "bulkhead-bore sliced project"),
        ("gcode_sha256", "2" * 64, "bulkhead-bore G-code"),
        ("clear_radius_lower_mm", -0.145, "bulkhead-bore clearance"),
        ("clear_radius_lower_mm", float("inf"), "bulkhead-bore clearance"),
        ("checked_early_depositions", 0, "bulkhead-bore clearance"),
    ):
        bore_path.write_text(json.dumps({**bore, field: stale}))
        assert any(message in error for error in check_delivery(tmp_path, receipt))
    bore_path.write_text(json.dumps(bore))

    receipt["parts"].append({"path": "elsewhere/lid.stl", "sha256": parts["lid"]})
    assert any("duplicate" in error for error in check_delivery(tmp_path, receipt))
