"""Anthropic (Claude) adapter implementing LLMPort.

All configuration injected via constructor or os.environ:
  ANTHROPIC_API_KEY  (required)
  ANTHROPIC_MODEL    (optional, default: claude-3-5-sonnet-20241022)
  ANTHROPIC_MAX_TOKENS (optional, default: 4096)
"""

from __future__ import annotations

import anthropic

from src.core.domain.session import Message
from src.core.ports.llm_port import LLMPort, LLMResponse


class AnthropicAdapter(LLMPort):
    """Claude LLM adapter via the official Anthropic SDK."""

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

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model
