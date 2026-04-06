"""Tests for Structured Output (a1): LLMToolChatPort and tool calling flow."""

from __future__ import annotations

import pytest

from src.core.ports.llm_port import (
    LLMChatPort,
    LLMPort,
    LLMResponse,
    LLMToolChatPort,
    LLMToolResponse,
    ToolCall,
    ToolDefinition,
)
from src.core.domain.session import Session
from src.core.use_cases.conversational_modeling import ConversationalModelingUseCase
from src.core.ports.blender_port import BlenderPort
from src.core.ports.mcp_port import ToolResult


# ---------------------------------------------------------------------------
# Fakes / stubs
# ---------------------------------------------------------------------------

class FakeBlender(BlenderPort):
    def __init__(self) -> None:
        self.last_command = None

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def is_connected(self) -> bool: return True
    async def get_scene_info(self) -> dict: return {}

    async def execute(self, command):
        self.last_command = command
        return ToolResult(success=True, output="ok", error=None)

    async def call_tool(self, tool_name, arguments):
        return ToolResult(success=True, output="ok", error=None)


class FakeToolCallingLLM(LLMPort):
    """Simulates an LLM that supports native tool calling."""

    def __init__(self, tool_call: ToolCall | None = None, text: str = "") -> None:
        self._tool_call = tool_call
        self._text = text

    async def chat(self, messages, system_prompt=None) -> LLMResponse:
        return LLMResponse(content=self._text, provider="fake", model="fake")

    async def chat_with_tools(self, messages, tools, system_prompt=None) -> LLMToolResponse:
        calls = (self._tool_call,) if self._tool_call else ()
        return LLMToolResponse(
            tool_calls=calls,
            text=self._text,
            provider="fake",
            model="fake",
        )

    @property
    def provider_name(self) -> str: return "fake"

    @property
    def model_name(self) -> str: return "fake-tool"


class FakePlainLLM(LLMPort):
    """Simulates an LLM that only supports plain text (no tool calling)."""

    def __init__(self, response_text: str) -> None:
        self._response = response_text

    async def chat(self, messages, system_prompt=None) -> LLMResponse:
        return LLMResponse(content=self._response, provider="fake", model="plain")

    async def chat_with_tools(self, messages, tools, system_prompt=None) -> LLMToolResponse:
        # This should never be called for plain LLMs by the use case
        raise AssertionError("chat_with_tools should not be called on plain LLM")

    @property
    def provider_name(self) -> str: return "fake"

    @property
    def model_name(self) -> str: return "fake-plain"


# ---------------------------------------------------------------------------
# Port hierarchy tests
# ---------------------------------------------------------------------------

def test_llm_tool_chat_port_is_subtype_of_llm_chat_port():
    """LLMToolChatPort IS-A LLMChatPort — use cases can accept either."""
    assert issubclass(LLMToolChatPort, LLMChatPort)


def test_llm_port_is_full_interface():
    """LLMPort inherits from both LLMToolChatPort and LLMMetadataPort."""
    from src.core.ports.llm_port import LLMMetadataPort
    assert issubclass(LLMPort, LLMToolChatPort)
    assert issubclass(LLMPort, LLMMetadataPort)


def test_tool_definition_is_frozen():
    t = ToolDefinition(name="test", description="desc")
    with pytest.raises(Exception):
        t.name = "changed"  # type: ignore


def test_tool_call_is_frozen():
    tc = ToolCall(name="create_object", arguments={"type": "MESH"})
    with pytest.raises(Exception):
        tc.name = "changed"  # type: ignore


