"""Fix round 1 at the MCP boundary: scrubbed errors, busy slicer, derived timeout, bad bytes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastmcp import Client

from src.adapters.mcp_server import design_tools
from src.adapters.slicing.bambu_studio_cli import BambuStudioCli
from src.core.domain.design_run import StageName
from src.core.domain.exceptions import DomainError
from src.core.domain.import_limits import ImportLimits
from src.infrastructure.tools_config import load_tools_config
from tests.unit.adapters.test_mcp_design_tools import _server, _strings, _text
from tests.unit.core.test_design_pipeline import _payload, _rig


async def test_slice_for_print_missing_binary_is_failed_result_without_path(tmp_path):
    rig = _rig(tmp_path)
    rig.pipeline._slicing = BambuStudioCli(tmp_path / "nope" / "BambuStudio", profiles_dir=tmp_path)
    async with Client(_server(rig)) as client:
        res = await client.call_tool("slice_for_print", {"input_3mf": "artifact/p.3mf"})
    data = res.structured_content
    assert data["passed"] is False and "not available" in data["message"]
    assert data["log_path"] is None and data["output_3mf"] is None
    texts = [*_strings(data), _text(res)]
    assert not [t for t in texts for f in (str(tmp_path), str(Path.home())) if f in t]


async def test_design_tool_errors_are_scrubbed(tmp_path):
    rig = _rig(tmp_path)

    async def boom(paths):
        raise DomainError(f"cannot read {tmp_path}/artifact/STL/a.stl for {Path.home()}/x")

    rig.pipeline._integrity.check = boom
    async with Client(_server(rig)) as client:
        res = await client.call_tool(
            "check_mesh_integrity", {"stl_paths": ["artifact/STL/a.stl"]}, raise_on_error=False
        )
    assert res.is_error and "cannot read" in _text(res)
    assert str(tmp_path) not in _text(res) and str(Path.home()) not in _text(res)


async def test_slice_for_print_returns_busy_when_lease_held(tmp_path):
    rig = _rig(tmp_path)
    async with Client(_server(rig)) as client:
        async with rig.lease.hold(StageName.MECHANISM):
            res = await client.call_tool("slice_for_print", {"input_3mf": "artifact/p.3mf"})
        later = await client.call_tool("slice_for_print", {"input_3mf": "artifact/p.3mf"})
    assert res.structured_content["passed"] is False
    assert res.structured_content["message"] == (
        "slicer busy: another print job is running; retry later"
    )
    assert len(rig.slicing.requests) == 1  # only the call after the lease was free
    assert later.structured_content["passed"] is True
    assert not rig.runs.exists() or list(rig.runs.iterdir()) == []  # busy call: no run dir


def test_integrity_timeout_derives_from_caps_and_measurement():
    limits = load_tools_config().import_limits
    expected = (
        design_tools.SAFETY_FACTOR
        * design_tools.V78_CHECK_S
        * (limits.max_stl_files * limits.max_stl_bytes)
        / design_tools.V78_STL_TOTAL_BYTES
    )
    assert design_tools.integrity_timeout_s(limits) == pytest.approx(expected)
    assert design_tools.integrity_timeout_s(ImportLimits(1, 1, 1)) < expected


async def test_integrity_tool_timeout_uses_the_servers_limits(tmp_path):
    rig = _rig(tmp_path)
    mcp = _server(rig)
    tool = await mcp.get_tool("check_mesh_integrity")
    assert tool.timeout == pytest.approx(design_tools.integrity_timeout_s(rig.pipeline.limits))


async def test_run_resource_tolerates_undecodable_text(tmp_path):
    rig = _rig(tmp_path)
    job = await rig.pipeline.submit(_payload(rig))
    await rig.pipeline.wait_idle()
    (rig.runs / job.run_id / "bad.log").write_bytes(b"ok \xff\xfe tail")
    async with Client(_server(rig)) as client:
        body = await client.read_resource(f"run://{job.run_id}/bad.log")
    assert "ok" in body[0].text and "tail" in body[0].text
    assert json.loads((rig.runs / job.run_id / "report.json").read_text())["run_id"] == job.run_id
