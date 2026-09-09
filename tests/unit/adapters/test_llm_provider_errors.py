"""LLM adapters translate their provider's failures at the boundary.

Same class as D-002: an unreachable provider is `LLMConnectionError` (503), a
provider that answered with a failure is `LLMProviderError` (502). Neither
httpx nor the Anthropic SDK's exception types may escape an adapter, because
the use case above it would otherwise have to guess — which is what its own
blanket `except Exception` used to do, collapsing every failure into "LLM
chat failed".
"""

from __future__ import annotations

import anthropic
import httpx
import pytest

from src.adapters.llm.anthropic_adapter import AnthropicAdapter
from src.adapters.llm.ollama_adapter import OllamaAdapter
from src.core.domain.exceptions import (
    ExternalServiceError,
    LLMConnectionError,
    LLMProviderError,
)
from src.core.domain.session import Message

MESSAGES = [Message(role="user", content="a cube")]
OLLAMA = "http://localhost:11434"


def test_a_provider_failure_is_an_external_service_error() -> None:
    assert issubclass(LLMProviderError, ExternalServiceError)
    assert not issubclass(LLMConnectionError, ExternalServiceError)


# ---------------------------------------------------------------- Ollama


@pytest.mark.asyncio
async def test_ollama_http_error_is_a_provider_error(respx_mock) -> None:
    respx_mock.post(f"{OLLAMA}/api/chat").mock(return_value=httpx.Response(500, text="boom"))
    adapter = OllamaAdapter(base_url=OLLAMA, model="x")

    with pytest.raises(LLMProviderError) as caught:
        await adapter.chat(MESSAGES)
    assert isinstance(caught.value.__cause__, httpx.HTTPStatusError)


@pytest.mark.asyncio
async def test_ollama_unreachable_is_a_connection_error(respx_mock) -> None:
    respx_mock.post(f"{OLLAMA}/api/chat").mock(side_effect=httpx.ConnectError("refused"))
    adapter = OllamaAdapter(base_url=OLLAMA, model="x")

    with pytest.raises(LLMConnectionError):
        await adapter.chat(MESSAGES)


@pytest.mark.asyncio
async def test_ollama_stream_and_tool_paths_translate_too(respx_mock) -> None:
    respx_mock.post(f"{OLLAMA}/api/chat").mock(return_value=httpx.Response(503, text="busy"))
    adapter = OllamaAdapter(base_url=OLLAMA, model="x")

    with pytest.raises(LLMProviderError):
        async for _ in adapter.astream(MESSAGES):
            pass
    with pytest.raises(LLMProviderError):
        await adapter.chat_with_tools(MESSAGES, tools=[])


# ------------------------------------------------------------- Anthropic


class _Messages:
    def __init__(self, error: Exception) -> None:
        self._error = error

    async def create(self, **kwargs: object) -> object:
        raise self._error

    def stream(self, **kwargs: object) -> object:
        raise self._error


class _Client:
    def __init__(self, error: Exception) -> None:
        self.messages = _Messages(error)


def _adapter_failing_with(error: Exception) -> AnthropicAdapter:
    adapter = AnthropicAdapter(api_key="test-key")
    adapter._client = _Client(error)  # type: ignore[assignment]  # inject the failing SDK client
    return adapter


def _status_error(status: int) -> anthropic.APIStatusError:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.APIStatusError(
        "overloaded", response=httpx.Response(status, request=request), body=None
    )


@pytest.mark.asyncio
async def test_anthropic_status_error_is_a_provider_error() -> None:
    adapter = _adapter_failing_with(_status_error(529))

    with pytest.raises(LLMProviderError) as caught:
        await adapter.chat(MESSAGES)
    assert isinstance(caught.value.__cause__, anthropic.APIStatusError)


@pytest.mark.asyncio
async def test_anthropic_connection_error_is_a_connection_error() -> None:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    adapter = _adapter_failing_with(anthropic.APIConnectionError(request=request))

    with pytest.raises(LLMConnectionError):
        await adapter.chat_with_tools(MESSAGES, tools=[])


@pytest.mark.asyncio
async def test_anthropic_stream_path_translates_too() -> None:
    adapter = _adapter_failing_with(_status_error(500))

    with pytest.raises(LLMProviderError):
        async for _ in adapter.astream(MESSAGES):
            pass
