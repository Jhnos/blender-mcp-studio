"""One selected delivery for Claude Code, discovery, schema examples and the real gate."""

import copy
import hashlib
import json
from pathlib import Path

from src.core.domain.model_spec_schema import V1_EXAMPLE
from src.core.use_cases.artifact_catalog import list_artifacts
from src.infrastructure.tools_config import load_tools_config

ROOT = Path(__file__).resolve().parents[3]


def test_shared_entry_selects_v80_and_rejects_missing_default(tmp_path):
    old = tmp_path / "old-v78"
    old.mkdir()
    (old / "old.3mf").write_bytes(b"old")
    result = list_artifacts((tmp_path,), max_stl_files=100)
    assert result["default_spec"]["name"] == "lab-station-v80"
    assert result["default_available"] is False  # Never infer 'latest' from directory order.
    spec = copy.deepcopy(result["default_spec"])
    selected = tmp_path / spec["source"]["root_dir"]
    (selected / "STL/列印零件").mkdir(parents=True)
    (selected / "STL/列印零件/a.stl").write_bytes(b"fixture")
    (selected / spec["source"]["project_3mf"]).write_bytes(b"fixture")
    result = list_artifacts((tmp_path,), max_stl_files=100)
    assert result["default_available"] is True
    assert result["artifacts"][0]["root_dir"] == spec["source"]["root_dir"]
    assert any(r["root_dir"] == "old-v78" for r in result["artifacts"])


def test_claude_mcp_and_real_gate_share_selected_spec():
    shared = json.loads((ROOT / "models/lab-station/model-spec.json").read_text())
    assert shared == V1_EXAMPLE
    assert shared == json.loads(
        (ROOT / "docs/verification/lab-station/v80-model-spec.json").read_text()
    )
    contract = json.loads((ROOT / "scripts/verify/contracts/design_pipeline_v80.json").read_text())
    assert contract["spec"] == shared
    assert "models/lab-station" in (ROOT / "CLAUDE.md").read_text()


def test_selected_delivery_is_complete_checksummed_and_admitted():
    shared = json.loads((ROOT / "models/lab-station/model-spec.json").read_text())
    folder = ROOT / shared["source"]["root_dir"]
    manifest = json.loads((folder / "SHA256.json").read_text())
    assert len(list(folder.glob(shared["source"]["stl_glob"]))) == 69
    for name, expected in manifest.items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == expected, name
    cfg = load_tools_config()
    assert (
        folder / shared["source"]["project_3mf"]
    ).stat().st_size <= cfg.import_limits.max_3mf_bytes
