"""The conversation can reach the project's own generators — and only those.

Before this, the most a conversation could produce was a primitive: a cube, a
light, a camera. Everything in this repository that makes a printable part
lives behind the generators, and the conversation could not see them. These
tests pin the capability and the boundary it must not cross.
"""

from __future__ import annotations

import json

import pytest

from src.core.domain.command import Command
from src.core.domain.exceptions import UnknownInstanceError
from src.core.domain.hand_instances import HAND_INSTANCES
from src.core.domain.mechanical_generation import BuiltPart, InstanceBuild, InstanceSummary
from src.core.ports.mcp_port import ToolResult
from src.core.use_cases.conversation_generation import (
    GENERATION_TOOL_NAMES,
    GENERATION_TOOLS,
)
from src.core.use_cases.conversational_modeling import ConversationalModelingUseCase


class StubGeneration:
    def __init__(self) -> None:
        self.built: list[str] = []

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
        if slug not in HAND_INSTANCES:
            raise UnknownInstanceError(f"{slug!r} is not a registered instance")
        self.built.append(slug)
        return InstanceBuild(
            slug=slug,
            output_dir=f"tmp/{slug}",
            parts=(BuiltPart("palm_mm.stl", 2086, (56.0, 30.0, 80.5)),),
        )


class RecordingBlender:
    def __init__(self) -> None:
        self.commands: list[Command] = []

    async def execute(self, command: Command) -> ToolResult:
        self.commands.append(command)
        return ToolResult(success=True, output="blender", error=None)


class DumbLLM:
    provider_name = "stub"
    model_name = "stub"

    async def chat(self, messages, system_prompt=None):  # noqa: ANN001, ANN201
        raise AssertionError("not used")


def _use_case(generation: StubGeneration | None) -> tuple[ConversationalModelingUseCase, object]:
    blender = RecordingBlender()
    return (
        ConversationalModelingUseCase(
            llm=DumbLLM(),  # type: ignore[arg-type]
            blender=blender,  # type: ignore[arg-type]
            generation=generation,  # type: ignore[arg-type]
        ),
        blender,
    )


def test_the_generation_tools_are_offered_only_when_the_service_is_wired() -> None:
    with_service, _ = _use_case(StubGeneration())
    without, _ = _use_case(None)

    offered = {tool.name for tool in with_service.available_tools("做一隻夾爪")}
    assert offered >= GENERATION_TOOL_NAMES

    assert not {tool.name for tool in without.available_tools("做一隻夾爪")} & GENERATION_TOOL_NAMES


def test_the_generation_tools_survive_the_semantic_router() -> None:
    """The router drops tools whose names do not look like the message. Losing
    the only tool that makes a printable part, because the user wrote 夾爪
    instead of an English verb, would be a silent loss of the capability."""
    use_case, _ = _use_case(StubGeneration())

    for message in ("夾爪", "make me a hand", "", "完全無關的句子"):
        offered = {tool.name for tool in use_case.available_tools(message)}
        assert offered >= GENERATION_TOOL_NAMES, message


def test_the_offered_slugs_are_exactly_the_registry() -> None:
    build = next(tool for tool in GENERATION_TOOLS if tool.name == "build_instance")

    assert build.parameters["slug"]["enum"] == sorted(HAND_INSTANCES)  # type: ignore[index]


@pytest.mark.asyncio
async def test_a_generation_tool_goes_to_the_generator_not_to_blender() -> None:
    generation = StubGeneration()
    use_case, blender = _use_case(generation)

    result = await use_case._dispatch(
        Command(tool_name="build_instance", arguments={"slug": "hand-gripper"})
    )

    assert result.success
    assert generation.built == ["hand-gripper"]
    assert blender.commands == []  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_every_other_tool_still_goes_to_blender() -> None:
    generation = StubGeneration()
    use_case, blender = _use_case(generation)

    await use_case._dispatch(Command(tool_name="create_object", arguments={"type": "MESH"}))

    assert generation.built == []
    assert [command.tool_name for command in blender.commands] == ["create_object"]  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_listing_answers_with_every_registered_instance() -> None:
    use_case, _ = _use_case(StubGeneration())

    result = await use_case._dispatch(Command(tool_name="list_instances", arguments={}))

    assert result.success
    listed = {entry["slug"] for entry in json.loads(str(result.output))}
    assert listed == set(HAND_INSTANCES)


@pytest.mark.asyncio
async def test_an_unregistered_slug_answers_in_the_turn_instead_of_raising() -> None:
    """A raised turn loses the assistant's reply with it. The user asked for a
    hand that does not exist; say so, in the same turn."""
    use_case, _ = _use_case(StubGeneration())

    result = await use_case._dispatch(
        Command(tool_name="build_instance", arguments={"slug": "hand-v4"})
    )

    assert not result.success
    assert "hand-v4" in str(result.error)


@pytest.mark.asyncio
async def test_a_generation_tool_without_a_service_is_refused_not_sent_to_blender() -> None:
    use_case, blender = _use_case(None)

    result = await use_case._dispatch(
        Command(tool_name="build_instance", arguments={"slug": "hand-gripper"})
    )

    assert not result.success
    assert blender.commands == []  # type: ignore[attr-defined]
