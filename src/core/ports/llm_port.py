"""LLM Port — abstract interface for all LLM providers.

ISP (Interface Segregation):
  - LLMChatPort: minimal interface, only chat(). Use cases depend on this.
  - LLMToolChatPort(LLMChatPort): structured output via tool/function calling.
  - LLMMetadataPort: provider/model identity, for logging/monitoring.
  - LLMPort: full interface for adapters to implement (all three).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.core.domain.session import Message


@dataclass(frozen=True)
class LLMResponse:
    content: str
    provider: str
    model: str
    finish_reason: str = "stop"


# ---------------------------------------------------------------------------
# Structured Output / Tool Calling types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ToolDefinition:
    """Declarative schema for a single callable tool (JSON Schema style)."""

    name: str
    description: str
    parameters: dict[str, object] = field(default_factory=dict)
    required_params: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ToolCall:
    """A single tool invocation returned by the LLM."""

    name: str
    arguments: dict[str, object]
    call_id: str = ""


@dataclass(frozen=True)
class LLMToolResponse:
    """Response from chat_with_tools — may include tool calls and/or free text."""

    tool_calls: tuple[ToolCall, ...]
    text: str
    provider: str
    model: str
    finish_reason: str = "tool_use"


# ---------------------------------------------------------------------------
# Port interfaces
# ---------------------------------------------------------------------------

class LLMChatPort(ABC):
    """Minimal interface for LLM chat — use cases depend only on this."""

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Send messages to the LLM and return a response."""


class LLMToolChatPort(LLMChatPort):
    """Extended interface supporting structured tool/function calling.

    Use cases check isinstance(llm, LLMToolChatPort) and prefer this path
    for reliable command extraction without regex parsing.
    """

    @abstractmethod
    async def chat_with_tools(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        system_prompt: str | None = None,
    ) -> LLMToolResponse:
        """Send messages with tool definitions, receive structured tool calls."""


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


class LLMPort(LLMToolChatPort, LLMMetadataPort):
    """Full LLM interface — all adapters implement this."""
