"""Unit tests for ConversationalModelingUseCase with mocked ports."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.events.in_memory_event_bus import InMemoryEventBus
from src.core.domain.events import CommandExecutedEvent, CommandFailedEvent, DomainEvent, MessageAddedEvent
from src.core.domain.session import Session
from src.core.ports.llm_port import LLMResponse
from src.core.ports.mcp_port import ToolResult
from src.core.use_cases.conversational_modeling import ConversationalModelingUseCase


def _make_llm_mock(content: str) -> MagicMock:
    mock = MagicMock()
    mock.chat = AsyncMock(
        return_value=LLMResponse(
            content=content,
            provider="mock",
            model="mock-model",
        )
    )
    mock.provider_name = "mock"
    mock.model_name = "mock-model"
    return mock


def _make_blender_mock(success: bool = True) -> MagicMock:
    mock = MagicMock()
    mock.execute = AsyncMock(return_value=ToolResult(success=success, output="ok"))
    mock.is_connected = AsyncMock(return_value=True)
    return mock


@pytest.mark.asyncio
async def test_execute_returns_llm_reply_when_no_json_command() -> None:
    llm = _make_llm_mock("好的，我來幫你建立場景！")
    blender = _make_blender_mock()
    use_case = ConversationalModelingUseCase(llm=llm, blender=blender)
    session = Session().add_message("user", "你好")

    updated, reply, blender_out = await use_case.execute(session)

    assert reply == "好的，我來幫你建立場景！"
    assert updated.messages[-1].role == "assistant"
    assert blender_out is None
    blender.execute.assert_not_called()


@pytest.mark.asyncio
async def test_execute_calls_blender_when_json_command_found() -> None:
    json_reply = '{"tool_name": "create_object", "arguments": {"type": "CUBE"}}'
    llm = _make_llm_mock(json_reply)
    blender = _make_blender_mock()
    use_case = ConversationalModelingUseCase(llm=llm, blender=blender)
    session = Session().add_message("user", "建立一個立方體")

    _, reply, blender_out = await use_case.execute(session)

    blender.execute.assert_called_once()
    called_cmd = blender.execute.call_args[0][0]
    assert called_cmd.tool_name == "create_object"


@pytest.mark.asyncio
async def test_execute_raises_on_empty_session() -> None:
    from src.core.domain.exceptions import SceneCreationError

    use_case = ConversationalModelingUseCase(
        llm=_make_llm_mock(""), blender=_make_blender_mock()
    )
    with pytest.raises(SceneCreationError):
        await use_case.execute(Session())


@pytest.mark.asyncio
async def test_execute_returns_error_message_on_blender_failure() -> None:
    json_reply = '{"tool_name": "create_object", "arguments": {}}'
    llm = _make_llm_mock(json_reply)
    blender = _make_blender_mock(success=False)
    blender.execute = AsyncMock(
        return_value=ToolResult(success=False, output=None, error="Blender busy")
    )
    use_case = ConversationalModelingUseCase(llm=llm, blender=blender)
    session = Session().add_message("user", "build")

    _, reply, blender_out = await use_case.execute(session)

    assert "❌" in reply or blender_out is not None


@pytest.mark.asyncio
async def test_use_case_publishes_message_added_event() -> None:
    bus = InMemoryEventBus()
    events: list[DomainEvent] = []
    bus.subscribe(MessageAddedEvent, lambda e: events.append(e))

    llm = _make_llm_mock("好的！")
    use_case = ConversationalModelingUseCase(llm=llm, blender=_make_blender_mock(), event_bus=bus)
    session = Session().add_message("user", "你好")
    await use_case.execute(session)

    msg_events = [e for e in events if isinstance(e, MessageAddedEvent)]
    assert any(e.role == "user" for e in msg_events)
    assert any(e.role == "assistant" for e in msg_events)


@pytest.mark.asyncio
async def test_use_case_publishes_command_executed_event() -> None:
    bus = InMemoryEventBus()
    events: list[DomainEvent] = []
    bus.subscribe(CommandExecutedEvent, lambda e: events.append(e))

    json_reply = '{"tool_name": "get_scene_info", "arguments": {}}'
    llm = _make_llm_mock(json_reply)
    use_case = ConversationalModelingUseCase(llm=llm, blender=_make_blender_mock(), event_bus=bus)
    session = Session().add_message("user", "show scene")
    await use_case.execute(session)

    assert len(events) == 1
    assert events[0].tool_name == "get_scene_info"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_use_case_publishes_command_failed_event() -> None:
    bus = InMemoryEventBus()
    events: list[DomainEvent] = []
    bus.subscribe(CommandFailedEvent, lambda e: events.append(e))

    json_reply = '{"tool_name": "delete_object", "arguments": {"name": "Cube"}}'
    llm = _make_llm_mock(json_reply)
    blender = _make_blender_mock(success=False)
    blender.execute = AsyncMock(return_value=ToolResult(success=False, output=None, error="not found"))
    use_case = ConversationalModelingUseCase(llm=llm, blender=blender, event_bus=bus)
    session = Session().add_message("user", "delete cube")
    await use_case.execute(session)

    assert len(events) == 1
    assert events[0].error == "not found"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_use_case_works_without_event_bus() -> None:
    """event_bus=None is valid — no events, no crash."""
    use_case = ConversationalModelingUseCase(
        llm=_make_llm_mock("OK"),
        blender=_make_blender_mock(),
        event_bus=None,
    )
    session = Session().add_message("user", "hi")
    updated, reply, _ = await use_case.execute(session)
    assert reply == "OK"

