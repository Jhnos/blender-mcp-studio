"""Real composition supplies native provenance; shared Blender stays unused."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from api.runtime import build_runtime
from src.core.domain.command import Command
from src.core.domain.exceptions import BlenderBusyError
from src.core.domain.import_limits import ImportLimits
from src.infrastructure.tools_config import ToolsConfig
from tests.e2e.test_mcp_streamable_http import CountingBlender
from tests.unit.adapters.test_native_source import fixture


async def test_production_composition_checks_the_selected_native_without_blender(
    tmp_path, monkeypatch
):
    root, manifest, spec, reader = fixture(tmp_path)
    tools = ToolsConfig(
        Path("unused-slicer"),
        tmp_path / "runs",
        (tmp_path,),
        ImportLimits(10, 1000, 1000, 2000),
        tmp_path / "jobs.db",
    )
    payload = {
        "spec_version": "1",
        "name": "selected",
        "source": {
            "root_dir": "models/selected",
            "stl_glob": "STL/列印零件/*.stl",
            "project_3mf": "plate.3mf",
        },
    }
    monkeypatch.setattr("src.infrastructure.env_loader.load_env", lambda _: None)
    monkeypatch.setattr("src.infrastructure.tools_config.load_tools_config", lambda: tools)
    monkeypatch.setattr(
        "src.infrastructure.config_loader.load_selected_model_spec", lambda: payload
    )
    blender = CountingBlender()
    blender.execute = AsyncMock(side_effect=AssertionError("unexpected Blender execution"))
    blender.call_tool = AsyncMock(side_effect=AssertionError("unexpected Blender tool"))
    monkeypatch.setattr("src.adapters.mcp.factory.build_blender_adapter", lambda **_: blender)
    runtime = build_runtime()
    reply = await runtime.design_pipeline.list_artifacts()
    assert reply["default_native"]["available"] is True
    assert reply["default_native"]["verified_files"] == 5
    assert reply["default_native"]["native"]["sha256"] == manifest["native.blend"]
    assert runtime.native_revisions._artifacts is runtime.design_pipeline._artifacts
    assert runtime.design_pipeline._stages.native is runtime.native_revisions
    assert (
        runtime.design_pipeline._stages.products._stls._integrity
        is runtime.design_pipeline._stages.integrity
    )
    prepared = await runtime.native_revisions.prepare_source("c" * 32)
    assert prepared.source.native.sha256 == manifest["native.blend"]
    assert (
        tools.design_runs_dir / prepared.directory / "native.blend"
    ).read_bytes() == b"opaque-native"
    (root / "native.blend").write_bytes(b"changed")
    reply = await runtime.design_pipeline.list_artifacts()
    assert reply["default_native"]["available"] is False
    assert runtime.design_pipeline.lease.holder is None
    assert blender.connect_calls == 0 and blender.disconnect_calls == 0
    blender.execute.assert_not_awaited()
    blender.call_tool.assert_not_awaited()

    async def foreign_mutation():
        with pytest.raises(BlenderBusyError):
            await runtime.blender.execute(
                Command(tool_name="delete_object", arguments={"name": "Cube"})
            )
        with pytest.raises(BlenderBusyError):
            await runtime.blender.call_tool("execute_code", {"code": "pass"})

    async with runtime.design_pipeline.lease.hold("native-revision"):
        await asyncio.create_task(foreign_mutation())
    blender.execute.assert_not_awaited()
    blender.call_tool.assert_not_awaited()
