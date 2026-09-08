"""Which first-party modules a generator reaches, read from source.

The contract runner reloads each module on its list before running the
generator inside a resident Blender. A module the generator reaches that is
not on the list keeps whatever code Blender loaded last, and the run reports
green against a hand it did not build. The lists were hand-written; this
derives them, leaves first, so a reloaded dependent sees its reloaded leaves.

By reading, not importing: every generator imports `bpy` at the top.
"""

from __future__ import annotations

import ast
from pathlib import Path

FIRST_PARTY_ROOTS = ("scripts", "src")


def first_party_imports(path: Path) -> tuple[str, ...]:
    """Modules under `scripts.` or `src.` this file imports, in source order, once each."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module]
        else:
            continue
        found.extend(
            (node.lineno, name) for name in names if name.split(".")[0] in FIRST_PARTY_ROOTS
        )
    ordered: list[str] = []
    for _, name in sorted(found):
        if name not in ordered:
            ordered.append(name)
    return tuple(ordered)


def _module_file(project_root: Path, module: str) -> Path:
    stem = project_root.joinpath(*module.split("."))
    if stem.with_suffix(".py").is_file():
        return stem.with_suffix(".py")
    if (stem / "__init__.py").is_file():
        return stem / "__init__.py"
    raise FileNotFoundError(f"{module} is imported but has no file under {project_root}")


def reload_modules_for(project_root: Path, script: Path) -> tuple[str, ...]:
    """The generator's first-party import closure in post-order: leaves before dependents."""
    order: list[str] = []
    seen: set[str] = set()

    def visit(path: Path) -> None:
        for module in first_party_imports(path):
            if module in seen:
                continue
            seen.add(module)
            visit(_module_file(project_root, module))
            order.append(module)

    visit(script)
    return tuple(order)
