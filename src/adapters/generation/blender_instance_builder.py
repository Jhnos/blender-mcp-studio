"""Runs a registered instance's generator in the shared Blender and measures it.

Three reuse decisions, each of them load-bearing:

* The code string comes from `authorized_code.generator_code_for` — the same
  function the sandbox uses to decide what it will admit. Two spellings of the
  derivation would be two things that can drift apart.
* That derivation reads the reload list out of the instance's contract, which
  `build_hand_contracts.py` derives from the import closure. Typing a second
  list here would recreate the failure where a resident interpreter silently
  ran last load's code and every gate stayed green
  (`docs/LESSONS_LEARNED.md`, "常駐程序的『要重載哪些模組』清單是手打的").
* Measurement is face count and dimensions read back from the exported STL,
  never a hash: the generators are not byte-reproducible.

Nothing from an HTTP request reaches any of it. The only variable input is the
`HandInstance` the application already resolved from the registry.
"""

from __future__ import annotations

from pathlib import Path

from src.adapters.blender_scripts.runner import run_script
from src.adapters.generation.authorized_code import (
    CONTRACT_DIR,
    PROJECT_ROOT,
    generator_code_for,
)
from src.core.domain.exceptions import MechanicalGenerationError
from src.core.domain.hand_instances import HandInstance
from src.core.domain.mechanical_generation import BuiltPart, InstanceBuild
from src.core.ports.blender_port import BlenderPort
from src.verification.artifact_files import binary_stl_metrics


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
        outcome = await run_script(self._blender, self.generator_code(instance))
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
        return generator_code_for(instance, self._project_root, self._contract_dir)

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
