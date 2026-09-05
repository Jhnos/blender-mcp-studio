"""No project imports inside the code strings sent to Blender.

The adapters and verifiers build Blender scripts as string literals and hand
them to `execute_code`. Blender runs them in its own interpreter, which has no
knowledge of this repository — `from src.…` there raises `ModuleNotFoundError`
at runtime, inside Blender, where no static tool is looking.

Nothing else catches this. Ruff, mypy and the narrowing gate all parse the file
and see a string; the unit and e2e tiers never execute the string. It only fails
on the real machine — and for a script that only a human runs, not even then.
That is exactly the shape of a defect worth a gate: cheap to check, invisible to
every other check, and expensive to find.

`import bpy`, `from mathutils import …` and the rest of the Blender dialect are
expected inside those strings and must not be reported.
"""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
SCANNED_TREES = ("src", "api", "scripts")

#: Import prefixes that only resolve inside this repository's interpreter.
PROJECT_PREFIXES = ("src.", "api.", "scripts.", "tests.")

EXCLUDED_DIRS = ("__pycache__", "archive")


def _python_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.py")
        if not any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts)
    )


def _real_import_lines(tree: ast.AST) -> set[int]:
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            lines.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    return lines


def find_embedded_project_imports(root: Path) -> list[str]:
    """Return ``file:line`` for project imports that live inside string literals.

    An import the AST does not report as a real import, on a line that starts
    with ``import``/``from``, is text inside a string. Only project-module ones
    are reported: Blender's own modules belong there.
    """
    offenders: list[str] = []
    for path in _python_files(root):
        source = path.read_text(encoding="utf-8")
        real = _real_import_lines(ast.parse(source))
        for lineno, line in enumerate(source.splitlines(), 1):
            if lineno in real or not line.startswith(("import ", "from ")):
                continue
            target = line.split()[1] if len(line.split()) > 1 else ""
            if target.startswith(PROJECT_PREFIXES):
                offenders.append(f"{path.relative_to(root)}:{lineno}: {line.strip()}")
    return offenders


def test_no_project_imports_inside_blender_code_strings() -> None:
    offenders: list[str] = []
    for tree in SCANNED_TREES:
        offenders.extend(find_embedded_project_imports(PROJECT_ROOT / tree))
    assert not offenders, (
        "these imports sit inside a string that Blender executes; Blender cannot\n"
        "resolve this repository's modules:\n" + "\n".join(f"  {row}" for row in offenders)
    )


# --------------------------------------------------------------------------
# Guard self-tests
# --------------------------------------------------------------------------

_EMBEDDED_PROJECT_IMPORT = '''CODE = """\\
import bpy
from src.infrastructure.narrowing import as_str
print("hi")
"""
'''

_EMBEDDED_BLENDER_IMPORTS = '''CODE = """\\
import bpy, bmesh, json
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
print("hi")
"""
'''

_REAL_PROJECT_IMPORT = "from src.infrastructure.narrowing import as_str\n"


def test_gate_fires_on_a_project_import_inside_a_code_string(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text(_EMBEDDED_PROJECT_IMPORT, encoding="utf-8")
    assert find_embedded_project_imports(tmp_path) == [
        "m.py:3: from src.infrastructure.narrowing import as_str"
    ]


def test_gate_allows_blender_dialect_inside_a_code_string(tmp_path: Path) -> None:
    """The whole point of those strings is to import bpy and friends."""
    (tmp_path / "m.py").write_text(_EMBEDDED_BLENDER_IMPORTS, encoding="utf-8")
    assert find_embedded_project_imports(tmp_path) == []


def test_gate_allows_a_genuine_module_level_project_import(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text(_REAL_PROJECT_IMPORT, encoding="utf-8")
    assert find_embedded_project_imports(tmp_path) == []


def test_gate_ignores_the_archive(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "old.py").write_text(_EMBEDDED_PROJECT_IMPORT, encoding="utf-8")
    assert find_embedded_project_imports(tmp_path) == []
