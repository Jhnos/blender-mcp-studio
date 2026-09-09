"""Runs a registered instance's generator in the shared Blender and measures it.

Three reuse decisions, each of them load-bearing:

* The reload list comes from the instance's contract file, which
  `build_hand_contracts.py` derives from the import closure. Typing a second
  list here would recreate the failure where a resident interpreter silently
  ran last load's code and every gate stayed green
  (`docs/LESSONS_LEARNED.md`, "常駐程序的『要重載哪些模組』清單是手打的").
* The code string comes from `build_generator_code`, the same builder the CI
  path uses, so the product path and the verification path cannot drift into
  generating two different things.
* Measurement is face count and dimensions read back from the exported STL,
  never a hash: the generators are not byte-reproducible.

Nothing from an HTTP request reaches any of it. The only variable input is the
`HandInstance` the application already resolved from the registry.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.adapters.blender_scripts.runner import run_script
from src.core.domain.exceptions import MechanicalGenerationError
from src.core.domain.hand_instances import HandInstance
from src.core.domain.mechanical_generation import BuiltPart, InstanceBuild
from src.core.ports.blender_port import BlenderPort
from src.infrastructure.narrowing import as_str_keyed_exact, required
from src.verification.artifact_files import binary_stl_metrics
from src.verification.generated_artifact_bootstrap import build_generator_code
from src.verification.generated_artifact_contract import (
    GeneratedArtifactContract,
    contract_from_mapping,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_DIR = PROJECT_ROOT / "scripts" / "verify" / "contracts"


class BlenderInstanceBuilder:
    """Adapter side of `InstanceBuilderPort`."""

    def __init__(
        self,
        blender: BlenderPort,
        *,
        project_root: Path = PROJECT_ROOT,
        contract_dir: Path = CONTRACT_DIR,
    ) -> None:
        self._blender = blender
        self._project_root = project_root
        self._contract_dir = contract_dir

    async def build_instance(self, instance: HandInstance) -> InstanceBuild:
        code = self.generator_code(instance)
        outcome = await run_script(self._blender, code)
        if not outcome.success:
            raise MechanicalGenerationError(
                f"{instance.slug} generator failed in Blender: {outcome.error or 'no detail'}"
            )
        return InstanceBuild(
            slug=instance.slug,
            output_dir=instance.output_dir,
            parts=tuple(self._measure(instance, name) for name in instance.stl_files),
        )

    def generator_code(self, instance: HandInstance) -> str:
        """Exposed so a guard can assert the string is derived from the registry alone."""
        return build_generator_code(self._contract_for(instance), self._project_root)

    def _contract_for(self, instance: HandInstance) -> GeneratedArtifactContract:
        path = self._contract_dir / f"{instance.contract_name}.json"
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
        return contract_from_mapping(decoded, self._project_root)

    def _measure(self, instance: HandInstance, name: str) -> BuiltPart:
        path = self._project_root / instance.output_dir / name
        try:
            metrics = binary_stl_metrics(path.read_bytes())
        except (OSError, ValueError) as exc:
            raise MechanicalGenerationError(
                f"{instance.slug} declares {name} but it is missing or unreadable "
                f"after the build: {exc}"
            ) from exc
        return BuiltPart(
            name=name,
            face_count=metrics.triangle_count,
            dimensions_mm=metrics.dimensions_mm,
        )
