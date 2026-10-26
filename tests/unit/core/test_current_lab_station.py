"""One selected delivery for Claude Code, discovery, schema examples and the real gate."""

import copy
import hashlib
import json
from pathlib import Path

from src.core.use_cases.artifact_catalog import list_artifacts
from src.infrastructure.config_loader import load_selected_model_spec
from src.infrastructure.tools_config import load_tools_config

ROOT = Path(__file__).resolve().parents[3]


def test_shared_entry_selects_v80_and_rejects_missing_default(tmp_path):
    old = tmp_path / "old-v78"
    old.mkdir()
    (old / "old.3mf").write_bytes(b"old")
    result = list_artifacts(
        (tmp_path,), max_stl_files=100, selected_spec=load_selected_model_spec()
    )
    assert result["default_spec"]["name"] == "lab-station-v80"
    assert result["default_available"] is False  # Never infer 'latest' from directory order.
    spec = copy.deepcopy(result["default_spec"])
    selected = tmp_path / spec["source"]["root_dir"]
    (selected / "STL/列印零件").mkdir(parents=True)
    (selected / "STL/列印零件/a.stl").write_bytes(b"fixture")
    (selected / spec["source"]["project_3mf"]).write_bytes(b"fixture")
    result = list_artifacts(
        (tmp_path,), max_stl_files=100, selected_spec=load_selected_model_spec()
    )
    assert result["default_available"] is True
    assert result["artifacts"][0]["root_dir"] == spec["source"]["root_dir"]
    assert any(r["root_dir"] == "old-v78" for r in result["artifacts"])


def test_current_contract_has_no_live_spec_copy():
    contract = json.loads(
        (ROOT / "scripts/verify/contracts/design_pipeline_current.json").read_text()
    )
    assert contract["selection"] == "current" and "spec" not in contract
    schema_source = (ROOT / "src/core/domain/model_spec_schema.py").read_text()
    assert "lab-station-v" not in schema_source
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


def test_declaration_reload_and_missing_file_fail_closed(tmp_path):
    import pytest

    from src.core.domain.model_spec import ModelSpecError
    from src.infrastructure.config_loader import load_selected_model_spec

    path = tmp_path / "models/lab-station/model-spec.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"name": "first"}))
    assert load_selected_model_spec(tmp_path)["name"] == "first"
    path.write_text(json.dumps({"name": "second"}))
    assert load_selected_model_spec(tmp_path)["name"] == "second"
    path.unlink()
    with pytest.raises(ModelSpecError, match="selected"):
        load_selected_model_spec(tmp_path)


async def test_mcp_default_changes_with_the_injected_declaration(tmp_path):
    from fastmcp import Client

    from tests.unit.adapters.test_mcp_design_tools import _server
    from tests.unit.core.test_design_pipeline import _rig

    selected = {
        "spec_version": "1",
        "name": "first",
        "source": {"root_dir": "artifact", "stl_glob": "STL/*.stl", "project_3mf": "p.3mf"},
    }
    rig = _rig(tmp_path, selected_spec=lambda: selected)
    async with Client(_server(rig)) as client:
        for name in ("first", "second"):
            selected["name"] = name
            discovery = (await client.call_tool("list_artifacts", {})).structured_content
            example = (await client.call_tool("describe_model_spec", {})).structured_content
            assert discovery["default_spec"] == example["example"] == selected
            submitted = (await client.call_tool("run_design_pipeline", {})).structured_content
            await rig.pipeline.wait_idle()
            report = await rig.pipeline.report(submitted["run_id"])
            assert report.spec_name == name and report.passed


async def test_missing_selection_creates_no_job(tmp_path):
    import pytest

    from src.core.domain.model_spec import ModelSpecError
    from tests.unit.core.test_design_pipeline import _rig

    def missing():
        raise ModelSpecError("selected declaration missing")

    rig = _rig(tmp_path, selected_spec=missing)
    with pytest.raises(ModelSpecError, match="selected"):
        await rig.pipeline.submit()
    assert not rig.jobs.records


def test_selection_does_not_depend_on_scan_depth_or_directory_order(tmp_path):
    from src.core.use_cases.artifact_catalog import ArtifactCatalog

    root = tmp_path / "releases/nested/current"
    (root / "STL").mkdir(parents=True)
    (root / "project").mkdir()
    (root / "STL/a.stl").write_bytes(b"mesh")
    (root / "project/p.3mf").write_bytes(b"project")
    spec = {
        "spec_version": "1",
        "name": "current",
        "source": {
            "root_dir": "releases/nested/current",
            "stl_glob": "STL/*.stl",
            "project_3mf": "project/p.3mf",
        },
    }
    catalog = ArtifactCatalog((tmp_path,), 100, lambda: spec)
    result = catalog.list()
    assert result["default_available"] is True
    assert result["artifacts"][0]["root_dir"] == spec["source"]["root_dir"]
    spec["source"]["stl_glob"] = "not-the-selected-stls/*.stl"
    assert catalog.list()["default_available"] is False


