"""Anthropic (Claude) adapter implementing LLMPort.

All configuration injected via constructor or os.environ:
  ANTHROPIC_API_KEY  (required)
  ANTHROPIC_MODEL    (optional, default: claude-3-5-sonnet-20241022)
  ANTHROPIC_MAX_TOKENS (optional, default: 4096)
"""

from __future__ import annotations

import anthropic

from src.core.domain.session import Message
from src.core.ports.llm_port import (
    LLMPort,
    LLMResponse,
    LLMToolResponse,
    ToolCall,
    ToolDefinition,
)


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
        sdk_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]
        kwargs: dict[str, object] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": sdk_messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = await self._client.messages.create(**kwargs)  # type: ignore[arg-type]
        return LLMResponse(
            content=response.content[0].text,
            provider=self.provider_name,
            model=self.model_name,
            finish_reason=response.stop_reason or "stop",
        )

    async def astream(  # type: ignore[override]
        self,
        messages: list[Message],
        system_prompt: str | None = None,
    ):
        """Stream response tokens via the Anthropic streaming API."""
        sdk_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]
        kwargs: dict[str, object] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": sdk_messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        async with self._client.messages.stream(**kwargs) as stream:  # type: ignore[arg-type]
            async for text in stream.text_stream:
                yield text

    async def chat_with_tools(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        system_prompt: str | None = None,
    ) -> LLMToolResponse:
        """Use Claude's native tool_use for structured output — no regex needed."""
        sdk_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]
        anthropic_tools = [self._to_anthropic_tool(t) for t in tools]

        kwargs: dict[str, object] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": sdk_messages,
            "tools": anthropic_tools,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = await self._client.messages.create(**kwargs)  # type: ignore[arg-type]

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
    def _to_anthropic_tool(t: ToolDefinition) -> dict[str, object]:
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
