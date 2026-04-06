"""WebSocket chat router.

Depends on:
  app.state.blender          — shared BlenderPort singleton (set by lifespan)
  app.state.adapter_factory  — AdapterFactoryPort (DIP: no concrete imports here)
  app.state.event_bus        — EventBusPort for domain event publishing
  app.state.sanitizer        — InputSanitizerPort (prompt injection protection)
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from src.core.domain.session import Session
from src.core.use_cases.conversational_modeling import ConversationalModelingUseCase

logger = logging.getLogger(__name__)
router = APIRouter()

_sessions: dict[str, Session] = {}


def _get_or_create(session_id: str | None) -> Session:
    if session_id and session_id in _sessions:
        return _sessions[session_id]
    s = Session()
    _sessions[s.id] = s
    return s


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket, request: Request) -> None:
    await websocket.accept()

    blender = request.app.state.blender
    factory = request.app.state.adapter_factory
    event_bus = request.app.state.event_bus
    sanitizer = getattr(request.app.state, "sanitizer", None)
    llm = factory.build_llm_adapter()
    use_case = ConversationalModelingUseCase(llm=llm, blender=blender, event_bus=event_bus)

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

            session = _get_or_create(session_id)
            session = session.add_message("user", content)
            _sessions[session.id] = session

            try:
                updated, reply, blender_out = await use_case.execute(session)
                _sessions[session.id] = updated
                await websocket.send_text(json.dumps({
                    "type": "response",
                    "content": reply,
                    "blender_output": blender_out,
                    "status": "done",
                    "session_id": session.id,
                }))
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "response",
                    "content": f"⚠️ Error: {e}",
                    "blender_output": None,
                    "status": "error",
                    "session_id": session.id,
                }))

    except WebSocketDisconnect:
        pass
