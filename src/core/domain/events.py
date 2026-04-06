"""Domain Events — immutable records of significant business occurrences.

Events are published by use cases (not domain entities, to keep entities pure).
Subscribers handle cross-cutting concerns: logging, monitoring, webhooks, etc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events."""
    occurred_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class SessionCreatedEvent(DomainEvent):
    session_id: str = ""
    workflow: str = ""


@dataclass(frozen=True)
class MessageAddedEvent(DomainEvent):
    session_id: str = ""
    role: str = ""  # "user" | "assistant"
    content_preview: str = ""  # first 120 chars


@dataclass(frozen=True)
class CommandExecutedEvent(DomainEvent):
    session_id: str = ""
    tool_name: str = ""
    arguments: str = ""   # JSON string — avoid mutable dict in frozen dataclass
    output_preview: str = ""


@dataclass(frozen=True)
class CommandFailedEvent(DomainEvent):
    session_id: str = ""
    tool_name: str = ""
    error: str = ""


@dataclass(frozen=True)
class LLMCalledEvent(DomainEvent):
    session_id: str = ""
    provider: str = ""
    model: str = ""
    message_count: int = 0
