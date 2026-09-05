"""Composition belongs to the composition root, not to delivery adapters.

``api/runtime.py`` is documented as the composition root (docs/01-architecture.md,
"Shared runtime"). A router that assembles a use case from adapters at request
time moves that decision into the delivery layer, and — because ``app.state``
hands back ``Any`` — it does so in a place no type checker can see.

That blind spot is not hypothetical here: ``POST /api/refine`` called
``adapter_factory.create_llm_adapter()``, a method that exists on neither
``AdapterFactoryPort`` nor ``ConcreteAdapterFactory``. Every gate stayed green,
because the only test double for the factory was a bare ``MagicMock`` that
answers to any attribute name.

So this module enforces two things: routers do not construct use cases, and the
factory port is exercised through a spec-bound double that refuses invented
method names.
"""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock

from src.core.ports.adapter_factory_port import AdapterFactoryPort

PROJECT_ROOT = Path(__file__).parents[3]
ROUTERS = PROJECT_ROOT / "api" / "routers"


def find_use_case_constructions(root: Path) -> list[str]:
    """Return ``module:line -> Name`` for every ``*UseCase(...)`` call under root."""
    found: list[str] = []
    for path in sorted(root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id.endswith("UseCase")
            ):
                found.append(f"{path.name}:{node.lineno} -> {node.func.id}")
    return found


def test_routers_do_not_construct_use_cases() -> None:
    found = find_use_case_constructions(ROUTERS)
    assert not found, (
        "routers assembled a use case from adapters; build it in api/runtime.py\n"
        "and read it off the runtime instead:\n" + "\n".join(f"  {row}" for row in found)
    )


def test_adapter_factory_port_has_no_create_llm_adapter() -> None:
    """Pins the real interface, so a caller cannot invent a method name.

    A bare ``MagicMock`` answers to anything; a spec-bound one does not. This is
    the difference that let a non-existent method survive in production code.
    """
    double = MagicMock(spec=AdapterFactoryPort)
    assert hasattr(double, "build_llm_adapter")
    assert not hasattr(double, "create_llm_adapter")


# --------------------------------------------------------------------------
# Guard self-tests
# --------------------------------------------------------------------------

_CONSTRUCTS = """
async def endpoint(request):
    use_case = IterativeRefinementUseCase(llm=llm, blender=blender)
    return await use_case.execute()
"""

_READS_RUNTIME = """
async def endpoint(request):
    use_case = request.app.state.iterative_refinement
    return await use_case.execute()
"""

_UNRELATED_CALL = """
async def endpoint(request):
    spec = PrintReadinessSpec(selection_only=False)
    return await request.app.state.print_readiness.check(spec)
"""


def test_gate_fires_on_use_case_construction(tmp_path: Path) -> None:
    (tmp_path / "r.py").write_text(_CONSTRUCTS, encoding="utf-8")
    assert find_use_case_constructions(tmp_path) == ["r.py:3 -> IterativeRefinementUseCase"]


def test_gate_passes_when_router_reads_the_runtime(tmp_path: Path) -> None:
    (tmp_path / "r.py").write_text(_READS_RUNTIME, encoding="utf-8")
    assert find_use_case_constructions(tmp_path) == []


def test_gate_ignores_ordinary_constructor_calls(tmp_path: Path) -> None:
    """Building a request DTO is not composition and must not be reported."""
    (tmp_path / "r.py").write_text(_UNRELATED_CALL, encoding="utf-8")
    assert find_use_case_constructions(tmp_path) == []
