"""The generation service: the registry is the input surface, and the claim is checked."""

from __future__ import annotations

import pytest

from src.core.domain.exceptions import MechanicalGenerationError, UnknownInstanceError
from src.core.domain.hand_instances import HAND_INSTANCES, HandInstance
from src.core.domain.mechanical_generation import BuiltPart, InstanceBuild
from src.core.use_cases.mechanical_generation import MechanicalGenerationService


class StubBuilder:
    def __init__(self, names: tuple[str, ...] | None = None) -> None:
        self.names = names
        self.seen: list[HandInstance] = []

    async def build_instance(self, instance: HandInstance) -> InstanceBuild:
        self.seen.append(instance)
        names = self.names if self.names is not None else instance.stl_files
        return InstanceBuild(
            slug=instance.slug,
            output_dir=instance.output_dir,
            parts=tuple(BuiltPart(name, 100, (1.0, 2.0, 3.0)) for name in names),
        )


@pytest.mark.asyncio
async def test_the_builder_receives_the_resolved_entry_not_the_slug() -> None:
    """The adapter must not look anything up; if it did, the registry would stop
    being the only input surface."""
    builder = StubBuilder()

    await MechanicalGenerationService(builder).build("hand-compact")

    assert builder.seen == [HAND_INSTANCES["hand-compact"]]


@pytest.mark.asyncio
async def test_an_unregistered_slug_never_reaches_the_builder() -> None:
    builder = StubBuilder()

    with pytest.raises(UnknownInstanceError):
        await MechanicalGenerationService(builder).build("hand-v4")

    assert builder.seen == []


@pytest.mark.asyncio
async def test_a_part_list_that_contradicts_the_registry_is_an_error() -> None:
    builder = StubBuilder(names=("palm_mm.stl",))

    with pytest.raises(MechanicalGenerationError, match="declares"):
        await MechanicalGenerationService(builder).build("hand-compact")


@pytest.mark.asyncio
async def test_part_order_is_part_of_the_claim() -> None:
    """Base part first is what the manifest, the README and the package tests all
    read; a reordered list is a different package, not the same one shuffled."""
    instance = HAND_INSTANCES["hand-compact"]
    builder = StubBuilder(names=tuple(reversed(instance.stl_files)))

    with pytest.raises(MechanicalGenerationError):
        await MechanicalGenerationService(builder).build("hand-compact")


@pytest.mark.asyncio
async def test_the_catalog_reports_every_registered_instance_with_its_claim() -> None:
    summaries = await MechanicalGenerationService(StubBuilder()).list_instances()

    assert {summary.slug for summary in summaries} == set(HAND_INSTANCES)
    for summary in summaries:
        assert summary.declared_parts == HAND_INSTANCES[summary.slug].stl_files
