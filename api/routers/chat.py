"""WebSocket chat router.

Depends on:
  app.state.blender          — shared BlenderPort singleton (set by lifespan)
  app.state.adapter_factory  — AdapterFactoryPort (DIP: no concrete imports here)
  app.state.event_bus        — EventBusPort for domain event publishing
  app.state.sanitizer        — InputSanitizerPort (prompt injection protection)
  app.state.prompt_builder   — PromptBuilderPort (context-enriched system prompts)
  app.state.session_store    — SessionStorePort (persistent session storage)

V3: Streaming — if LLM implements LLMStreamPort, tokens are pushed to the client
in real-time as `status: "streaming"` messages before the final `status: "done"`.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import tempfile

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from src.core.ports.llm_port import LLMStreamPort
from src.core.use_cases.conversational_modeling import ConversationalModelingUseCase

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket, request: Request) -> None:
    await websocket.accept()

    blender = request.app.state.blender
    factory = request.app.state.adapter_factory
    event_bus = request.app.state.event_bus
    sanitizer = getattr(request.app.state, "sanitizer", None)
    prompt_builder = getattr(request.app.state, "prompt_builder", None)
    session_store = getattr(request.app.state, "session_store", None)

    llm = factory.build_llm_adapter()
    use_case = ConversationalModelingUseCase(
        llm=llm,
        blender=blender,
        event_bus=event_bus,
        prompt_builder=prompt_builder,
    )
    supports_streaming = isinstance(llm, LLMStreamPort)

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            session_id: str | None = data.get("session_id")
            content: str = data.get("content", "")

            # Sanitize user input before it reaches the LLM
            if sanitizer is not None:
                result = sanitizer.sanitize(content)
                if not result.clean:
                    logger.warning(
                        "Prompt injection detected in session %s: %s",
                        session_id,
                        result.detections,
                    )
                content = result.sanitized_text

            # Load or create session (persistent store if available, else in-memory)
            if session_store is not None:
                session = (
                    await session_store.get(session_id) if session_id else None
                ) or await session_store.create()
            else:
                from src.core.domain.session import Session
                if not hasattr(request.app.state, "_sessions"):
                    request.app.state._sessions = {}
                _sessions: dict = request.app.state._sessions
                session = (_sessions.get(session_id) if session_id else None) or Session()
                _sessions[session.id] = session

            session = session.add_message("user", content)
            if session_store is not None:
                await session_store.save(session)
            else:
                request.app.state._sessions[session.id] = session

            try:
                # --- Streaming: push tokens as they arrive (text-only path) ---
                # Tool-calling path always runs non-streaming (tools need full response)
                if supports_streaming:
                    from src.core.ports.llm_port import LLMToolChatPort
                    prefers_tools = isinstance(llm, LLMToolChatPort)
                    # Only stream when we won't be using tool-calling
                    if not prefers_tools:
                        await _handle_streaming(
                            websocket, llm, use_case, session,  # type: ignore[arg-type]
                            session_store, request, prompt_builder,
                        )
                        continue

                # --- Non-streaming (tool calling or no stream support) ---
                updated, reply, blender_out = await use_case.execute(session)

                if session_store is not None:
                    await session_store.save(updated)
                else:
                    request.app.state._sessions[updated.id] = updated

                screenshot_b64 = await _capture_screenshot(blender, blender_out)

                await websocket.send_text(json.dumps({
                    "type": "response",
                    "content": reply,
                    "blender_output": blender_out,
                    "screenshot": screenshot_b64,
                    "status": "done",
                    "session_id": updated.id,
                }))
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "response",
                    "content": f"⚠️ Error: {e}",
                    "blender_output": None,
                    "screenshot": None,
                    "status": "error",
                    "session_id": session.id,
                }))

    except WebSocketDisconnect:
        pass


async def _handle_streaming(
    websocket: WebSocket,
    llm: LLMStreamPort,
    use_case: ConversationalModelingUseCase,
    session,
    session_store,
    request: Request,
    prompt_builder,
) -> None:
    """Push LLM tokens to client in real-time, then execute Blender commands."""
    from src.core.domain.command import CommandParser

    system_prompt = use_case._get_system_prompt() if hasattr(use_case, "_get_system_prompt") else None
    accumulated = ""

    try:
        # Stream text tokens to client
        async for token in llm.astream(session.messages, system_prompt=system_prompt):
            accumulated += token
            await websocket.send_text(json.dumps({
                "type": "response",
                "content": token,
                "status": "streaming",
                "session_id": session.id,
            }))

        # After streaming, parse commands from full response and execute
        command = CommandParser.from_llm_output(accumulated)
        blender_out: str | None = None
        if command:
            try:
                result = await use_case._blender.execute(command)
                blender_out = result.output if result.success else f"❌ {result.error}"
            except Exception as exc:
                blender_out = f"❌ {exc}"

        updated = session.add_message("assistant", accumulated)
        if session_store is not None:
            await session_store.save(updated)
        elif hasattr(request.app.state, "_sessions"):
            request.app.state._sessions[updated.id] = updated

        screenshot_b64 = await _capture_screenshot(use_case._blender, blender_out)

        # Final "done" message with full content + blender output
        await websocket.send_text(json.dumps({
            "type": "response",
            "content": accumulated,
            "blender_output": blender_out,
            "screenshot": screenshot_b64,
            "status": "done",
            "session_id": updated.id,
        }))

    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "response",
            "content": f"⚠️ Streaming error: {e}",
            "blender_output": None,
            "screenshot": None,
            "status": "error",
            "session_id": session.id,
        }))


async def _capture_screenshot(blender, blender_out: str | None) -> str | None:
    """Take a viewport screenshot after a successful Blender command."""
    if not blender_out or blender_out.startswith("❌"):
        return None
    try:
        tmp = tempfile.mktemp(suffix=".png")
        shot = await blender.call_tool("get_viewport_screenshot", {"filepath": tmp})
        if shot.success and os.path.exists(tmp):
            with open(tmp, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            os.unlink(tmp)
            return b64
    except Exception as exc:
        logger.debug("Screenshot capture failed: %s", exc)
    return None

