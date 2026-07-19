"""Streamable HTTP MCP assembly and perimeter contract tests."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api.main import create_app
from api.runtime import AppRuntime
from src.core.domain.command import Command
from src.core.ports.blender_port import BlenderPort
from src.core.ports.mcp_port import ToolResult
from src.core.use_cases.scene_operations import SceneOperationsService

_IDENTITY = {"x-mes-identity": "tester@example.com"}
_MCP_HEADERS = {"accept": "application/json, text/event-stream"}
_INITIALIZE_REQUEST = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": {},
        "clientInfo": {"name": "contract-test", "version": "1"},
    },
}
_EXPECTED_TOOLS = {
    "apply_material",
    "blender_status",
    "create_object",
    "delete_object",
    "get_object_info",
    "get_scene_info",
    "get_viewport_screenshot",
    "modify_object",
}


class CountingBlender(BlenderPort):
    """Blender fake that proves the shared transport owns one connection."""

    def __init__(self) -> None:
        self.connect_calls = 0
        self.disconnect_calls = 0

    async def connect(self) -> None:
        self.connect_calls += 1

    async def disconnect(self) -> None:
        self.disconnect_calls += 1

    async def is_connected(self) -> bool:
        return True

    async def get_scene_info(self) -> dict[str, object]:
        return {
            "name": "Scene",
            "object_count": 0,
            "materials_count": 0,
            "objects": [],
        }

    async def execute(self, command: Command) -> ToolResult:
        return ToolResult(success=True, output="ok")

    async def call_tool(self, tool_name: str, arguments: dict[str, object]) -> ToolResult:
        return ToolResult(success=False, output=None, error="unused by assembly tests")


def make_fake_runtime() -> AppRuntime:
    """Use a real application service and replace only unrelated outer ports."""
    blender = CountingBlender()
    marker = MagicMock()
    return AppRuntime(
        blender=blender,
        scene_operations=SceneOperationsService(blender),
        scene_export=marker,
        event_bus=marker,
        adapter_factory=marker,
        sandbox=marker,
        sanitizer=marker,
        vision=None,
        prompt_builder=marker,
        session_store=marker,
        snapshot_store=marker,
        polyhaven=marker,
        text3d=None,
    )


def _client(runtime: AppRuntime, *, require_identity: bool = False) -> TestClient:
    app = create_app(
        runtime=runtime,
        require_identity=require_identity,
        cors_origins=["https://bearmacminimac-mini.tail56c751.ts.net"],
    )
    return TestClient(app, base_url="http://localhost")


def _json_rpc_payload(response) -> dict[str, object]:
    for line in response.text.splitlines():
        if line.startswith("data: "):
            payload = json.loads(line.removeprefix("data: "))
            assert isinstance(payload, dict)
            return payload
    payload = response.json()
    assert isinstance(payload, dict)
    return payload


def test_rest_and_mcp_share_one_blender_connection() -> None:
    runtime = make_fake_runtime()

    with _client(runtime) as client:
        assert client.get("/api/health").json() == {
            "status": "ok",
            "blender": "connected",
        }
        response = client.post(
            "/mcp",
            headers=_MCP_HEADERS,
            json=_INITIALIZE_REQUEST,
        )
        assert response.status_code == 200

    blender = runtime.blender
    assert isinstance(blender, CountingBlender)
    assert blender.connect_calls == 1
    assert blender.disconnect_calls == 1


def test_mcp_endpoint_without_trailing_slash_does_not_redirect() -> None:
    """Proxy clients must not be redirected to an internal localhost authority."""
    app = create_app(
        runtime=make_fake_runtime(),
        require_identity=False,
        cors_origins=["https://bearmacminimac-mini.tail56c751.ts.net"],
    )

    with TestClient(app, base_url="http://localhost", follow_redirects=False) as client:
        response = client.post("/mcp", headers=_MCP_HEADERS, json=_INITIALIZE_REQUEST)

    assert response.status_code == 200
    assert "location" not in response.headers


def test_mcp_requires_tailnet_identity() -> None:
    with _client(make_fake_runtime(), require_identity=True) as client:
        assert client.post("/mcp", json=_INITIALIZE_REQUEST).status_code == 401
        response = client.post(
            "/mcp",
            headers=_MCP_HEADERS | _IDENTITY,
            json=_INITIALIZE_REQUEST,
        )
        assert response.status_code == 200


def test_mcp_rejects_untrusted_origin() -> None:
    with _client(make_fake_runtime()) as client:
        response = client.post(
            "/mcp",
            headers=_MCP_HEADERS | {"origin": "https://evil.example"},
            json=_INITIALIZE_REQUEST,
        )

    assert response.status_code == 403


def test_mcp_rejects_unsupported_protocol_version() -> None:
    request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    with _client(make_fake_runtime()) as client:
        response = client.post(
            "/mcp",
            headers=_MCP_HEADERS | {"mcp-protocol-version": "1900-01-01"},
            json=request,
        )

    assert response.status_code == 400


def test_client_name_does_not_change_capabilities_or_catalog() -> None:
    observations: list[tuple[object, set[str]]] = []
    client_names = ("codex", "claude-code", "cursor", "Visual Studio Code", "unknown-host")

    for client_name in client_names:
        initialize = {
            **_INITIALIZE_REQUEST,
            "params": {
                **_INITIALIZE_REQUEST["params"],
                "clientInfo": {"name": client_name, "version": "1"},
            },
        }
        tools_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        with _client(make_fake_runtime()) as client:
            initialize_response = client.post("/mcp", headers=_MCP_HEADERS, json=initialize)
            tools_response = client.post(
                "/mcp",
                headers=_MCP_HEADERS | {"mcp-protocol-version": "2025-11-25"},
                json=tools_request,
            )

        assert initialize_response.status_code == 200
        assert tools_response.status_code == 200
        initialize_payload = _json_rpc_payload(initialize_response)
        tools_payload = _json_rpc_payload(tools_response)
        initialize_result = initialize_payload["result"]
        tools_result = tools_payload["result"]
        assert isinstance(initialize_result, dict)
        assert isinstance(tools_result, dict)
        tool_items = tools_result["tools"]
        assert isinstance(tool_items, list)
        names = {
            item["name"]
            for item in tool_items
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        observations.append((initialize_result["capabilities"], names))

    assert all(observation == observations[0] for observation in observations)
    assert observations[0][1] == _EXPECTED_TOOLS
