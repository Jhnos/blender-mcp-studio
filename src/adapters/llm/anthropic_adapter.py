"""Anthropic (Claude) adapter implementing LLMPort.

All configuration injected via constructor or os.environ:
  ANTHROPIC_API_KEY  (required)
  ANTHROPIC_MODEL    (optional, default: claude-3-5-sonnet-20241022)
  ANTHROPIC_MAX_TOKENS (optional, default: 4096)
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Iterable

import anthropic
from anthropic.types import ContentBlock, MessageParam, ToolParam
from anthropic.types.message_create_params import (
    MessageCreateParamsBase,
    MessageCreateParamsNonStreaming,
)

from src.core.domain.session import Message
from src.core.ports.llm_port import (
    LLMPort,
    LLMResponse,
    LLMToolResponse,
    ToolCall,
    ToolDefinition,
)


def _to_sdk_messages(messages: list[Message]) -> list[MessageParam]:
    """Project domain messages onto the SDK shape.

    The literal per branch is what lets these satisfy MessageParam's
    `role: Literal["user", "assistant"]` — `m.role` is a plain `str`, so passing
    it through would not narrow.
    """
    return [
        {"role": "user" if m.role == "user" else "assistant", "content": m.content}
        for m in messages
        if m.role in ("user", "assistant")
    ]


def _first_text(blocks: Iterable[ContentBlock]) -> str:
    """Return the first text block's text, or "" if the reply carries none.

    `content[0]` is not necessarily text — with extended thinking enabled the
    first block is a ThinkingBlock, which has no `.text`. Same rule as
    claude_vision_adapter and the tool-calling branch below.
    """
    return next((b.text for b in blocks if b.type == "text"), "")


class AnthropicAdapter(LLMPort):
    """Claude LLM adapter via the official Anthropic SDK.

    Implements LLMToolChatPort — uses native Claude tool_use for structured output,
    eliminating regex-based JSON parsing.
    """

    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
    DEFAULT_MAX_TOKENS = 4096

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        api_key: str = "",
    ) -> None:
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for AnthropicAdapter")
        self._model = model
        self._max_tokens = max_tokens
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def chat(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        kwargs: MessageCreateParamsNonStreaming = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": _to_sdk_messages(messages),
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = await self._client.messages.create(**kwargs)
        return LLMResponse(
            content=_first_text(response.content),
            provider=self.provider_name,
            model=self.model_name,
            finish_reason=response.stop_reason or "stop",
        )

    async def astream(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens via the Anthropic streaming API."""
        # MessageCreateParamsBase, not ...NonStreaming: the latter carries a
        # `stream` key that .stream() rejects as an extra argument.
        kwargs: MessageCreateParamsBase = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": _to_sdk_messages(messages),
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text

    async def chat_with_tools(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        system_prompt: str | None = None,
    ) -> LLMToolResponse:
        """Use Claude's native tool_use for structured output — no regex needed."""
        kwargs: MessageCreateParamsNonStreaming = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": _to_sdk_messages(messages),
            "tools": [self._to_anthropic_tool(t) for t in tools],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = await self._client.messages.create(**kwargs)

        tool_calls: list[ToolCall] = []
        text_parts: list[str] = []

        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        name=block.name,
                        arguments=dict(block.input),
                        call_id=block.id,
                    )
                )
            elif block.type == "text":
                text_parts.append(block.text)

        return LLMToolResponse(
            tool_calls=tuple(tool_calls),
            text=" ".join(text_parts),
            provider=self.provider_name,
            model=self.model_name,
            finish_reason=response.stop_reason or "tool_use",
        )

    @staticmethod
    def _to_anthropic_tool(t: ToolDefinition) -> ToolParam:
        return {
            "name": t.name,
            "description": t.description,
            "input_schema": {
                "type": "object",
                "properties": t.parameters,
                "required": list(t.required_params),
            },
        }

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model
