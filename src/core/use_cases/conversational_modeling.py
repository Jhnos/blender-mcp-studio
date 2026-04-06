"""Conversational Modeling Use Case.

Orchestrates: user message → LLM intent parsing → Blender command execution.

Strategy for command extraction (in priority order):
  1. LLMToolChatPort.chat_with_tools() — native structured output, most reliable
  2. CommandParser.from_llm_output() — regex JSON fallback for plain-text models

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
from src.core.ports.llm_port import LLMChatPort, LLMToolChatPort, ToolDefinition

SYSTEM_PROMPT = """\
You are a 3D modeling assistant connected to Blender via MCP.
When the user describes a 3D scene or object, call the appropriate tool.
Always respond in the same language the user used.
If the request is unclear, ask for clarification instead of guessing.
"""

SYSTEM_PROMPT_FALLBACK = """\
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

_BLENDER_TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="create_object",
        description="Create a new 3D object in the Blender scene.",
        parameters={
            "type": {"type": "string", "description": "Object type: MESH, CURVE, LIGHT, CAMERA"},
            "name": {"type": "string", "description": "Name for the new object"},
            "location": {"type": "array", "items": {"type": "number"}, "description": "[x, y, z]"},
            "scale": {"type": "array", "items": {"type": "number"}, "description": "[sx, sy, sz]"},
        },
        required_params=("type",),
    ),
    ToolDefinition(
        name="delete_object",
        description="Delete an object from the Blender scene by name.",
        parameters={"name": {"type": "string", "description": "Object name to delete"}},
        required_params=("name",),
    ),
    ToolDefinition(
        name="modify_object",
        description="Modify properties of an existing object (location, scale, visibility).",
        parameters={
            "name": {"type": "string"},
            "location": {"type": "array", "items": {"type": "number"}},
            "rotation": {"type": "array", "items": {"type": "number"}},
            "scale": {"type": "array", "items": {"type": "number"}},
            "visible": {"type": "boolean"},
        },
        required_params=("name",),
    ),
    ToolDefinition(
        name="apply_material",
        description="Apply or create a material on a Blender object.",
        parameters={
            "object_name": {"type": "string"},
            "material_name": {"type": "string"},
            "color": {"type": "array", "items": {"type": "number"}, "description": "RGBA [0-1]"},
            "metallic": {"type": "number"},
            "roughness": {"type": "number"},
        },
        required_params=("object_name", "material_name"),
    ),
    ToolDefinition(
        name="get_scene_info",
        description="Get current scene objects and metadata.",
        parameters={},
        required_params=(),
    ),
    ToolDefinition(
        name="execute_code",
        description="Execute arbitrary Python (bpy) code in Blender for advanced operations.",
        parameters={"code": {"type": "string", "description": "Python bpy code to execute"}},
        required_params=("code",),
    ),
]


class ConversationalModelingUseCase:
    """Transforms user dialogue into Blender operations via LLM + MCP.

    Prefers native tool calling (LLMToolChatPort) when available; falls back
    to regex JSON parsing for models that don't support function calling.
    """

    def __init__(
        self,
        llm: LLMChatPort,
        blender: BlenderPort,
        event_bus: EventBusPort | None = None,
    ) -> None:
        self._llm = llm
        self._blender = blender
        self._bus = event_bus
        self._use_tool_calling = isinstance(llm, LLMToolChatPort)

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
            if self._use_tool_calling:
                command, assistant_reply = await self._chat_with_tools(session)
            else:
                command, assistant_reply = await self._chat_fallback(session)
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

        updated_session = session.add_message("assistant", assistant_reply)
        await self._emit(
            MessageAddedEvent(
                session_id=session.id,
                role="assistant",
                content_preview=assistant_reply[:120],
            )
        )

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

    async def _chat_with_tools(
        self, session: Session
    ) -> tuple[Command | None, str]:
        """Native tool calling path — structured, no regex."""
        assert isinstance(self._llm, LLMToolChatPort)
        response = await self._llm.chat_with_tools(
            messages=session.messages,
            tools=_BLENDER_TOOLS,
            system_prompt=SYSTEM_PROMPT,
        )
        if response.tool_calls:
            tc = response.tool_calls[0]
            command = Command(tool_name=tc.name, arguments=tc.arguments)
            reply = response.text or f"🔧 執行 `{tc.name}`"
            return command, reply
        return None, response.text

    async def _chat_fallback(
        self, session: Session
    ) -> tuple[Command | None, str]:
        """Regex JSON fallback for models without native tool calling."""
        llm_response = await self._llm.chat(
            messages=session.messages,
            system_prompt=SYSTEM_PROMPT_FALLBACK,
        )
        reply = llm_response.content
        command = CommandParser.from_llm_output(reply)
        return command, reply

    async def _emit(self, event: object) -> None:
        if self._bus is not None:
            from src.core.domain.events import DomainEvent
            if isinstance(event, DomainEvent):
                await self._bus.publish(event)