async def test_explicit_historical_spec_does_not_depend_on_current_declaration(tmp_path):
    from src.core.domain.model_spec import ModelSpecError
    from tests.unit.core.test_design_pipeline import _payload, _rig

    def unavailable():
        raise ModelSpecError("selected declaration missing")

    rig = _rig(tmp_path, selected_spec=unavailable)
    payload = _payload(rig)
    payload["name"] = "deliberate-historical-model"
    job = await rig.pipeline.submit(payload)
    await rig.pipeline.wait_idle()
    report = await rig.pipeline.report(job.run_id)
    assert report.passed and report.spec_name == payload["name"]


def test_malformed_declaration_is_not_replaced_with_an_example(tmp_path):
    import pytest

    from src.core.domain.model_spec import ModelSpecError

    path = tmp_path / "models/lab-station/model-spec.json"
    path.parent.mkdir(parents=True)
    for body in ("not-json", "[]", "null"):
        path.write_text(body)
        with pytest.raises(ModelSpecError, match="selected"):
            load_selected_model_spec(tmp_path)


def test_selection_honors_model_spec_defaults_without_copying_them(tmp_path):
    from src.core.use_cases.artifact_catalog import ArtifactCatalog
    from tests.unit.core.test_design_pipeline import _rig

    _rig(tmp_path)
    spec = {
        "spec_version": "1",
        "name": "minimal-current",
        "source": {"root_dir": "artifact", "project_3mf": "p.3mf"},
    }
    result = ArtifactCatalog((tmp_path,), 100, lambda: spec).list()
    assert result["default_available"] is True
    assert result["default_spec"] == spec


async def test_promotion_changes_actual_inputs_not_only_the_display_name(tmp_path):
    from fastmcp import Client

    from tests.unit.adapters.test_mcp_design_tools import _server
    from tests.unit.core.test_design_pipeline import _rig

    promoted = tmp_path / "promoted"
    (promoted / "STL").mkdir(parents=True)
    mesh, project = b"promoted mesh", b"promoted project"
    (promoted / "STL/new.stl").write_bytes(mesh)
    (promoted / "new.3mf").write_bytes(project)
    selected = {
        "spec_version": "1",
        "name": "current",
        "source": {"root_dir": "artifact", "stl_glob": "STL/*.stl", "project_3mf": "p.3mf"},
    }
    rig = _rig(tmp_path, selected_spec=lambda: selected)
    async with Client(_server(rig)) as client:
        for directory, filename, count in (("artifact", "p.3mf", 2), ("promoted", "new.3mf", 1)):
            selected["source"].update(root_dir=directory, project_3mf=filename)
            job = (await client.call_tool("run_design_pipeline", {})).structured_content
            await rig.pipeline.wait_idle()
            run_dir = rig.runs / job["run_id"]
            report = await rig.pipeline.report(job["run_id"])
            assert report.passed
            assert json.loads((run_dir / "spec.json").read_text()) == selected
            evidence = json.loads((run_dir / "import.json").read_text())
            assert len(evidence["stls"]) == count
        assert evidence["stls"][0]["sha256"] == hashlib.sha256(mesh).hexdigest()
        assert evidence["project_3mf"]["sha256"] == hashlib.sha256(project).hexdigest()


def test_current_stls_are_valid_without_repair_and_collapsed_face_is_rejected():
    import struct

    import pytest

    from src.verification.artifact_files import binary_stl_surface
    from src.verification.mesh_integrity import require_triangle_surface

    spec = load_selected_model_spec()
    folder = ROOT / spec["source"]["root_dir"]
    files = sorted(folder.glob(spec["source"]["stl_glob"]))
    assert files
    for path in files:
        require_triangle_surface(binary_stl_surface(path.read_bytes()))
    corrupted = bytearray(files[0].read_bytes())
    first = struct.unpack_from("<3f", corrupted, 84 + 12)
    struct.pack_into("<3f", corrupted, 84 + 24, *first)
    with pytest.raises(ValueError, match="Zero-area triangle"):
        require_triangle_surface(binary_stl_surface(corrupted))
