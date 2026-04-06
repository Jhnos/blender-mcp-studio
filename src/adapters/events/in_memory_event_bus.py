"""InMemoryEventBus — default synchronous event bus for single-process use.

Thread-safe for asyncio; handlers are called sequentially.
For multi-process / async fan-out: replace with Redis Streams or similar.
"""

from __future__ import annotations

import inspect
import logging
from collections import defaultdict

from src.core.domain.events import DomainEvent
from src.core.ports.event_bus_port import EventBusPort, EventHandler

logger = logging.getLogger(__name__)


class InMemoryEventBus(EventBusPort):
    """In-process event bus. Register handlers, then publish events."""

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        handlers = self._handlers.get(type(event), [])
        for handler in handlers:
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("EventBus handler %s raised for %s", handler, event)
