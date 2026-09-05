"""Smoke test for the /ws/chat WebSocket entry point.

Drives the *real* route through a real ASGI WebSocket connection — the only
layer that exercises FastAPI's dependency injection, the `request = websocket`
alias, and JSON framing end to end. Unit tests call `_handle_streaming`
directly and therefore cannot catch a regression in the route wiring itself.

Two lessons converge here (docs/LESSONS_LEARNED.md):
  * 2026-07-15 "entry point declares a dependency the runtime won't inject" — a
    WS route needs a connect->send->don't-crash test, not human validation.
    Declaring `request: Request` on this route once crashed every connection;
    only a real connection surfaces that.
  * 2026-07-17 chat.py:201 — a dict Blender output aborted the whole streaming
    turn. The discriminating assertion below is that a dict output still
    reaches status "done", not "error".

Dependencies are fakes; the route, _handle_streaming, and serialization are real.
"""

from __future__ import annotations

import json

from fastapi import FastAPI
from starlette.testclient import TestClient

from api.routers import chat
from src.adapters.events.in_memory_event_bus import InMemoryEventBus
from src.core.domain.command import Command
from src.core.ports.adapter_factory_port import AdapterFactoryPort
from src.core.ports.blender_port import BlenderPort
from src.core.ports.llm_port import LLMChatPort, LLMResponse, LLMStreamPort
from src.core.ports.mcp_port import ToolResult
from src.core.use_cases.conversational_modeling import ConversationalModelingUseCase

# A command block the LLM "emits" so the streaming path runs a Blender call.
_COMMAND_JSON = '{"tool_name": "create_object", "arguments": {"type": "CUBE"}}'


class _FakeStreamLLM(LLMStreamPort):
    """Streams a canned reply. Not a LLMToolChatPort, so the route streams."""

    async def chat(self, messages, system_prompt=None) -> LLMResponse:  # pragma: no cover
        return LLMResponse(content="", provider="fake", model="fake")

    async def astream(self, messages, system_prompt=None):
        yield "Making "
        yield "a cube. "
        yield _COMMAND_JSON


class _FakeBlender(BlenderPort):
    """execute() returns whatever output shape the test injects."""

    def __init__(self, output: object) -> None:
        self._output = output

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...

    async def execute(self, command: Command) -> ToolResult:
        return ToolResult(success=True, output=self._output, error=None)

    async def call_tool(self, tool_name: str, arguments: dict[str, object]) -> ToolResult:
        # Screenshot capture calls this; a failure keeps the test off the filesystem.
        return ToolResult(success=False, output=None, error="no screenshot in smoke test")

    async def get_scene_info(self) -> dict[str, object]:  # pragma: no cover
        return {}

    async def is_connected(self) -> bool:
        return True


class _FakeFactory(AdapterFactoryPort):
    def __init__(self, llm: LLMChatPort) -> None:
        self._llm = llm

    def build_llm_adapter(self, provider: str | None = None) -> LLMChatPort:
        return self._llm

    def build_blender_adapter(
        self, host: str | None = None, port: int | None = None
    ) -> BlenderPort:  # pragma: no cover - streaming path uses app.state.blender
        raise NotImplementedError


def _make_client(blender_output: object) -> TestClient:
    app = FastAPI()
    app.include_router(chat.router)
    blender = _FakeBlender(blender_output)
    llm = _FakeStreamLLM()
    event_bus = InMemoryEventBus()
    app.state.blender = blender
    app.state.adapter_factory = _FakeFactory(llm)
    app.state.event_bus = event_bus
    # The use case is assembled by the composition root in production
    # (api/runtime.py); this mirrors that wiring with fake adapters so the route
    # under test reads it the same way it does at runtime.
    app.state.conversational_modeling = ConversationalModelingUseCase(
        llm=llm,
        blender=blender,
        event_bus=event_bus,
        prompt_builder=None,
    )
    # sanitizer / prompt_builder / session_store / ws_manager are all optional
    # (the route reads them via getattr(..., None)); leaving them unset is a
    # real configuration the route must tolerate.
    return TestClient(app)


def _final_message(blender_output: object) -> dict[str, object]:
    with _make_client(blender_output).websocket_connect("/ws/chat") as ws:
        ws.send_text(json.dumps({"content": "make a cube"}))
        # Drain streaming tokens; keep the first non-streaming frame.
        while True:
            msg = json.loads(ws.receive_text())
            if msg.get("status") != "streaming":
                return msg


def test_ws_chat_connects_and_completes_a_turn() -> None:
    """The bare connect->send->respond path must not crash (2026-07-15)."""
    final = _final_message("Created cube")

    assert final["status"] == "done"
    assert final["blender_output"] == "Created cube"


def test_ws_chat_survives_dict_blender_output() -> None:
    """A dict Blender output must still reach 'done', not 'error' (2026-07-17)."""
    final = _final_message({"status": "success", "name": "Cube"})

    assert final["status"] == "done"
    assert "Cube" in str(final["blender_output"])
