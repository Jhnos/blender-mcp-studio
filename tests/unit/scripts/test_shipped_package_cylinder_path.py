"""A precision upgrade of a shared primitive must not silently change shipped packages.

Observed 2026-10-21: `add_cylinder` gained exact quarter turns (coordinate
permutation instead of a float rotation) for the lab-station joints. The hand
generators build their pins through the same primitive with `axis=solid.axis`,
so hand-v3 regenerated with 3932 phalanx triangles against a shipped manifest of
3434 (+14%, tiny triangles 18 -> 64) and the "regenerated package matches
shipped" gate stopped the real tier. The published manifests are the contract;
switching them to the exact path is a republish decision, not a side effect of
editing the primitive. Checked statically: the generators import `bpy`.
"""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
PRIMITIVES = PROJECT_ROOT / "scripts" / "blender_mesh_primitives.py"
HAND_GEOMETRY = PROJECT_ROOT / "scripts" / "hand_geometry.py"


def _function(path: Path, name: str) -> ast.FunctionDef:
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} not found in {path.name}")


def _calls(path: Path, name: str) -> list[ast.Call]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name
    ]


def test_exact_axes_is_an_explicit_choice_that_defaults_to_the_lab_station_path() -> None:
    function = _function(PRIMITIVES, "add_cylinder")
    names = [arg.arg for arg in function.args.args + function.args.kwonlyargs]
    assert "exact_axes" in names
    defaults = dict(
        zip(
            [arg.arg for arg in function.args.args][-len(function.args.defaults) :],
            function.args.defaults,
            strict=True,
        )
    )
    default = defaults.get("exact_axes")
    assert isinstance(default, ast.Constant) and default.value is True


def test_hand_generators_keep_the_float_rotation_their_shipped_packages_were_built_from() -> None:
    calls = _calls(HAND_GEOMETRY, "add_cylinder")
    assert calls, "hand_geometry no longer builds cylinders through the shared primitive"
    for call in calls:
        flags = {kw.arg: kw.value for kw in call.keywords}
        assert "exact_axes" in flags, "a hand cylinder call does not say which path it takes"
        value = flags["exact_axes"]
        assert isinstance(value, ast.Constant) and value.value is False
