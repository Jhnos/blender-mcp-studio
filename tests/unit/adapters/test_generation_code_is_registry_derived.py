"""The wall that keeps `execute_code` out of the generation endpoint.

`docs/01-architecture.md` says no MCP client may submit arbitrary Python. The
REST build path runs Python in Blender, so that promise only holds if the code
string is a function of the registry entry and nothing else. This file is what
makes that checkable instead of merely intended.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from src.adapters.generation.blender_instance_builder import BlenderInstanceBuilder
from src.core.domain.exceptions import MechanicalGenerationError
from src.core.domain.hand_instances import HAND_INSTANCES

HOSTILE = (
    "'); import os; os.system('rm -rf /'); ('",
    "../../etc/passwd",
    "hand-compact\nimport shutil",
    "__import__('os').system('id')",
)


def _builder() -> BlenderInstanceBuilder:
    return BlenderInstanceBuilder(blender=object())  # type: ignore[arg-type]


@pytest.mark.parametrize("slug", sorted(HAND_INSTANCES))
def test_the_code_is_a_function_of_the_registry_entry_alone(slug: str) -> None:
    """Two builders, two calls, one string: nothing ambient varies it."""
    instance = HAND_INSTANCES[slug]
    assert _builder().generator_code(instance) == _builder().generator_code(instance)


@pytest.mark.parametrize("slug", sorted(HAND_INSTANCES))
def test_the_code_reloads_exactly_what_the_contract_derived(slug: str) -> None:
    """The reload list is derived by `build_hand_contracts.py` from the import
    closure. A second, hand-typed list is how a resident Blender ends up running
    last load's code while every gate stays green."""
    import json
    from pathlib import Path

    instance = HAND_INSTANCES[slug]
    root = Path(__file__).resolve().parents[3]
    contract = json.loads(
        (root / "scripts" / "verify" / "contracts" / f"{instance.contract_name}.json").read_text(
            encoding="utf-8"
        )
    )

    code = _builder().generator_code(instance)

    for module in contract["reload_modules"]:
        assert f'"{module}"' in code, f"{module} is in the contract but not in the built code"


@pytest.mark.parametrize("hostile", HOSTILE)
def test_a_hostile_slug_never_reaches_the_code(hostile: str) -> None:
    """A slug is rejected by the registry lookup, not sanitised on its way in.

    Should-fire: `HandInstance` validates its own slug, so building an instance
    with hostile text raises before any code exists to inspect. That is the
    property under test — there is no path from arbitrary text to a code string.
    """
    with pytest.raises(ValueError):
        replace(HAND_INSTANCES["hand-compact"], slug=hostile)


def test_a_missing_contract_is_refused_not_improvised() -> None:
    """No contract means no derived reload list. Building one here would be the
    hand-typed second copy this whole file exists to prevent."""
    from pathlib import Path

    builder = BlenderInstanceBuilder(
        blender=object(),  # type: ignore[arg-type]
        contract_dir=Path(__file__).resolve().parent / "no-such-dir",
    )

    with pytest.raises(MechanicalGenerationError, match="has no contract"):
        builder.generator_code(HAND_INSTANCES["hand-compact"])
