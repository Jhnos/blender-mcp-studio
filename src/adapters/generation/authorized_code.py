"""The closed set of generator code this project authorizes itself to run.

The sandbox blocks `importlib`, `sys` and `runpy` because code arriving from a
client must never reach them. The project's own generators need exactly those
three to make a resident Blender load new source, so running a generator
through the shared port would otherwise be impossible.

The exemption is a **set of strings**, not a caller. A string is authorized
only if it is byte-for-byte what this module derives from the instance registry
and that instance's derived contract; one changed character is a different
string and is blocked like anything else. Nothing a request carries can put a
string into the set, because the set is recomputed here from the registry and
never accepted from a caller.

Both sides of the check come from `generator_code_for` on purpose: the builder
sends what this function produces, and the sandbox admits what this function
produces. Two spellings of "the same" derivation would be two things that can
drift.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from src.core.domain.exceptions import MechanicalGenerationError
from src.core.domain.hand_instances import HAND_INSTANCES, HandInstance
from src.infrastructure.narrowing import as_str_keyed_exact, required
from src.verification.generated_artifact_bootstrap import build_generator_code
from src.verification.generated_artifact_contract import (
    GeneratedArtifactContract,
    contract_from_mapping,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_DIR = PROJECT_ROOT / "scripts" / "verify" / "contracts"


def contract_for(
    instance: HandInstance,
    project_root: Path = PROJECT_ROOT,
    contract_dir: Path = CONTRACT_DIR,
) -> GeneratedArtifactContract:
    """The instance's contract, whose reload list is derived from the import closure.

    A missing contract is refused rather than improvised: writing a reload list
    here would be the hand-typed second copy that lets a resident interpreter
    run last load's code while every gate stays green.
    """
    path = contract_dir / f"{instance.contract_name}.json"
    if not path.is_file():
        raise MechanicalGenerationError(
            f"{instance.slug} has no contract at {path}; the reload list is derived "
            "there and is not retyped here"
        )
    decoded = required(
        json.loads(path.read_text(encoding="utf-8")),
        as_str_keyed_exact,
        message=f"{path.name} must contain one JSON object",
        error=ValueError,
    )
    return contract_from_mapping(decoded, project_root)


def generator_code_for(
    instance: HandInstance,
    project_root: Path = PROJECT_ROOT,
    contract_dir: Path = CONTRACT_DIR,
) -> str:
    """The one derivation. Its only input is the registry entry."""
    return build_generator_code(contract_for(instance, project_root, contract_dir), project_root)


@lru_cache(maxsize=1)
def authorized_generator_code() -> frozenset[str]:
    """Every string the sandbox will admit past the blocklist.

    Computed once per process. Authorization is therefore fixed at start-up:
    changing a contract on disk does not widen a running service's exemption
    until it is restarted, which is the direction an accident should fail in.

    An instance with no contract contributes nothing. It is not an error here —
    the build path reports that clearly on its own — and inventing an entry for
    it would put an underived string in the authorized set.
    """
    codes: set[str] = set()
    for instance in HAND_INSTANCES.values():
        try:
            codes.add(generator_code_for(instance))
        except (MechanicalGenerationError, ValueError):
            continue
    return frozenset(codes)
