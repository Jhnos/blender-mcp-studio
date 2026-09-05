"""Keep the Blender generators calling shared primitives instead of re-typing them.

The generators were forks of each other: `m`, `add_cylinder`, `boolean`,
`cleanup_mesh` and the whole `main()` wrapper existed in several copies, some
byte-identical, some subtly divergent. `scripts/blender_mesh_primitives.py` had
already been extracted — it was simply not used by everyone.

This checks by *name*, statically. The generators import `bpy`, which is only
available inside Blender, so importing them here is not an option; and a copy
that keeps the original name is exactly the failure being prevented.
"""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
SCRIPTS = PROJECT_ROOT / "scripts"

#: Primitives with exactly one home. The value names the module that owns it.
OWNED: dict[str, str] = {
    "m": "hollow_hinge_render.py",
    "material": "blender_mesh_primitives.py",
    "add_cylinder": "blender_mesh_primitives.py",
    "boolean": "blender_mesh_primitives.py",
    "cleanup_mesh": "blender_mesh_primitives.py",
    "collection": "blender_mesh_primitives.py",
    "run_generator": "blender_generator_runner.py",
    "clear_previous": "blender_generator_runner.py",
}

#: Archived generators are frozen history and are not held to current rules.
EXCLUDED_DIRS = ("archive",)


def _live_scripts(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.py")
        if not any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts)
    )


def find_redefinitions(root: Path, owned: dict[str, str]) -> list[str]:
    """Return ``file:line -> name`` for primitives defined outside their home."""
    offenders: list[str] = []
    for path in _live_scripts(root):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            home = owned.get(node.name)
            if home is not None and path.name != home:
                offenders.append(f"{path.name}:{node.lineno} -> {node.name} (owned by {home})")
    return offenders


def test_primitives_are_defined_once() -> None:
    offenders = find_redefinitions(SCRIPTS, OWNED)
    assert not offenders, (
        "these generators re-defined a shared primitive instead of importing it:\n"
        + "\n".join(f"  {row}" for row in offenders)
    )


# --------------------------------------------------------------------------
# Guard self-tests
# --------------------------------------------------------------------------

OWNED_FIXTURE = {"m": "home.py"}


def test_gate_fires_on_a_redefinition(tmp_path: Path) -> None:
    (tmp_path / "generator.py").write_text(
        "def m(value_mm):\n    return value_mm / 1000.0\n", encoding="utf-8"
    )
    assert find_redefinitions(tmp_path, OWNED_FIXTURE) == ["generator.py:1 -> m (owned by home.py)"]


def test_gate_allows_the_owning_module(tmp_path: Path) -> None:
    (tmp_path / "home.py").write_text(
        "def m(value_mm):\n    return value_mm / 1000.0\n", encoding="utf-8"
    )
    assert find_redefinitions(tmp_path, OWNED_FIXTURE) == []


def test_gate_allows_importing_the_primitive(tmp_path: Path) -> None:
    """Importing under an alias is reuse, not redefinition."""
    (tmp_path / "generator.py").write_text("from scripts.home import m as _m\n", encoding="utf-8")
    assert find_redefinitions(tmp_path, OWNED_FIXTURE) == []


def test_gate_ignores_a_nested_helper_of_the_same_name(tmp_path: Path) -> None:
    """Only module-level definitions count; a local closure is not a second copy."""
    source = "def build():\n    def m(v):\n        return v\n    return m\n"
    (tmp_path / "generator.py").write_text(source, encoding="utf-8")
    assert find_redefinitions(tmp_path, OWNED_FIXTURE) == []


def test_gate_ignores_the_archive(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "old.py").write_text("def m(v):\n    return v\n", encoding="utf-8")
    assert find_redefinitions(tmp_path, OWNED_FIXTURE) == []
