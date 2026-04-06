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

import json

import httpx

from src.core.domain.session import Message
from src.core.ports.llm_port import LLMPort, LLMResponse
from src.infrastructure.env_loader import load_env


class OllamaAdapter(LLMPort):
    """Local Ollama LLM adapter — zero API cost."""

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

        # qwen3 models emit <think>...</think> blocks — strip them for clean output
        content = self._strip_thinking(content)

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=self.model_name,
            finish_reason=data.get("done_reason", "stop"),
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
    def _strip_thinking(text: str) -> str:
        """Remove <think>...</think> chain-of-thought blocks from qwen3/deepseek-r1."""
        import re
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model