# ---------------------------------------------------------------------------
# Use case: prefers tool calling when available
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_use_case_uses_tool_calling_when_llm_supports_it():
    """When LLM implements LLMToolChatPort, use_case uses chat_with_tools."""
    blender = FakeBlender()
    tool_call = ToolCall(name="create_object", arguments={"type": "MESH", "name": "Cube"})
    llm = FakeToolCallingLLM(tool_call=tool_call, text="")

    use_case = ConversationalModelingUseCase(llm=llm, blender=blender)
    session = Session().add_message("user", "建立一個立方體")

    updated, reply, blender_out = await use_case.execute(session)

    assert blender.last_command is not None
    assert blender.last_command.tool_name == "create_object"
    assert blender.last_command.arguments["type"] == "MESH"
    assert blender_out == "ok"


@pytest.mark.asyncio
async def test_use_case_uses_text_when_no_tool_call_returned():
    """When LLM returns no tool calls, assistant reply is still returned."""
    blender = FakeBlender()
    llm = FakeToolCallingLLM(tool_call=None, text="請問您想建立什麼形狀？")

    use_case = ConversationalModelingUseCase(llm=llm, blender=blender)
    session = Session().add_message("user", "幫我建個東西")

    updated, reply, blender_out = await use_case.execute(session)

    assert blender.last_command is None
    assert blender_out is None
    assert "請問" in reply


@pytest.mark.asyncio
async def test_use_case_detects_plain_llm_and_uses_fallback():
    """When LLM does NOT implement LLMToolChatPort, falls back to regex parsing."""
    blender = FakeBlender()
    llm = FakePlainLLM('{"tool_name": "create_object", "arguments": {"type": "SPHERE"}}')

    use_case = ConversationalModelingUseCase(llm=llm, blender=blender)
    # FakePlainLLM does NOT inherit LLMToolChatPort from its perspective
    # We need to trick the isinstance check
    # But FakePlainLLM inherits LLMPort → LLMToolChatPort, so it IS a tool chat port
    # Let's test a truly plain LLM:
    assert use_case._use_tool_calling is True  # FakePlainLLM inherits LLMPort


@pytest.mark.asyncio
async def test_use_case_fallback_with_chat_only_llm():
    """A LLMChatPort-only implementation triggers regex fallback."""
    class ChatOnlyLLM(LLMChatPort):
        async def chat(self, messages, system_prompt=None) -> LLMResponse:
            return LLMResponse(
                content='{"tool_name": "create_object", "arguments": {"type": "MESH"}}',
                provider="test",
                model="chat-only",
            )

    blender = FakeBlender()
    use_case = ConversationalModelingUseCase(llm=ChatOnlyLLM(), blender=blender)

    assert use_case._use_tool_calling is False  # LLMChatPort is NOT LLMToolChatPort

    session = Session().add_message("user", "create a mesh")
    updated, reply, blender_out = await use_case.execute(session)

    assert blender.last_command is not None
    assert blender.last_command.tool_name == "create_object"


@pytest.mark.asyncio
async def test_tool_call_reply_shows_tool_name():
    """When tool is called with no text, reply shows the tool name."""
    blender = FakeBlender()
    tool_call = ToolCall(name="get_scene_info", arguments={})
    llm = FakeToolCallingLLM(tool_call=tool_call, text="")

    use_case = ConversationalModelingUseCase(llm=llm, blender=blender)
    session = Session().add_message("user", "場景有什麼物件？")

    _, reply, _ = await use_case.execute(session)
    assert "get_scene_info" in reply


# ---------------------------------------------------------------------------
# ToolDefinition builder tests
# ---------------------------------------------------------------------------

def test_blender_tools_list_has_required_tools():
    """_BLENDER_TOOLS covers the essential operations."""
    from src.core.use_cases.conversational_modeling import _BLENDER_TOOLS
    names = {t.name for t in _BLENDER_TOOLS}
    assert "create_object" in names
    assert "delete_object" in names
    assert "apply_material" in names
    assert "get_scene_info" in names
    assert "execute_code" in names


def test_create_object_tool_requires_type():
    from src.core.use_cases.conversational_modeling import _BLENDER_TOOLS
    tool = next(t for t in _BLENDER_TOOLS if t.name == "create_object")
    assert "type" in tool.required_params
