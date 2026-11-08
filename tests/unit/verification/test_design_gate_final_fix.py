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
        AsyncMock(return_value={"spec": {"source": {"root_dir": "selected"}}, "native": {}}),
    )
    monkeypatch.setattr(gate, "check_deliverable", lambda *_: [])
    monkeypatch.setattr(gate, "check_native_source", lambda *_: [])
    monkeypatch.setattr(gate, "check_slicer", lambda *_: [])
    monkeypatch.setattr(real, "_tool", AsyncMock(return_value=[]))
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
