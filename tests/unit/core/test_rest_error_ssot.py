"""Single source of truth for how REST turns domain errors into HTTP status.

Two rules, one analyzer:

1. **No hand-written domain-error mapping.** Translating a domain exception into
   an ``HTTPException`` is one decision and belongs in one place — the
   application-wide handler in ``api/main.py``. A router that re-implements it
   drifts (this codebase already carried both ``str(exc)`` and
   ``f"Blender unreachable: {e}"`` for the same condition).

2. **The explicit guards stay untouched.** ``not configured`` 503s, 404s, the 410
   for an expired snapshot and the 500s built from result payloads are a
   *different* contract — they are decisions the endpoint genuinely owns. Their
   inventory is frozen here so a refactor that quietly changes one is visible in
   review rather than only in production.

Rule 1 covers what changes; rule 2 covers what must not. Either alone would be
partial coverage: a green light on the changed subset says nothing about the
rest, which is how a gate hands out false assurance.
"""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
ROUTERS = PROJECT_ROOT / "api" / "routers"

#: Exceptions whose HTTP mapping is owned by the application-wide handler.
#: Catching one of these in a router and raising HTTPException is the duplication.
DOMAIN_EXCEPTIONS = frozenset(
    {
        "DomainError",
        "BlenderConnectionError",
        "SceneOperationError",
        "SceneCreationError",
        "BatchTransformError",
        "PrintReadinessError",
        "SceneExportError",
    }
)

#: ``(module, function, status)`` for every HTTPException the endpoint owns.
#: Update this set only together with a deliberate change of behaviour, never to
#: silence the gate.
FROZEN_EXPLICIT_GUARDS = frozenset(
    {
        ("generate3d.py", "generate_3d", 500),
        ("generate3d.py", "generate_3d", 503),
        ("materials.py", "apply_material", 400),
        ("materials.py", "apply_material", 404),
        ("materials.py", "apply_material", 500),
        ("materials.py", "apply_material", 503),
        ("materials.py", "search_materials", 503),
        ("objects.py", "select_object", 500),
        ("objects.py", "update_object", 500),
        ("pipelines.py", "run_pipeline", 404),
        ("pipelines.py", "run_pipeline", 500),
        ("snapshots.py", "create_snapshot", 500),
        ("snapshots.py", "create_snapshot", 503),
        ("snapshots.py", "delete_snapshot", 404),
        ("snapshots.py", "delete_snapshot", 503),
        ("snapshots.py", "restore_snapshot", 404),
        ("snapshots.py", "restore_snapshot", 410),
        ("snapshots.py", "restore_snapshot", 500),
        ("snapshots.py", "restore_snapshot", 503),
        ("vision.py", "analyze_image", 413),
        ("vision.py", "analyze_image", 422),
        ("vision.py", "analyze_image", 500),
        ("vision.py", "analyze_image", 503),
        ("vision.py", "refine_model", 500),
        ("vision.py", "refine_model", 503),
    }
)


def _handler_catches_domain_error(handler: ast.ExceptHandler) -> bool:
    names: list[str] = []
    node = handler.type
    if isinstance(node, ast.Name):
        names.append(node.id)
    elif isinstance(node, ast.Tuple):
        names.extend(item.id for item in node.elts if isinstance(item, ast.Name))
    return any(name in DOMAIN_EXCEPTIONS for name in names)


def _status_of(call: ast.Call) -> int | None:
    for keyword in call.keywords:
        if keyword.arg == "status_code" and isinstance(keyword.value, ast.Constant):
            value = keyword.value.value
            if isinstance(value, int) and not isinstance(value, bool):
                return value
    return None


def _http_exception_calls(node: ast.AST) -> list[ast.Call]:
    return [
        child
        for child in ast.walk(node)
        if isinstance(child, ast.Call)
        and isinstance(child.func, ast.Name)
        and child.func.id == "HTTPException"
    ]


