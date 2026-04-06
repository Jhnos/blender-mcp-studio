"""Conversational Modeling Use Case.

Orchestrates: user message → LLM intent parsing → Blender command execution.
Publishes domain events for cross-cutting concerns (logging, monitoring, etc.).
"""

from __future__ import annotations

import json

from src.core.domain.command import Command, CommandParser
from src.core.domain.events import (
    CommandExecutedEvent,
    CommandFailedEvent,
    LLMCalledEvent,
    MessageAddedEvent,
)
from src.core.domain.exceptions import LLMConnectionError, SceneCreationError
from src.core.domain.session import Session
from src.core.ports.blender_port import BlenderPort
from src.core.ports.event_bus_port import EventBusPort
from src.core.ports.llm_port import LLMChatPort

SYSTEM_PROMPT = """\
You are a 3D modeling assistant connected to Blender via MCP.
When the user describes a 3D scene or object, respond with a JSON object:
{
  "tool_name": "<mcp_tool_name>",
  "arguments": { ... }
}
Always respond in the same language the user used.
If the request is unclear, ask for clarification instead.
Available tools: create_object, delete_object, modify_object, apply_material, get_scene_info.
"""


class ConversationalModelingUseCase:
    """Transforms user dialogue into Blender operations via LLM + MCP."""

    def __init__(
        self,
        llm: LLMChatPort,
        blender: BlenderPort,
        event_bus: EventBusPort | None = None,
    ) -> None:
        self._llm = llm
        self._blender = blender
        self._bus = event_bus

    async def execute(self, session: Session) -> tuple[Session, str, str | None]:
        """Process the latest user message and execute in Blender.

        Returns (updated_session, assistant_reply, blender_output).
        blender_output is None if no Blender command was executed.
        """
        if not session.messages:
            raise SceneCreationError("Session has no messages to process.")

        await self._emit(
            MessageAddedEvent(
                session_id=session.id,
                role="user",
                content_preview=session.messages[-1].content[:120],
            )
        )

        try:
            llm_response = await self._llm.chat(
                messages=session.messages,
                system_prompt=SYSTEM_PROMPT,
            )
        except Exception as e:
            raise LLMConnectionError("LLM chat failed") from e

        await self._emit(
            LLMCalledEvent(
                session_id=session.id,
                provider=getattr(self._llm, "provider_name", "unknown"),
                model=getattr(self._llm, "model_name", "unknown"),
                message_count=len(session.messages),
            )
        )

        assistant_reply = llm_response.content
        updated_session = session.add_message("assistant", assistant_reply)

        await self._emit(
            MessageAddedEvent(
                session_id=session.id,
                role="assistant",
                content_preview=assistant_reply[:120],
            )
        )

        command = CommandParser.from_llm_output(assistant_reply)
        blender_output: str | None = None
        if command is not None:
            result = await self._blender.execute(command)
            if not result.success:
                await self._emit(
                    CommandFailedEvent(
                        session_id=session.id,
                        tool_name=command.tool_name,
                        error=result.error or "unknown",
                    )
                )
                return updated_session, assistant_reply, f"❌ {result.error}"

            await self._emit(
                CommandExecutedEvent(
                    session_id=session.id,
                    tool_name=command.tool_name,
                    arguments=json.dumps(command.arguments),
                    output_preview=str(result.output)[:120],
                )
            )
            blender_output = str(result.output) if result.output else "✅ 執行成功"

        return updated_session, assistant_reply, blender_output

    async def _emit(self, event: object) -> None:
        if self._bus is not None:
            from src.core.domain.events import DomainEvent
            if isinstance(event, DomainEvent):
                await self._bus.publish(event)

