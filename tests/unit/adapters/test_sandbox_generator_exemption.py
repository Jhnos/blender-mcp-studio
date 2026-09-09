"""The sandbox exemption is a set of derived strings, not a trusted caller.

The generators need `importlib`, `sys` and `runpy` to make a resident Blender
load new source; the sandbox blocks all three because code arriving from a
client must never reach them. This file pins the shape of the exemption that
resolves that: byte-for-byte equality with what the registry derives, and
nothing else.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from src.adapters.generation.authorized_code import (
    authorized_generator_code,
    generator_code_for,
)
from src.adapters.security.blender_code_sandbox import BlenderCodeSandbox
from src.core.domain.hand_instances import HAND_INSTANCES

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _sandbox() -> BlenderCodeSandbox:
    return BlenderCodeSandbox(authorized=authorized_generator_code)


@pytest.mark.parametrize("slug", sorted(HAND_INSTANCES))
def test_the_projects_own_generator_code_is_admitted(slug: str) -> None:
    code = generator_code_for(HAND_INSTANCES[slug])

    assert "importlib" in code, "if this stops being true the exemption is testing nothing"
    assert _sandbox().validate(code).allowed


@pytest.mark.parametrize("slug", sorted(HAND_INSTANCES))
def test_one_changed_character_is_a_different_string_and_is_blocked(slug: str) -> None:
    """Should-fire. An exemption that survived an edit would be an exemption on
    the shape of the code rather than on its identity."""
    code = generator_code_for(HAND_INSTANCES[slug])
    tampered = code.replace("runpy.run_path", "runpy.run_path ", 1)

    assert tampered != code
    assert not _sandbox().validate(tampered).allowed


@pytest.mark.parametrize("slug", sorted(HAND_INSTANCES))
def test_authorized_code_with_a_payload_appended_is_blocked(slug: str) -> None:
    """Equality, not containment. A prefix match would let anyone who could name
    an authorized string append whatever they liked to it."""
    code = generator_code_for(HAND_INSTANCES[slug])
    smuggled = code + "\nimport os\nos.system('id')\n"

    assert not _sandbox().validate(smuggled).allowed


def test_arbitrary_dynamic_import_is_still_blocked() -> None:
    result = _sandbox().validate("import importlib\nimportlib.import_module('os')")

    assert not result.allowed
    assert any("importlib" in violation for violation in result.violations)


@pytest.mark.parametrize("slug", sorted(HAND_INSTANCES))
def test_a_sandbox_without_the_provider_exempts_nothing(slug: str) -> None:
    """The exemption is opt-in at the composition root; the default is unchanged."""
    code = generator_code_for(HAND_INSTANCES[slug])

    assert not BlenderCodeSandbox().validate(code).allowed


def test_the_authorized_set_is_exactly_the_registry_derivation() -> None:
    expected = {generator_code_for(instance) for instance in HAND_INSTANCES.values()}

    assert authorized_generator_code() == expected


def test_the_composition_root_wires_the_provider() -> None:
    """A provider nothing injects is an exemption that silently does not exist —
    and the endpoint would fail with a security message that reads like a bug."""
    source = (PROJECT_ROOT / "api" / "runtime.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    wired = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "BlenderCodeSandbox"
        and any(keyword.arg == "authorized" for keyword in node.keywords)
    ]

    assert wired, "build_runtime must construct BlenderCodeSandbox with authorized=..."
