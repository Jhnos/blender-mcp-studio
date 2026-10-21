"""The eight design tools and the run:// resource over a real DesignPipeline with fake ports."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastmcp import Client, FastMCP
from mcp.shared.exceptions import McpError

from src.adapters.generation.authorized_code import GENERATOR_TIMEOUT_S
from src.adapters.mcp_server import create_mcp_server, design_tools
from src.adapters.slicing.bambu_studio_cli import SLICE_TIMEOUT_S
from src.core.domain.exceptions import UnknownInstanceError
from src.core.domain.mechanical_generation import BuiltPart, InstanceBuild, InstanceSummary
from tests.unit.core.test_design_pipeline import _payload, _rig


class FakeCatalog:
    async def list_instances(self):
        return (InstanceSummary("hand-a", "hand", ("a.stl",), "models/hand-a"),)

    async def build(self, slug):
        if slug != "hand-a":
            raise UnknownInstanceError(f"{slug!r} is not a registered instance")
        return InstanceBuild(slug, "models/hand-a", (BuiltPart("a.stl", 12, (1.0, 2.0, 3.0)),))


def _server(rig=None, *, catalog=True) -> FastMCP:
    return create_mcp_server(
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        design=None if rig is None else rig.pipeline,
        generation=FakeCatalog() if catalog else None,
    )


def _text(result) -> str:
    return " ".join(getattr(block, "text", "") for block in result.content)


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _strings(k)
            yield from _strings(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _strings(v)


async def _submit(client, rig):
    res = await client.call_tool("run_design_pipeline", {"spec": _payload(rig)})
    await rig.pipeline.wait_idle()
    return res.structured_content


async def test_unconfigured_tools_stay_in_the_catalog_and_say_so():
    calls = {
        "run_design_pipeline": {"spec": {}},
        "get_job_status": {"job_id": "j"},
        "get_run_report": {"run_id": "r"},
        "check_mesh_integrity": {"stl_paths": ["a.stl"]},
        "slice_for_print": {"input_3mf": "a.3mf"},
        "list_instances": {},
        "build_instance": {"slug": "x"},
        "tool_status": {},
    }
    async with Client(_server(None, catalog=False)) as client:
        assert {t.name for t in await client.list_tools()} >= set(calls)
        for name, args in calls.items():
            res = await client.call_tool(name, args, raise_on_error=False)
            assert res.is_error, name
            assert "not configured on this server" in _text(res), name


async def test_submit_poll_and_report_round_trip(tmp_path):
    rig = _rig(tmp_path)
    async with Client(_server(rig)) as client:
        job = await _submit(client, rig)
        assert job["status"] == "queued" and len(job["run_id"]) == 32
        polled = await client.call_tool("get_job_status", {"job_id": job["job_id"]})
        assert polled.structured_content["status"] == "done"
        report = await client.call_tool("get_run_report", {"run_id": job["run_id"]})
        assert report.structured_content["spec_name"] == "demo"
        assert report.structured_content["stages"][0]["name"] == "import"


async def test_get_run_report_includes_passed(tmp_path):
    rig = _rig(tmp_path)
    async with Client(_server(rig)) as client:
        job = await _submit(client, rig)
        report = await client.call_tool("get_run_report", {"run_id": job["run_id"]})
    assert report.structured_content["passed"] is True


async def test_unknown_job_and_report_are_tool_errors(tmp_path):
    rig = _rig(tmp_path)
    async with Client(_server(rig)) as client:
        job = await client.call_tool("get_job_status", {"job_id": "nope"}, raise_on_error=False)
        report = await client.call_tool(
            "get_run_report", {"run_id": "0" * 32}, raise_on_error=False
        )
    assert job.is_error and "unknown job" in _text(job)
    assert report.is_error and "no report" in _text(report)


async def test_invalid_spec_is_a_tool_error_without_a_job(tmp_path):
    rig = _rig(tmp_path)
    bad = _payload(rig)
    bad["source"]["root_dir"] = "/etc"
    async with Client(_server(rig)) as client:
        res = await client.call_tool("run_design_pipeline", {"spec": bad}, raise_on_error=False)
    assert res.is_error and "outside" in _text(res)
    assert rig.jobs.records == {}


async def test_check_mesh_integrity_rejects_escape_and_hidden(tmp_path):
    rig = _rig(tmp_path)
    (rig.root / ".hid").mkdir()
    (rig.root / ".hid" / "h.stl").write_bytes(b"x")
    async with Client(_server(rig)) as client:
        for bad in ("../x.stl", "/etc/hosts.stl", "artifact/.hid/h.stl", "artifact/p.3mf"):
            res = await client.call_tool(
                "check_mesh_integrity", {"stl_paths": [bad]}, raise_on_error=False
            )
            assert res.is_error, bad
            assert str(tmp_path) not in _text(res)
    assert rig.integrity.seen == ()


async def test_check_mesh_integrity_respects_count_cap(tmp_path):
    rig = _rig(tmp_path)
    rig.pipeline._limits = replace(rig.pipeline._limits, max_stl_files=1)
    async with Client(_server(rig)) as client:
        res = await client.call_tool(
            "check_mesh_integrity",
            {"stl_paths": ["artifact/STL/a.stl", "artifact/STL/b.stl"]},
            raise_on_error=False,
        )
    assert res.is_error and "1" in _text(res)
    assert rig.integrity.seen == ()


async def test_check_mesh_integrity_returns_relative_verdicts(tmp_path):
    rig = _rig(tmp_path)
    async with Client(_server(rig)) as client:
        res = await client.call_tool("check_mesh_integrity", {"stl_paths": ["artifact/STL/a.stl"]})
    data = res.structured_content
    assert data["verdicts"][0]["path"] == "artifact/STL/a.stl"
    assert data["verdicts"][0]["watertight"] is True and data["passed"] is True


async def test_slice_for_print_rejects_non_3mf(tmp_path):
    rig = _rig(tmp_path)
    async with Client(_server(rig)) as client:
        res = await client.call_tool(
            "slice_for_print", {"input_3mf": "artifact/STL/a.stl"}, raise_on_error=False
        )
    assert res.is_error and "3mf" in _text(res)
    assert rig.slicing.requests == []


async def test_slice_for_print_returns_run_uris(tmp_path):
    rig = _rig(tmp_path)
    async with Client(_server(rig)) as client:
        res = await client.call_tool("slice_for_print", {"input_3mf": "artifact/p.3mf"})
    data = res.structured_content
    run_id = Path(rig.slicing.requests[0].output_dir).parent.name
    assert data["output_3mf"] == f"run://{run_id}/print/out.3mf"
    assert data["log_path"] == f"run://{run_id}/print/log.txt"
    assert data["settings_json"] is None and data["passed"] is True


async def test_list_build_instances_and_tool_status(tmp_path):
    rig = _rig(tmp_path)
    async with Client(_server(rig)) as client:
        listed = (await client.call_tool("list_instances", {})).structured_content["result"]
        built = (await client.call_tool("build_instance", {"slug": "hand-a"})).structured_content
        status = (await client.call_tool("tool_status", {})).structured_content["result"]
        missing = await client.call_tool("build_instance", {"slug": "zzz"}, raise_on_error=False)
    assert listed[0]["slug"] == "hand-a" and built["parts"][0]["name"] == "a.stl"
    assert status[0]["name"] == "Bambu Studio" and status[0]["available"] is True
    assert "path" not in status[0]
    assert missing.is_error and "not a registered instance" in _text(missing)


async def test_mcp_outputs_have_no_absolute_paths(tmp_path):
    rig = _rig(tmp_path)
    forbidden = (str(tmp_path), str(Path.home()))
    async with Client(_server(rig)) as client:
        job = await _submit(client, rig)
        results = [
            job,
            (await client.call_tool("get_job_status", {"job_id": job["job_id"]})),
            (await client.call_tool("get_run_report", {"run_id": job["run_id"]})),
            (await client.call_tool("check_mesh_integrity", {"stl_paths": ["artifact/STL/a.stl"]})),
            (await client.call_tool("slice_for_print", {"input_3mf": "artifact/p.3mf"})),
            (await client.call_tool("list_instances", {})),
            (await client.call_tool("build_instance", {"slug": "hand-a"})),
            (await client.call_tool("tool_status", {})),
        ]
    scanned = 0
    for res in results:
        payload = res if isinstance(res, dict) else res.structured_content
        texts = list(_strings(payload)) + ([] if isinstance(res, dict) else [_text(res)])
        scanned += len(texts)
        assert not [t for t in texts for f in forbidden if f in t]
    assert scanned > 40


async def test_run_resource_reads_files_and_rejects_traversal(tmp_path):
    rig = _rig(tmp_path)
    async with Client(_server(rig)) as client:
        job = await _submit(client, rig)
        run_id = job["run_id"]
        body = await client.read_resource(f"run://{run_id}/report.json")
        assert json.loads(body[0].text)["run_id"] == run_id
        (rig.runs / run_id / "print").mkdir(exist_ok=True)
        (rig.runs / run_id / "print" / "out.3mf").write_bytes(b"\x00\x01zip")
        blob = await client.read_resource(f"run://{run_id}/print/out.3mf")
        assert blob[0].blob  # bytes for non-text suffixes
        (rig.runs / "secret.json").write_text('{"secret": true}')
        for evil in ("../secret.json", "..%2Fsecret.json", "print/../../secret.json"):
            with pytest.raises(McpError) as err:
                await client.read_resource(f"run://{run_id}/{evil}")
            assert '"secret": true' not in str(err.value)
        with pytest.raises(McpError):
            await client.read_resource("run://not-a-run-id/report.json")


async def test_run_resource_rejects_traversal(tmp_path):
    rig = _rig(tmp_path)
    run_dir = rig.runs / ("0" * 32)
    run_dir.mkdir(parents=True)
    (rig.runs / "secret.json").write_text('{"secret": true}')
    (run_dir / "link.json").symlink_to(rig.runs / "secret.json")
    for name in ("../secret.json", "../../etc/hosts", "link.json", "/etc/hosts"):
        with pytest.raises(ValueError, match="outside the run directory"):
            design_tools.read_run_resource(rig.pipeline, "0" * 32, name)
    with pytest.raises(ValueError, match="32 lowercase hex"):
        design_tools.read_run_resource(rig.pipeline, "../" + "0" * 29, "x.json")


async def test_run_resource_template_is_listed(tmp_path):
    rig = _rig(tmp_path)
    async with Client(_server(rig)) as client:
        templates = await client.list_resource_templates()
    assert any(t.uriTemplate.startswith("run://{run_id}/") for t in templates)


async def test_tool_timeouts_derive_from_existing_constants(tmp_path):
    rig = _rig(tmp_path)
    mcp = _server(rig)
    assert (await mcp.get_tool("slice_for_print")).timeout == SLICE_TIMEOUT_S + 30
    assert (await mcp.get_tool("build_instance")).timeout == GENERATOR_TIMEOUT_S + 30
    assert (await mcp.get_tool("check_mesh_integrity")).timeout == (
        design_tools.integrity_timeout_s(rig.pipeline.limits)
    )
    assert (await mcp.get_tool("run_design_pipeline")).timeout == 30
