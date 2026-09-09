"""Application service that turns a slug into a built instance.

The registry is the only input surface. This service resolves the slug to a
`HandInstance` and hands the whole entry to the builder; a slug that does not
resolve never reaches an adapter at all.
"""

from __future__ import annotations

from src.core.domain.exceptions import MechanicalGenerationError, UnknownInstanceError
from src.core.domain.hand_instances import HAND_INSTANCES
from src.core.domain.mechanical_generation import InstanceBuild, InstanceSummary
from src.core.ports.mechanical_generation_port import InstanceBuilderPort


class MechanicalGenerationService:
    def __init__(self, builder: InstanceBuilderPort) -> None:
        self._builder = builder

    async def list_instances(self) -> tuple[InstanceSummary, ...]:
        return tuple(
            InstanceSummary(
                slug=instance.slug,
                family=instance.family,
                declared_parts=instance.stl_files,
                output_dir=instance.output_dir,
            )
            for instance in HAND_INSTANCES.values()
        )

    async def build(self, slug: str) -> InstanceBuild:
        instance = HAND_INSTANCES.get(slug)
        if instance is None:
            raise UnknownInstanceError(f"{slug!r} is not a registered instance")
        build = await self._builder.build_instance(instance)
        if build.part_names != instance.stl_files:
            raise MechanicalGenerationError(
                f"{slug} declares {instance.stl_files} but the build produced {build.part_names}"
            )
        return build
