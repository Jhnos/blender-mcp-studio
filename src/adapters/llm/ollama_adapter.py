"""Ollama local LLM adapter implementing LLMPort.

Connects to the local Ollama server (default http://localhost:11434).
Supports any model available in the local Ollama installation.
All configuration is injectable via constructor or os.environ.

Recommended models for Blender bpy code generation:
- qwen3-coder:480b-cloud (cloud, zero local memory)
- qwen3-coder:30b  (best local coding quality, 17GB)
- deepseek-r1:32b  (strong reasoning, 18GB)
- gemma4:26b       (MoE, only 4B active params, very fast)
"""

from __future__ import annotations

import re

import httpx

from src.core.domain.session import Message
from src.core.ports.llm_port import (
    LLMPort,
    LLMResponse,
    LLMToolResponse,
    ToolCall,
    ToolDefinition,
)


class OllamaAdapter(LLMPort):
    """Local Ollama LLM adapter — zero API cost.

    Implements LLMToolChatPort via OpenAI-compatible /api/chat tools parameter.
    Models that support function calling (qwen3-coder, llama3.1+) will return
    structured tool_calls; others fall back to text mode gracefully.
    """

    DEFAULT_MODEL = "qwen3-coder:30b"
    DEFAULT_BASE_URL = "http://localhost:11434"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 300.0,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def chat(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        payload: dict[str, object] = {
            "model": self._model,
            "stream": False,
            "messages": self._build_messages(messages, system_prompt),
            "options": {"temperature": 0.3},
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        content: str = data["message"]["content"]
        content = self._strip_thinking(content)

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=self.model_name,
            finish_reason=data.get("done_reason", "stop"),
        )

    async def chat_with_tools(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        system_prompt: str | None = None,
    ) -> LLMToolResponse:
        """Use OpenAI-compatible tools format for structured output."""
        openai_tools = [self._to_openai_tool(t) for t in tools]
        payload: dict[str, object] = {
            "model": self._model,
            "stream": False,
            "messages": self._build_messages(messages, system_prompt),
            "tools": openai_tools,
            "options": {"temperature": 0.1},  # lower temp for structured calls
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        message = data.get("message", {})
        raw_tool_calls = message.get("tool_calls") or []
        tool_calls: list[ToolCall] = []
        for tc in raw_tool_calls:
            fn = tc.get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):
                import json
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            tool_calls.append(
                ToolCall(
                    name=fn.get("name", ""),
                    arguments=dict(args),
                    call_id=tc.get("id", ""),
                )
            )

        text = self._strip_thinking(message.get("content") or "")
        return LLMToolResponse(
            tool_calls=tuple(tool_calls),
            text=text,
            provider=self.provider_name,
            model=self.model_name,
            finish_reason=data.get("done_reason", "tool_calls" if tool_calls else "stop"),
        )

    def _build_messages(
        self, messages: list[Message], system_prompt: str | None
    ) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})
        for m in messages:
            if m.role in ("user", "assistant"):
                result.append({"role": m.role, "content": m.content})
        return result

    @staticmethod
    def _to_openai_tool(t: ToolDefinition) -> dict[str, object]:
        return {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": {
                    "type": "object",
                    "properties": t.parameters,
                    "required": list(t.required_params),
                },
            },
        }

    @staticmethod
    def _strip_thinking(text: str) -> str:
        """Remove <think>...</think> chain-of-thought blocks from qwen3/deepseek-r1."""
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model
