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

    selected = {"spec": {"source": {"root_dir": "models/selected"}}, "native": {"available": False}}
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
