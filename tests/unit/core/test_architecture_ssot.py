"""Fail-closed drift guards for the architecture HTML single source of truth."""

from __future__ import annotations

import ast
import json
from html.parser import HTMLParser
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
ARTIFACT = PROJECT_ROOT / "docs" / "architecture.html"
ARCHITECTURE_DOC = PROJECT_ROOT / "docs" / "01-architecture.md"

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


def _bpy_importers(root: Path) -> list[str]:
    """Files under `root` that import Blender, found by reading rather than importing."""
    hits: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            if any(name.split(".")[0] in {"bpy", "mathutils", "bmesh"} for name in names):
                hits.append(str(path.relative_to(PROJECT_ROOT)))
                break
    return hits


def test_the_bpy_import_scan_fires_on_a_planted_import() -> None:
    planted = PROJECT_ROOT / "tmp" / "bpy_scan_fixture"
    planted.mkdir(parents=True, exist_ok=True)
    try:
        (planted / "clean.py").write_text("import math\n")
        (planted / "dirty.py").write_text("def f():\n    from mathutils import Vector\n")
        assert _bpy_importers(planted) == ["tmp/bpy_scan_fixture/dirty.py"]
    finally:
        for path in planted.glob("*.py"):
            path.unlink()
        planted.rmdir()


def test_domain_and_planning_never_import_bpy() -> None:
    """DS-1: the specs and the plans have to be checkable on a machine without Blender."""
    for tree in ("src/core/domain", "src/core/planning"):
        assert (PROJECT_ROOT / tree).is_dir(), tree
        assert _bpy_importers(PROJECT_ROOT / tree) == [], tree


def test_real_ci_gates_batch_transform_single_undo() -> None:
    ci = (PROJECT_ROOT / "scripts" / "ci.sh").read_text()

    assert "scripts/verify/batch_transform_verify_real.py" in ci


def test_real_ci_gates_the_hand_contracts() -> None:
    """The contract system caught ten defects this campaign while being run by hand.

    A gate that is not in ci.sh is a gate that is not run. The three lines are
    the reference pair (both hand-v3 contracts) and the reproduction differential
    against the shipped package, in that order: the finger contract reuses the
    scene the hand contract generated, and the differential reads the STLs that
    generation exported.
    """
    ci = (PROJECT_ROOT / "scripts" / "ci.sh").read_text()

    hand = ci.index("scripts/verify/contracts/hand_v3.json")
    finger = ci.index("scripts/verify/contracts/hand_v3_finger.json --skip-generate")
    differential = ci.index(
        "scripts/verify/regenerated_package_matches_shipped.py --package hand-v3"
    )
    assert hand < finger < differential
    real_tier = ci.index("T3 · real machine (MCP↔Blender)")
    assert real_tier < hand, "the hand gates belong inside the --real tier"


def test_real_ci_runs_every_contract() -> None:
    """A contract nobody runs is a hand-run contract, and those run when someone remembers.

    D-004: every file under scripts/verify/contracts is a --real gate. Probe
    contracts go through the read-only mesh-probe checker, the rest through
    the generic verifier, and a contract that reuses a scene (--skip-generate)
    must come after a contract that generated it with the same script.
    """
    ci = (PROJECT_ROOT / "scripts" / "ci.sh").read_text()
    real_tier = ci.index("T3 · real machine (MCP↔Blender)")
    contracts = sorted((PROJECT_ROOT / "scripts" / "verify" / "contracts").glob("*.json"))
    assert contracts, "no contracts to gate — the check is vacuous"

    missing = [
        contract.name
        for contract in contracts
        if ci.find(f"scripts/verify/contracts/{contract.name}", real_tier) < 0
    ]
    assert missing == [], f"contracts ci.sh --real never runs: {missing}"

    lines = ci.splitlines()
    for contract in contracts:
        index, line = next(
            (i, text) for i, text in enumerate(lines) if f"contracts/{contract.name}" in text
        )
        probe = contract.name.endswith("_probe.json")
        runner = "mesh_probe_verify_real.py" if probe else "generated_artifact_verify_real.py"
        assert runner in line, f"{contract.name} runs through the wrong checker: {line.strip()}"
        if "--skip-generate" not in line:
            continue
        generator = json.loads(contract.read_text())["generator_script"]
        earlier = [
            text
            for text in lines[:index]
            if "generated_artifact_verify_real.py" in text and "--skip-generate" not in text
        ]
        assert any(
            json.loads((PROJECT_ROOT / _contract_path(text)).read_text())["generator_script"]
            == generator
            for text in earlier
        ), f"{contract.name} reuses a scene nothing before it generated"


def _contract_path(ci_line: str) -> str:
    return next(token for token in ci_line.split() if token.startswith("scripts/verify/contracts/"))


def test_frontend_productivity_boundaries_are_documented_and_exist() -> None:
    source = ARCHITECTURE_DOC.read_text()
    anchors = {
        "web/src/commands/registry.ts": "CommandRegistry",
        "web/src/commands/studioCommands.ts": "StudioCommandActions",
        "web/src/hooks/useGlobalShortcuts.ts": "useGlobalShortcuts",
        "web/src/stores/operationStore.ts": "OperationStore",
        "web/src/stores/batchSelectionStore.ts": "BatchSelectionStore",
    }

    for path, documented_name in anchors.items():
        assert (PROJECT_ROOT / path).is_file(), f"missing frontend architecture anchor: {path}"
        assert documented_name in source, f"01-architecture.md must document {documented_name}"


def _first_party_importers(package: str, roots: list[Path]) -> list[str]:
    """Files under `roots` (outside the package itself) that import `src.<package>`."""
    needle = f"src.{package}"
    hits: list[str] = []
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            if path.is_relative_to(PROJECT_ROOT / "src" / package):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                if any(name == needle or name.startswith(needle + ".") for name in names):
                    hits.append(str(path.relative_to(PROJECT_ROOT)))
                    break
    return hits


def test_no_src_package_is_an_island() -> None:
    """A package nothing in production imports is dead code wearing a scope label.

    `src/workflows` shipped in the initial implementation, was never wired to
    any REST, MCP or UI path, and stayed for months because its own unit test
    kept it green. Production means api/, scripts/ and the other src packages;
    a package's own tests do not count.
    """
    production = [PROJECT_ROOT / "api", PROJECT_ROOT / "scripts", PROJECT_ROOT / "src"]
    islands = [
        package.name
        for package in sorted((PROJECT_ROOT / "src").iterdir())
        if package.is_dir() and package.name != "__pycache__"
        and not _first_party_importers(package.name, production)
    ]
    assert islands == [], f"src packages nothing in production imports: {islands}"
