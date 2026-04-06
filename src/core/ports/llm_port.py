"""LLM Port — abstract interface for all LLM providers.

ISP (Interface Segregation):
  - LLMChatPort: minimal interface, only chat(). Use cases depend on this.
  - LLMMetadataPort: provider/model identity, for logging/monitoring.
  - LLMPort: full interface for adapters to implement (both).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.core.domain.session import Message


@dataclass(frozen=True)
class LLMResponse:
    content: str
    provider: str
    model: str
    finish_reason: str = "stop"


class LLMChatPort(ABC):
    """Minimal interface for LLM chat — use cases depend only on this."""

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Send messages to the LLM and return a response."""


class LLMMetadataPort(ABC):
    """Provider/model identity — used by factories and logging."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g. 'anthropic')."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier (e.g. 'claude-3-5-sonnet-20241022')."""


class LLMPort(LLMChatPort, LLMMetadataPort):
    """Full LLM interface — all adapters implement this."""
