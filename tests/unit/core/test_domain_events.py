"""Tests for domain events, EventBusPort, and InMemoryEventBus."""

from __future__ import annotations

import pytest

from src.core.domain.events import (
    CommandExecutedEvent,
    CommandFailedEvent,
    DomainEvent,
    LLMCalledEvent,
    MessageAddedEvent,
    SessionCreatedEvent,
)
from src.adapters.events.in_memory_event_bus import InMemoryEventBus


@pytest.mark.asyncio
async def test_publish_calls_registered_handler() -> None:
    bus = InMemoryEventBus()
    received: list[DomainEvent] = []

    bus.subscribe(MessageAddedEvent, lambda e: received.append(e))
    await bus.publish(MessageAddedEvent(session_id="s1", role="user", content_preview="hi"))

    assert len(received) == 1
    assert isinstance(received[0], MessageAddedEvent)
    assert received[0].session_id == "s1"


@pytest.mark.asyncio
async def test_publish_only_calls_matching_type() -> None:
    bus = InMemoryEventBus()
    received: list[DomainEvent] = []

    bus.subscribe(CommandExecutedEvent, lambda e: received.append(e))
    await bus.publish(MessageAddedEvent(session_id="s2", role="user"))

    assert received == []


@pytest.mark.asyncio
async def test_multiple_handlers_for_same_event() -> None:
    bus = InMemoryEventBus()
    calls: list[str] = []

    bus.subscribe(LLMCalledEvent, lambda e: calls.append("A"))
    bus.subscribe(LLMCalledEvent, lambda e: calls.append("B"))
    await bus.publish(LLMCalledEvent(session_id="s3", provider="ollama", model="qwen3"))

    assert calls == ["A", "B"]


@pytest.mark.asyncio
async def test_async_handler_is_awaited() -> None:
    bus = InMemoryEventBus()
    received: list[DomainEvent] = []

    async def async_handler(e: DomainEvent) -> None:
        received.append(e)

    bus.subscribe(CommandFailedEvent, async_handler)
    await bus.publish(CommandFailedEvent(session_id="s4", tool_name="create_object", error="boom"))

    assert len(received) == 1
    assert received[0].error == "boom"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_handler_exception_does_not_propagate() -> None:
    bus = InMemoryEventBus()

    def bad_handler(e: DomainEvent) -> None:
        raise RuntimeError("I broke")

    bus.subscribe(SessionCreatedEvent, bad_handler)
    # Should NOT raise — bad handlers are logged, not propagated
    await bus.publish(SessionCreatedEvent(session_id="s5", workflow="test"))


def test_events_are_frozen_dataclasses() -> None:
    evt = MessageAddedEvent(session_id="s6", role="user", content_preview="x")
    with pytest.raises((AttributeError, TypeError)):
        evt.role = "assistant"  # type: ignore[misc]
