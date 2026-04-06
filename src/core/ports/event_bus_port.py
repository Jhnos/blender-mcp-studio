"""EventBus Port — abstract interface for publishing domain events.

Use cases call publish(). Infrastructure decides how to route/store events.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from src.core.domain.events import DomainEvent

EventHandler = Callable[[DomainEvent], Awaitable[None] | None]


class EventBusPort(ABC):
    """Abstract event bus — publish domain events, subscribe handlers."""

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to all registered subscribers."""

    @abstractmethod
    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
