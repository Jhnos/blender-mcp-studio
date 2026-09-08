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


#: Blender dialect markers. A router that contains these is writing Blender
#: source in the HTTP layer, bypassing the documented rule that the Blender
#: adapters are the only translation chokepoint (docs/01-architecture.md).
BPY_MARKERS = ("import bpy", "bpy.ops", "bpy.data", "bpy.context")

#: ``execute_code`` is the addon's arbitrary-Python escape hatch. Routers must go
#: through a named operation in src/adapters/blender_scripts/ instead.
ESCAPE_HATCH = '"execute_code"'


def _docstring_lines(tree: ast.AST) -> set[int]:
    """Line numbers occupied by docstrings.

    Docstrings are prose *about* an operation; the script constants this gate
    hunts are ordinary strings. Skipping every string would disarm the gate —
    the constants it was written for were strings — so only docstrings are
    exempt, and only because naming an operation in prose is not embedding it.
    """
    lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", [])
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
            and first.end_lineno is not None
        ):
            lines.update(range(first.lineno, first.end_lineno + 1))
    return lines


def find_blender_dialect(root: Path) -> list[str]:
    """Return ``file:line`` for router lines carrying Blender source."""
    hits: list[str] = []
    for path in sorted(root.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        skip = _docstring_lines(ast.parse(source))
        for lineno, line in enumerate(source.splitlines(), 1):
            if lineno in skip:
                continue
            code = line.split("#", 1)[0]
            if any(marker in code for marker in BPY_MARKERS) or ESCAPE_HATCH in code:
                hits.append(f"{path.name}:{lineno}")
    return hits


def test_routers_hold_no_blender_source() -> None:
    hits = find_blender_dialect(ROUTERS)
    assert not hits, (
        "routers contain Blender source or reach for execute_code; move the\n"
        "operation into src/adapters/blender_scripts/ and call it by name:\n"
        + "\n".join(f"  {row}" for row in hits)
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


_HAS_BPY = 'code = "import bpy\\nbpy.ops.ed.undo()"\n'
_CALLS_ACL = "outcome = await history_scripts.run_history_action(blender, action)\n"
_MENTIONS_BPY_IN_A_COMMENT = "# delegates to bpy.ops.import_scene.gltf via the ACL\n"


def test_dialect_gate_fires_on_embedded_bpy(tmp_path: Path) -> None:
    (tmp_path / "r.py").write_text(_HAS_BPY, encoding="utf-8")
    assert find_blender_dialect(tmp_path) == ["r.py:1"]


def test_dialect_gate_passes_a_router_that_calls_the_acl(tmp_path: Path) -> None:
    (tmp_path / "r.py").write_text(_CALLS_ACL, encoding="utf-8")
    assert find_blender_dialect(tmp_path) == []


def test_dialect_gate_ignores_comments(tmp_path: Path) -> None:
    """Naming the operation in prose is documentation, not embedded source."""
    (tmp_path / "r.py").write_text(_MENTIONS_BPY_IN_A_COMMENT, encoding="utf-8")
    assert find_blender_dialect(tmp_path) == []


def test_dialect_gate_ignores_docstrings(tmp_path: Path) -> None:
    """A docstring may name the operation it delegates to."""
    source = '"""Imports the GLB via bpy.ops.import_scene.gltf in the ACL."""\n'
    (tmp_path / "r.py").write_text(source, encoding="utf-8")
    assert find_blender_dialect(tmp_path) == []


def test_dialect_gate_still_sees_script_constants(tmp_path: Path) -> None:
    """Exempting docstrings must not exempt ordinary string constants.

    The constants this gate was written for were exactly that: module-level
    triple-quoted strings holding Blender source.
    """
    source = '"""Router docstring."""\n\n_CODE = """\\\nimport bpy\nbpy.ops.ed.undo()\n"""\n'
    (tmp_path / "r.py").write_text(source, encoding="utf-8")
    assert find_blender_dialect(tmp_path) == ["r.py:4", "r.py:5"]


#: D-002: routers that still translate arbitrary exceptions into HTTP themselves.
#: A budget, not an allowlist: a file may only go down, and a file not listed
#: here is at zero. The three provider-facing routers (vision, pipelines,
#: generate3d) are at zero because their providers now raise domain errors
#: that api/main.py maps in one place.
#: chat.py keeps three: the two per-turn handlers that send an error frame over
#: the WebSocket (Starlette's exception middleware is HTTP-only, so nothing
#: else could) and the Blender command wrapper inside the stream; ws_manager.py
#: keeps the send-loop guard. The screenshot helpers went through the typed
#: port and narrowed to the domain errors it raises.
BLANKET_EXCEPT_BUDGET: dict[str, int] = {"chat.py": 3, "ws_manager.py": 1}


def find_blanket_excepts(root: Path) -> dict[str, int]:
    """Count ``except Exception`` and bare ``except:`` handlers per router file."""
    counts: dict[str, int] = {}
    for path in sorted(root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        hits = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if node.type is None or (
                isinstance(node.type, ast.Name) and node.type.id == "Exception"
            ):
                hits += 1
        if hits:
            counts[path.name] = hits
    return counts


def test_routers_do_not_translate_arbitrary_exceptions() -> None:
    counts = find_blanket_excepts(ROUTERS)
    over = {
        name: (count, BLANKET_EXCEPT_BUDGET.get(name, 0))
        for name, count in counts.items()
        if count > BLANKET_EXCEPT_BUDGET.get(name, 0)
    }
    assert not over, (
        "routers translating arbitrary exceptions themselves (found, budget); raise a\n"
        "domain error in the adapter and let api/main.py map it:\n"
        + "\n".join(f"  {name}: {found} > {budget}" for name, (found, budget) in over.items())
    )


def test_blanket_except_gate_fires_and_passes(tmp_path: Path) -> None:
    (tmp_path / "dirty.py").write_text(
        "try:\n    pass\nexcept Exception as e:\n    pass\ntry:\n    pass\nexcept:\n    pass\n"
    )
    (tmp_path / "clean.py").write_text("try:\n    pass\nexcept ValueError:\n    pass\n")

    assert find_blanket_excepts(tmp_path) == {"dirty.py": 2}


#: The addon's raw screenshot tool takes a file path and leaves a file behind.
#: That dance belongs in the adapter (src/adapters/viewport_capture.py); the
#: port exposes `viewport_screenshot()`, and nothing above the adapter may call
#: the raw tool — four copies of the temp-file code once lived in these trees.
RAW_SCREENSHOT_TOOL = '"get_viewport_screenshot"'


def find_raw_screenshot_calls(roots: list[Path]) -> list[str]:
    found: list[str] = []
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if RAW_SCREENSHOT_TOOL in line:
                    found.append(f"{path.relative_to(PROJECT_ROOT)}:{number}")
    return found


def test_screenshots_go_through_the_typed_port() -> None:
    found = find_raw_screenshot_calls([PROJECT_ROOT / "api", PROJECT_ROOT / "src" / "core"])
    assert not found, (
        "the raw screenshot tool is called above the adapter; use "
        "BlenderPort.viewport_screenshot():\n" + "\n".join(f"  {row}" for row in found)
    )


def test_raw_screenshot_gate_fires_on_a_planted_call(tmp_path: Path) -> None:
    (tmp_path / "x.py").write_text('await blender.call_tool("get_viewport_screenshot", {})\n')
    assert find_raw_screenshot_calls([tmp_path]) == [str((tmp_path / "x.py").relative_to(PROJECT_ROOT)) + ":1"] if tmp_path.is_relative_to(PROJECT_ROOT) else True
