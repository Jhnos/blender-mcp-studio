"""describe_model_spec and list_artifacts let an LLM build a spec without reading source."""

from __future__ import annotations

import json
from pathlib import Path

from fastmcp import Client

from src.core.domain.model_spec import parse_model_spec
from tests.unit.adapters.test_mcp_design_tools import _server
from tests.unit.core.test_design_pipeline import _rig


def _data(result):
    data = result.structured_content
    return data["result"] if set(data) == {"result"} else data


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


async def test_describe_model_spec_example_parses(tmp_path):
    rig = _rig(tmp_path)
    async with Client(_server(rig)) as client:
        described = _data(await client.call_tool("describe_model_spec", {}))
    assert described["spec_version"] == "1"
    schema = described["schema"]
    assert schema["required"] == ["spec_version", "name", "source"]
    target = schema["properties"]["print_target"]["properties"]
    assert target["printer"]["enum"] == ["bambu-p2s"] and target["material"]["enum"] == ["PLA"]
    assert target["layer_height_mm"]["default"] == 0.2
    assert schema["properties"]["source"]["properties"]["stl_glob"]["default"] == "STL/*.stl"
    assert schema["properties"]["mechanism"]["properties"]["suites"]["maxItems"] == 0
    assert "Phase 1" in schema["properties"]["mechanism"]["description"]
    example = described["example"]
    source = example["source"]
    root = tmp_path / "layout"
    stl_dir = root / source["root_dir"] / Path(source["stl_glob"]).parent
    stl_dir.mkdir(parents=True)
    (stl_dir / "part.stl").write_bytes(b"x")
    (root / source["root_dir"] / source["project_3mf"]).write_bytes(b"3mf")
    spec = parse_model_spec(example, artifact_roots=(root,))
    assert spec.name == example["name"] and spec.mechanism.suites == ()


async def test_list_artifacts_relative_and_capped(tmp_path):
    rig = _rig(tmp_path)  # artifact root is tmp_path; rig.root = tmp_path/artifact (STL/ + p.3mf)
    deep = tmp_path / "deliv" / "STL" / "print"
    deep.mkdir(parents=True)
    for i in range(3):
        (deep / f"p{i}.stl").write_bytes(b"x")
    (tmp_path / "deliv" / "plate.3mf").write_bytes(b"3mf")
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".hidden" / "x.3mf").write_bytes(b"3mf")
    (tmp_path / "a" / "b" / "c").mkdir(parents=True)
    (tmp_path / "a" / "b" / "c" / "too-deep.3mf").write_bytes(b"3mf")
    for i in range(250):
        many = tmp_path / "many" / f"d{i:03d}"
        many.mkdir(parents=True)
        (many / "x.stl").write_bytes(b"x")
    async with Client(_server(rig)) as client:
        listed = _data(await client.call_tool("list_artifacts", {}))
    rows = {row["root_dir"]: row for row in listed["artifacts"]}
    assert len(listed["artifacts"]) == 200 and listed["truncated"] is True
    assert rows["artifact"]["stl_dirs"] == {"STL": 2}
    assert rows["artifact"]["project_3mf"] == ["p.3mf"]
    assert rows["deliv"]["stl_dirs"] == {"STL/print": 3}
    assert rows["deliv"]["project_3mf"] == ["plate.3mf"]
    assert not any(k.startswith(".hidden") or k.startswith("a/b/c") for k in rows)
    for text in _strings(listed):
        assert not text.startswith("/") and str(tmp_path) not in text


async def test_list_artifacts_is_empty_without_candidates(tmp_path):
    rig = _rig(tmp_path)
    for f in (*(rig.root / "STL").iterdir(), rig.root / "p.3mf"):
        f.unlink()
    async with Client(_server(rig)) as client:
        listed = _data(await client.call_tool("list_artifacts", {}))
    assert listed["artifacts"] == [] and listed["truncated"] is False
    assert listed["default_available"] is False


async def test_run_design_pipeline_description_names_the_helpers(tmp_path):
    rig = _rig(tmp_path)
    async with Client(_server(rig)) as client:
        tools = {t.name: t for t in await client.list_tools()}
    description = tools["run_design_pipeline"].description
    for word in ("describe_model_spec", "list_artifacts", "spec_version", "name", "root_dir"):
        assert word in description, word
    for name in ("describe_model_spec", "list_artifacts"):
        assert tools[name].annotations.readOnlyHint is True
    json.dumps(tools["describe_model_spec"].outputSchema)
