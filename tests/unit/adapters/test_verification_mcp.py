"""MCP returns the shared suite catalog and measured per-case results."""

from unittest.mock import AsyncMock

import pytest
from fastmcp import Client

from src.adapters.mcp_server import create_mcp_server
from src.core.domain.verification import CheckResult, VerificationError, VerificationReport
from src.verification.cable_route_cases import registered_suites


@pytest.mark.asyncio
async def test_verification_tools_return_structured_catalog_and_failure_evidence() -> None:
    service = AsyncMock()
    service.list_suites.return_value = registered_suites()
    service.run.return_value = VerificationReport(
        "cable-contact-controls",
        False,
        (CheckResult("clear_path", "clear", "contact", False, "Unexpected contact"),),
        "Synthetic controls only",
        True,
    )
    async with Client(create_mcp_server(AsyncMock(), AsyncMock(), AsyncMock(), service)) as client:
        catalog = await client.call_tool("list_verification_suites", {})
        assert catalog.structured_content is not None
        result = await client.call_tool(
            "run_verification_suite", {"suite_id": "cable-contact-controls"}
        )
        assert result.structured_content["passed"] is False
        assert result.structured_content["checks"][0]["name"] == "clear_path"
        service.run.assert_awaited_once_with("cable-contact-controls")


@pytest.mark.asyncio
async def test_unknown_suite_and_extra_code_are_not_executable() -> None:
    service = AsyncMock()
    service.run.side_effect = VerificationError("Unknown verification suite")
    async with Client(create_mcp_server(AsyncMock(), AsyncMock(), AsyncMock(), service)) as client:
        result = await client.call_tool(
            "run_verification_suite", {"suite_id": "unknown"}, raise_on_error=False
        )
        assert result.is_error
        service.run.reset_mock()
        result = await client.call_tool(
            "run_verification_suite",
            {"suite_id": "cable-contact-controls", "code": "print(1)"},
            raise_on_error=False,
        )
        assert result.is_error
        service.run.assert_not_called()


def test_independent_scene_oracle_observes_topology_changes_with_identical_vertices(
    monkeypatch, capsys
):
    import json
    import sys
    from types import SimpleNamespace

    from scripts.verify.verification_mcp_verify_real import SNAPSHOT

    mesh = SimpleNamespace(
        name="mesh",
        vertices=[
            SimpleNamespace(co=(0, 0, 0)),
            SimpleNamespace(co=(1, 0, 0)),
            SimpleNamespace(co=(0, 1, 0)),
        ],
        edges=[SimpleNamespace(vertices=(0, 1))],
        polygons=[SimpleNamespace(vertices=(0, 1, 2))],
    )
    bpy = SimpleNamespace(
        data=SimpleNamespace(objects=[], meshes=[mesh], filepath=""),
        context=SimpleNamespace(
            view_layer=SimpleNamespace(objects=SimpleNamespace(active=None)),
            scene=SimpleNamespace(render=SimpleNamespace(filepath="render.png")),
        ),
    )
    monkeypatch.setitem(sys.modules, "bpy", bpy)

    def read():
        exec(SNAPSHOT, {})
        return json.loads(capsys.readouterr().out.split("SCENE_STATE_JSON:", 1)[1])

    before = read()
    mesh.polygons[0].vertices = (0, 2, 1)
    assert read() != before
