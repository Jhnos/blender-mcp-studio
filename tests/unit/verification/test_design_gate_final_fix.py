"""Design gate after the final fix round: stage evidence files and the configured artifact root."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.verify import design_gate_checks as gate
from scripts.verify import design_pipeline_verify_real as real
from src.infrastructure.tools_config import load_tools_config

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = json.loads((ROOT / "scripts/verify/contracts/design_pipeline_v78.json").read_text())
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
