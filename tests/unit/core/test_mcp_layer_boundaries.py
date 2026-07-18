"""Mechanical dependency-direction guards for the client-neutral MCP layer."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

FORBIDDEN = {"fastapi", "fastmcp", "httpx", "mcp", "starlette"}
PURE_DOMAIN_FORBIDDEN = FORBIDDEN | {"pydantic", "requests", "src", "yaml"}


def forbidden_imports(path: Path, forbidden: set[str]) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module]
        else:
            names = []
        for name in names:
            if name.split(".", 1)[0] in forbidden:
                violations.append(f"{path}:{node.lineno}:{name}")
    return violations


def test_core_does_not_import_mcp_or_http_frameworks() -> None:
    violations: list[str] = []
    for path in Path("src/core").rglob("*.py"):
        violations.extend(forbidden_imports(path, FORBIDDEN))
    assert violations == []


def test_new_scene_domain_values_are_stdlib_only() -> None:
    path = Path("src/core/domain/scene_operations.py")
    assert forbidden_imports(path, PURE_DOMAIN_FORBIDDEN) == []


@pytest.mark.parametrize(
    "source",
    [
        "import fastmcp\n",
        "from pydantic import BaseModel\n",
        "from src.adapters.mcp import client\n",
    ],
)
def test_import_sentinel_negative_fixture_fires(tmp_path: Path, source: str) -> None:
    bad_module = tmp_path / "bad_dependency.py"
    bad_module.write_text(source, encoding="utf-8")
    assert forbidden_imports(bad_module, PURE_DOMAIN_FORBIDDEN) != []
