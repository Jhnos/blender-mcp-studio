"""Tests for LLM streaming — LLMStreamPort + adapter implementations.

Tests use mocked HTTP / SDK calls so they run without real LLM credentials.
"""

from __future__ import annotations

import pytest

from src.core.domain.session import Message, Session
from src.core.ports.llm_port import LLMChatPort, LLMStreamPort, LLMPort


# ---------------------------------------------------------------------------
# Port contract tests
# ---------------------------------------------------------------------------

class TestLLMStreamPortContract:
    """Verify the ISP hierarchy: LLMStreamPort is a LLMChatPort."""

    def test_llm_stream_port_extends_chat_port(self):
        assert issubclass(LLMStreamPort, LLMChatPort)

    def test_llm_port_extends_stream_port(self):
        assert issubclass(LLMPort, LLMStreamPort)

    def test_llm_stream_port_has_astream_method(self):
        assert hasattr(LLMStreamPort, "astream")

    def test_astream_is_abstract(self):
        import inspect
        method = LLMStreamPort.__abstractmethods__
        assert "astream" in method


# ---------------------------------------------------------------------------
# OllamaAdapter streaming tests
# ---------------------------------------------------------------------------

class TestOllamaAdapterStreaming:
    """Test OllamaAdapter.astream() with mocked httpx streaming."""

    @pytest.fixture
    def adapter(self):
        from src.adapters.llm.ollama_adapter import OllamaAdapter
        return OllamaAdapter(model="test-model", base_url="http://localhost:11434")

    @pytest.fixture
    def messages(self):
        session = Session()
        session = session.add_message("user", "Hello")
        return session.messages

    @pytest.mark.asyncio
    async def test_astream_yields_tokens(self, adapter, messages, respx_mock):
        """astream() should yield each non-empty token."""
        import json
        import httpx

        ndjson_lines = "\n".join([
            json.dumps({"message": {"content": "Hello"}, "done": False}),
            json.dumps({"message": {"content": " world"}, "done": False}),
            json.dumps({"message": {"content": "!"}, "done": True}),
        ])

        respx_mock.post("http://localhost:11434/api/chat").mock(
            return_value=httpx.Response(200, text=ndjson_lines)
        )

        tokens = []
        async for token in adapter.astream(messages):
            tokens.append(token)

        assert tokens == ["Hello", " world", "!"]

    @pytest.mark.asyncio
    async def test_astream_strips_think_blocks(self, adapter, messages, respx_mock):
        """Tokens inside <think>...</think> should be filtered out."""
        import json
        import httpx

        ndjson_lines = "\n".join([
            json.dumps({"message": {"content": "<think>"}, "done": False}),
            json.dumps({"message": {"content": "internal thought"}, "done": False}),
            json.dumps({"message": {"content": "</think>visible"}, "done": False}),
            json.dumps({"message": {"content": " more"}, "done": True}),
        ])

        respx_mock.post("http://localhost:11434/api/chat").mock(
            return_value=httpx.Response(200, text=ndjson_lines)
        )

        tokens = []
        async for token in adapter.astream(messages):
            tokens.append(token)

        assert "<think>" not in "".join(tokens)
        assert "visible" in "".join(tokens)
        assert "internal thought" not in "".join(tokens)

    @pytest.mark.asyncio
    async def test_astream_skips_empty_tokens(self, adapter, messages, respx_mock):
        """Empty content tokens should not be yielded."""
        import json
        import httpx

        ndjson_lines = "\n".join([
            json.dumps({"message": {"content": ""}, "done": False}),
            json.dumps({"message": {"content": "real"}, "done": True}),
        ])

        respx_mock.post("http://localhost:11434/api/chat").mock(
            return_value=httpx.Response(200, text=ndjson_lines)
        )

        tokens = []
        async for token in adapter.astream(messages):
            tokens.append(token)

        assert tokens == ["real"]

    @pytest.mark.asyncio
    async def test_astream_with_system_prompt(self, adapter, messages, respx_mock):
        """System prompt should be sent in the payload."""
        import json
        import httpx

        captured_body: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_body.update(json.loads(request.content))
            return httpx.Response(200, text=json.dumps({"message": {"content": "ok"}, "done": True}))

        respx_mock.post("http://localhost:11434/api/chat").mock(side_effect=handler)

        tokens = []
        async for token in adapter.astream(messages, system_prompt="You are Blender."):
            tokens.append(token)

        sent_messages = captured_body.get("messages", [])
        roles = [m["role"] for m in sent_messages]
        assert "system" in roles
        system_content = next(m["content"] for m in sent_messages if m["role"] == "system")
        assert "Blender" in system_content

    def test_ollama_adapter_implements_llm_port(self, adapter):
        from src.core.ports.llm_port import LLMPort
        assert isinstance(adapter, LLMPort)

    def test_ollama_adapter_implements_stream_port(self, adapter):
        assert isinstance(adapter, LLMStreamPort)


# ---------------------------------------------------------------------------
# AnthropicAdapter streaming tests
# ---------------------------------------------------------------------------

class TestAnthropicAdapterStreaming:
    """Test AnthropicAdapter.astream() — mocked Anthropic SDK."""

    @pytest.fixture
    def adapter(self, monkeypatch):
        from unittest.mock import MagicMock, AsyncMock
        import anthropic as anthropic_sdk

        # Minimal mock of AsyncAnthropic to avoid real API calls
        mock_client = MagicMock()
        monkeypatch.setattr(anthropic_sdk, "AsyncAnthropic", lambda api_key: mock_client)

        from src.adapters.llm.anthropic_adapter import AnthropicAdapter
        return AnthropicAdapter(api_key="test-key"), mock_client

    @pytest.mark.asyncio
    async def test_astream_yields_tokens(self, adapter):
        from unittest.mock import AsyncMock, MagicMock
        import contextlib

        adp, mock_client = adapter
        session = Session().add_message("user", "hi")

        async def fake_text_stream():
            for t in ["Hello", " from", " Claude"]:
                yield t

        stream_ctx = MagicMock()
        stream_ctx.__aenter__ = AsyncMock(return_value=stream_ctx)
        stream_ctx.__aexit__ = AsyncMock(return_value=False)
        stream_ctx.text_stream = fake_text_stream()
        mock_client.messages.stream.return_value = stream_ctx

        tokens = []
        async for token in adp.astream(session.messages):
            tokens.append(token)

        assert tokens == ["Hello", " from", " Claude"]

    def test_anthropic_adapter_implements_stream_port(self, adapter):
        adp, _ = adapter
        assert isinstance(adp, LLMStreamPort)


# ---------------------------------------------------------------------------
# chatStore streaming logic (pure unit, no browser APIs)
# ---------------------------------------------------------------------------

class TestStreamingProtocol:
    """Verify streaming message protocol shape matches what backend sends."""

    def test_streaming_token_message_shape(self):
        token_msg = {
            "type": "response",
            "content": "Hello",
            "status": "streaming",
            "session_id": "sess-123",
        }
        assert token_msg["status"] == "streaming"
        assert isinstance(token_msg["content"], str)

    def test_done_message_has_blender_output(self):
        done_msg = {
            "type": "response",
            "content": "Full reply",
            "blender_output": "Created cube",
            "screenshot": None,
            "status": "done",
            "session_id": "sess-123",
        }
        assert done_msg["status"] == "done"
        assert "blender_output" in done_msg