def _enclosing_functions(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def collect(root: Path) -> tuple[set[tuple[str, str, int]], set[tuple[str, str, int]]]:
    """Return ``(domain_mapped, explicit_guards)`` inventories for ``root``.

    A call is *domain mapped* when it sits inside an ``except`` clause that
    catches a domain exception; everything else is a guard the endpoint owns.
    """
    domain_mapped: set[tuple[str, str, int]] = set()
    explicit: set[tuple[str, str, int]] = set()

    for path in sorted(root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for function in _enclosing_functions(tree):
            in_domain_handler: set[int] = set()
            for handler in [n for n in ast.walk(function) if isinstance(n, ast.ExceptHandler)]:
                if _handler_catches_domain_error(handler):
                    for call in _http_exception_calls(handler):
                        in_domain_handler.add(id(call))

            for call in _http_exception_calls(function):
                status = _status_of(call)
                if status is None:
                    continue
                row = (path.name, function.name, status)
                if id(call) in in_domain_handler:
                    domain_mapped.add(row)
                else:
                    explicit.add(row)

    return domain_mapped, explicit


# --------------------------------------------------------------------------
# Live rules
# --------------------------------------------------------------------------


def test_routers_do_not_hand_map_domain_errors() -> None:
    domain_mapped, _ = collect(ROUTERS)
    assert not domain_mapped, (
        "these routers translate a domain exception into HTTPException themselves;\n"
        "let the application-wide handler in api/main.py do it:\n"
        + "\n".join(
            f"  {module}::{func} -> {status}" for module, func, status in sorted(domain_mapped)
        )
    )


def test_explicit_guards_match_frozen_inventory() -> None:
    _, explicit = collect(ROUTERS)
    added = explicit - FROZEN_EXPLICIT_GUARDS
    removed = FROZEN_EXPLICIT_GUARDS - explicit
    assert not (added or removed), (
        "endpoint-owned HTTPException inventory changed. This is not a lint —\n"
        "review the diff, then update FROZEN_EXPLICIT_GUARDS in the same commit.\n"
        f"  added:   {sorted(added)}\n"
        f"  removed: {sorted(removed)}"
    )


# --------------------------------------------------------------------------
# Guard self-tests
# --------------------------------------------------------------------------

_DOMAIN_SOURCE = """
from fastapi import HTTPException

async def endpoint():
    try:
        return await service.call()
    except BlenderConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
"""

_EXPLICIT_SOURCE = """
from fastapi import HTTPException

async def endpoint():
    if store is None:
        raise HTTPException(status_code=503, detail="Snapshot store not configured")
    return store
"""

_TUPLE_HANDLER_SOURCE = """
from fastapi import HTTPException

async def endpoint():
    try:
        return await service.call()
    except (ValueError, PrintReadinessError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
"""

_UNRELATED_HANDLER_SOURCE = """
from fastapi import HTTPException

async def endpoint():
    try:
        return await service.call()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
"""


def _write(root: Path, name: str, source: str) -> None:
    (root / name).write_text(source, encoding="utf-8")


def test_gate_fires_on_hand_written_domain_mapping(tmp_path: Path) -> None:
    _write(tmp_path, "r.py", _DOMAIN_SOURCE)
    domain_mapped, explicit = collect(tmp_path)
    assert domain_mapped == {("r.py", "endpoint", 503)}
    assert explicit == set()


def test_gate_passes_explicit_guard(tmp_path: Path) -> None:
    """A 503 the endpoint genuinely owns must NOT be reported."""
    _write(tmp_path, "r.py", _EXPLICIT_SOURCE)
    domain_mapped, explicit = collect(tmp_path)
    assert domain_mapped == set()
    assert explicit == {("r.py", "endpoint", 503)}


def test_gate_sees_domain_error_inside_a_tuple_handler(tmp_path: Path) -> None:
    """``except (ValueError, PrintReadinessError)`` still counts as domain mapping."""
    _write(tmp_path, "r.py", _TUPLE_HANDLER_SOURCE)
    domain_mapped, _ = collect(tmp_path)
    assert domain_mapped == {("r.py", "endpoint", 422)}


def test_gate_ignores_non_domain_handler(tmp_path: Path) -> None:
    """Catching KeyError is the endpoint's own decision, not the shared mapping."""
    _write(tmp_path, "r.py", _UNRELATED_HANDLER_SOURCE)
    domain_mapped, explicit = collect(tmp_path)
    assert domain_mapped == set()
    assert explicit == {("r.py", "endpoint", 404)}
