"""Fail-closed drift guards for the architecture HTML single source of truth."""

from __future__ import annotations

import ast
import json
from html.parser import HTMLParser
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
ARTIFACT = PROJECT_ROOT / "docs" / "architecture.html"

CODE_ANCHORS = {
    "fastapi": ("api/main.py", "function", "create_app"),
    "stdio_proxy": ("scripts/run_mcp_stdio_proxy.py", "function", "main"),
    "mcp_adapter": ("src/adapters/mcp_server/server.py", "function", "create_mcp_server"),
    "app_runtime": ("api/runtime.py", "class", "AppRuntime"),
    "scene_service": (
        "src/core/use_cases/scene_operations.py",
        "class",
        "SceneOperationsService",
    ),
    "print_service": (
        "src/core/use_cases/print_readiness.py",
        "class",
        "PrintReadinessService",
    ),
    "batch_service": (
        "src/core/use_cases/batch_transform.py",
        "class",
        "BatchTransformService",
    ),
    "blender_adapter": (
        "src/adapters/mcp/blender_mcp_adapter.py",
        "class",
        "BlenderMCPAdapter",
    ),
    "print_adapter": (
        "src/adapters/print_readiness/blender_print_readiness.py",
        "class",
        "BlenderPrintReadinessAdapter",
    ),
    "batch_adapter": (
        "src/adapters/batch_transform/blender_batch_transform.py",
        "class",
        "BlenderBatchTransformAdapter",
    ),
    "socket_client": (
        "src/adapters/mcp/blender_mcp_adapter.py",
        "class",
        "BlenderSocketClient",
    ),
}

BOUNDARY_NODES = {
    "http_hosts",  # external MCP clients
    "stdio_hosts",  # external MCP clients
    "tailnet_gateway",  # MHH/Tailscale deployment boundary
    "vite_proxy",  # TypeScript configuration boundary
    "rest_ws",  # presentation adapters spanning multiple router modules
    "blender_addon",  # external Blender process and addon
}


class _ModelParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._inside_model = False
        self.chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._inside_model = tag == "script" and dict(attrs).get("id") == "model"

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._inside_model = False

    def handle_data(self, data: str) -> None:
        if self._inside_model:
            self.chunks.append(data)


def _model() -> dict[str, object]:
    parser = _ModelParser()
    parser.feed(ARTIFACT.read_text())
    assert parser.chunks, "architecture.html must contain an embedded #model"
    value = json.loads("".join(parser.chunks))
    assert isinstance(value, dict)
    return value


def test_model_nodes_equal_classified_code_and_boundary_anchors() -> None:
    model = _model()
    nodes = model["nodes"]
    assert isinstance(nodes, list)
    node_ids = {node["id"] for node in nodes if isinstance(node, dict)}

    assert node_ids == set(CODE_ANCHORS) | BOUNDARY_NODES

    by_id = {node["id"]: node for node in nodes if isinstance(node, dict)}
    for node_id, (path, kind, symbol) in CODE_ANCHORS.items():
        assert by_id[node_id].get("anchor") == {
            "path": path,
            "kind": kind,
            "symbol": symbol,
        }
    for node_id in BOUNDARY_NODES:
        assert "anchor" not in by_id[node_id]


def test_every_python_anchor_is_a_real_definition() -> None:
    for node_id, (relative_path, kind, symbol) in CODE_ANCHORS.items():
        tree = ast.parse((PROJECT_ROOT / relative_path).read_text())
        definition_type = (
            ast.ClassDef if kind == "class" else (ast.FunctionDef, ast.AsyncFunctionDef)
        )

        assert any(
            isinstance(node, definition_type) and node.name == symbol for node in ast.walk(tree)
        ), f"architecture node {node_id!r} has no {kind} {symbol!r} in {relative_path}"


def test_model_references_are_internally_consistent() -> None:
    model = _model()
    nodes = model["nodes"]
    edges = model["edges"]
    assert isinstance(nodes, list)
    assert isinstance(edges, list)
    node_ids = {node["id"] for node in nodes if isinstance(node, dict)}

    for node in nodes:
        assert isinstance(node, dict)
        depends_on = node.get("dependsOn", [])
        assert isinstance(depends_on, list)
        assert set(depends_on) <= node_ids
    for edge in edges:
        assert isinstance(edge, dict)
        assert edge.get("from") in node_ids
        assert edge.get("to") in node_ids


def test_artifact_is_self_contained_and_model_driven() -> None:
    source = ARTIFACT.read_text()

    assert '<script type="application/json" id="model">' in source
    assert "<script src=" not in source
    assert 'type="module"' not in source
    assert "fetch(" not in source
    assert "createElementNS" in source


def test_real_ci_gates_batch_transform_single_undo() -> None:
    ci = (PROJECT_ROOT / "scripts" / "ci.sh").read_text()

    assert "scripts/verify/batch_transform_verify_real.py" in ci
