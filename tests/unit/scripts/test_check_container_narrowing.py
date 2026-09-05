"""Tests for the container-narrowing CI gate.

This gate blocks every push, and until now had no test of its own. That is how
its blind spot survived: ``TARGET_TYPES`` listed only ``dict`` and ``list``
while four call sites narrowed with ``Mapping`` and ``Sequence``, so the gate
printed OK over code it structurally could not see.

Both halves are covered deliberately. The should-fire cases prove it still
catches; the should-pass cases prove widening the type set did not turn it into
a gate that flags every ``isinstance``. A checker with only the first half looks
identical to one that is broken in the second.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
SCRIPT = PROJECT_ROOT / "scripts" / "check_container_narrowing.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_container_narrowing", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load()


def _findings(tmp_path: Path, source: str) -> list[tuple[str, int, str]]:
    target = tmp_path / "sample.py"
    target.write_text(source, encoding="utf-8")
    return gate._check_file(str(target))


# --------------------------------------------------------------------------
# should-fire
# --------------------------------------------------------------------------

FLAGGED = [
    pytest.param("isinstance(x, dict)", id="dict"),
    pytest.param("isinstance(x, list)", id="list"),
    pytest.param("isinstance(x, tuple)", id="tuple"),
    pytest.param("isinstance(x, set)", id="set"),
    pytest.param("isinstance(x, Mapping)", id="Mapping"),
    pytest.param("isinstance(x, Sequence)", id="Sequence"),
    pytest.param("isinstance(x, MutableMapping)", id="MutableMapping"),
    pytest.param("isinstance(x, (str, list))", id="inside-a-tuple-of-types"),
]


@pytest.mark.parametrize("expression", FLAGGED)
def test_gate_flags_container_narrowing(tmp_path: Path, expression: str) -> None:
    assert _findings(tmp_path, f"if {expression}:\n    pass\n")


def test_gate_flags_the_abstract_types_it_used_to_miss(tmp_path: Path) -> None:
    """The regression this widening was written for.

    ``Mapping`` and ``Sequence`` are the exact names that slipped past the
    original ``{"dict", "list"}`` set in shipped code.
    """
    source = "if not isinstance(value, Mapping):\n    pass\nif isinstance(v, Sequence):\n    pass\n"
    assert len(_findings(tmp_path, source)) == 2


# --------------------------------------------------------------------------
# should-pass
# --------------------------------------------------------------------------

ALLOWED = [
    pytest.param("isinstance(x, str)", id="str"),
    pytest.param("isinstance(x, int)", id="int"),
    pytest.param("isinstance(x, bool)", id="bool"),
    pytest.param("isinstance(x, (str, bytes))", id="text-only-guard"),
    pytest.param("isinstance(x, SomeDomainClass)", id="domain-class"),
]


@pytest.mark.parametrize("expression", ALLOWED)
def test_gate_ignores_scalar_and_domain_checks(tmp_path: Path, expression: str) -> None:
    """Scalar narrowing loses no type parameters, so it is not this gate's business."""
    assert _findings(tmp_path, f"if {expression}:\n    pass\n") == []


def test_waiver_with_a_reason_silences_a_finding(tmp_path: Path) -> None:
    source = "if isinstance(x, dict):  # narrow-ok: rebuilt with checked keys below\n    pass\n"
    assert _findings(tmp_path, source) == []


def test_bare_waiver_without_a_reason_does_not_silence(tmp_path: Path) -> None:
    """A waiver must carry a judgement a reviewer can weigh, not act as a mute switch."""
    source = "if isinstance(x, dict):  # narrow-ok:\n    pass\n"
    assert _findings(tmp_path, source)


def test_isinstance_inside_a_string_is_not_code(tmp_path: Path) -> None:
    source = 'DOC = "call isinstance(x, dict) here"\n'
    assert _findings(tmp_path, source) == []


# --------------------------------------------------------------------------
# wiring: the gate must actually run over the real trees
# --------------------------------------------------------------------------


def test_gate_is_wired_into_ci() -> None:
    ci = (PROJECT_ROOT / "scripts" / "ci.sh").read_text(encoding="utf-8")
    assert "check_container_narrowing.py" in ci
    assert "_run hard" in ci.split("check_container_narrowing.py")[0].splitlines()[-1]


def test_ssot_module_is_the_only_allowlisted_path() -> None:
    """The exemption list is one module by design; a growing list is a smell."""
    assert {"src/infrastructure/narrowing.py"} == gate.ALLOWLIST_PATHS


def test_gate_covers_the_scripts_tree() -> None:
    """scripts/ was outside every Python gate until 2026-09-05.

    Two thousand lines — including this gate's own source — were unlinted,
    untyped and unscanned. A gate that does not read a tree cannot report on it,
    and "no findings" from an unread tree looks exactly like a clean one.
    """
    ci = (PROJECT_ROOT / "scripts" / "ci.sh").read_text(encoding="utf-8")
    for line in ci.splitlines():
        if "check_container_narrowing.py" in line and "_run hard" in line:
            assert line.rstrip().endswith("src api scripts")
            return
    raise AssertionError("no hard gate invoking check_container_narrowing.py found in ci.sh")


def test_archived_code_is_skipped(tmp_path: Path) -> None:
    """Frozen history is excluded here exactly as it is for ruff and mypy.

    A gate whose scope differs from its siblings' produces findings nobody is
    allowed to act on — the archive is kept findable, not kept current.
    """
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "old.py").write_text("if isinstance(x, dict):\n    pass\n", encoding="utf-8")
    (tmp_path / "live.py").write_text("if isinstance(x, dict):\n    pass\n", encoding="utf-8")

    scanned = sorted(Path(path).name for path in gate._iter_py_files((str(tmp_path),)))

    assert scanned == ["live.py"]
