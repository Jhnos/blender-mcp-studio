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
from src.core.domain.exceptions import DomainError, SceneCreationError
from src.core.domain.hand_instances import HAND_INSTANCES
from src.core.domain.session import Session
from src.core.ports.blender_port import BlenderPort
from src.core.ports.event_bus_port import EventBusPort
from src.core.ports.llm_port import LLMChatPort, LLMToolChatPort, ToolDefinition
from src.core.ports.mcp_port import ToolResult
from src.core.ports.mechanical_generation_port import InstanceCatalogPort
from src.core.ports.prompt_builder_port import PromptBuilderPort

try:
    from src.adapters.prompt.semantic_tool_router import SemanticToolRouter

    _router = SemanticToolRouter()
except Exception:
    _router = None  # type: ignore[assignment]

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
    ToolDefinition(
        name="hunyuan3d_generate",
        description="Generate a 3D mesh from text using Hunyuan3D AI (returns imported object in Blender).",
        parameters={
            "prompt": {
                "type": "string",
                "description": "Text description of the 3D model to generate",
            },
            "negative_prompt": {"type": "string", "description": "What to avoid in the generation"},
        },
        required_params=("prompt",),
    ),
    ToolDefinition(
        name="hyper3d_rodin_generate",
        description="Generate a high-quality 3D model using Hyper3D Rodin AI from text description.",
        parameters={
            "prompt": {"type": "string", "description": "Text description of the 3D model"},
            "geometry_file_format": {
                "type": "string",
                "description": "Output format: glb, usdz, fbx, obj, stl",
            },
        },
        required_params=("prompt",),
    ),
]

#: The project's own generators, offered to the conversation.
#:
#: Distinct from the public MCP catalogue, which `docs/01-architecture.md` fixes
#: at nine curated tools. That catalogue is what an outside client may call;
#: this list is what the LLM inside this process may call, and the two have
#: never been the same set.
#:
#: The slug is an enum rather than a free string so the closed set is visible to
#: the model. It is not the enforcement — the application resolves the slug
#: against the registry and refuses anything else — but a model shown the
#: choices asks for one of them instead of inventing "hand-v4".
_GENERATION_TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="list_instances",
        description=(
            "List the registered mechanical hand instances this studio can build, "
            "with the files each one declares."
        ),
    ),
    ToolDefinition(
        name="build_instance",
        description=(
            "Build one registered mechanical hand instance in Blender and export its "
            "meshes. Use this when the user asks for a hand, a gripper, or a printable "
            "part — not create_object, which only makes primitives."
        ),
        parameters={
            "slug": {
                "type": "string",
                "description": "Which registered instance to build",
                "enum": sorted(HAND_INSTANCES),
            }
        },
        required_params=("slug",),
    ),
]

#: Routing is by name, decided before dispatch. Trying Blender first and falling
#: back on failure would make "the generator raised" indistinguishable from
#: "this was never a Blender tool".
GENERATION_TOOL_NAMES = frozenset(tool.name for tool in _GENERATION_TOOLS)


class ConversationalModelingUseCase:
    """Transforms user dialogue into Blender operations via LLM + MCP.

    Prefers native tool calling (LLMToolChatPort) when available; falls back
    to regex JSON parsing for models that don't support function calling.
    Uses PromptBuilderPort when provided for API-context-enriched system prompts.
    """

    def __init__(
        self,
        llm: LLMChatPort,
        blender: BlenderPort,
        event_bus: EventBusPort | None = None,
        prompt_builder: PromptBuilderPort | None = None,
        generation: InstanceCatalogPort | None = None,
    ) -> None:
        self._llm = llm
        self._blender = blender
        self._bus = event_bus
        self._prompt_builder = prompt_builder
        self._generation = generation
        self._use_tool_calling = isinstance(llm, LLMToolChatPort)

    def available_tools(self, user_message: str = "") -> list[ToolDefinition]:
        """What this conversation may call, given what is wired into it.

        The generation tools are appended *after* the semantic router has had
        its say. The router exists to keep the prompt small by dropping tools
        the message does not look like; dropping the one tool that makes a
        printable part, because the user said "夾爪" rather than a word the
        router knows, would be a silent loss of the whole capability.
        """
        routed = (
            _router.select_tools(user_message, _BLENDER_TOOLS)
            if _router is not None
            else list(_BLENDER_TOOLS)
        )
        if self._generation is None:
            return list(routed)
        return [*routed, *_GENERATION_TOOLS]

    def system_prompt(self, context: dict[str, object] | None = None) -> str:
        """The prompt this use case would send, exposed for streaming callers.

        Delivery adapters need it to drive the token stream themselves; reaching
        for the private helper made the router depend on an implementation
        detail that could be renamed without warning.
        """
        return self._get_system_prompt(context)

    def _get_system_prompt(self, context: dict[str, object] | None = None) -> str:
        if self._prompt_builder is not None:
            return self._prompt_builder.build_system_prompt(context)
        return SYSTEM_PROMPT if self._use_tool_calling else SYSTEM_PROMPT_FALLBACK

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

        # The adapters raise LLMConnectionError / LLMProviderError at their
        # boundary; rewrapping here used to turn a provider's 529 into a 503
        # and lose the cause. Anything else is a bug and propagates as one.
        if self._use_tool_calling:
            command, assistant_reply = await self._chat_with_tools(session)
        else:
            command, assistant_reply = await self._chat_fallback(session)

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
            # Dispatch the domain command as-is. Rewriting high-level tools the
            # addon can't handle (create_object, …) into execute_code is the
            # socket adapter's job, not ours — we don't know which backend we hold.
            result = await self._dispatch(command)
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

    async def _dispatch(self, command: Command) -> ToolResult:
        """Route by tool name, decided before anything is attempted."""
        if command.tool_name not in GENERATION_TOOL_NAMES:
            return await self._blender.execute(command)
        if self._generation is None:
            return ToolResult(
                success=False,
                output=None,
                error=f"{command.tool_name} is not available: no generation service is wired",
            )
        return await self._run_generation(command)

    async def _run_generation(self, command: Command) -> ToolResult:
        """Domain errors become a failed result, not an exception.

        A conversation turn that raises loses the assistant's reply along with
        it. The user asked for a hand that does not exist; the honest answer is
        a message saying so, in the same turn.
        """
        assert self._generation is not None
        try:
            if command.tool_name == "list_instances":
                summaries = await self._generation.list_instances()
                output = json.dumps(
                    [
                        {
                            "slug": summary.slug,
                            "family": summary.family,
                            "parts": list(summary.declared_parts),
                        }
                        for summary in summaries
                    ],
                    ensure_ascii=False,
                )
                return ToolResult(success=True, output=output, error=None)

            slug = command.arguments.get("slug")
            if not isinstance(slug, str):
                return ToolResult(
                    success=False, output=None, error="build_instance needs a slug string"
                )
            build = await self._generation.build(slug)
            output = json.dumps(
                {
                    "slug": build.slug,
                    "output_dir": build.output_dir,
                    "parts": [
                        {"name": part.name, "faces": part.face_count} for part in build.parts
                    ],
                },
                ensure_ascii=False,
            )
            return ToolResult(success=True, output=output, error=None)
        except DomainError as exc:
            return ToolResult(success=False, output=None, error=str(exc))

    async def _chat_with_tools(self, session: Session) -> tuple[Command | None, str]:
        """Native tool calling path — structured, no regex.

        Uses SemanticToolRouter to pre-filter tools based on user message,
        reducing token usage and improving LLM accuracy.
        """
        assert isinstance(self._llm, LLMToolChatPort)

        # Semantic pre-filtering: only send relevant tools to the LLM
        user_msg = session.messages[-1].content if session.messages else ""
        tools = self.available_tools(user_msg)

        response = await self._llm.chat_with_tools(
            messages=session.messages,
            tools=tools,
            system_prompt=self._get_system_prompt(),
        )
        if response.tool_calls:
            tc = response.tool_calls[0]
            command = Command(tool_name=tc.name, arguments=tc.arguments)
            reply = response.text or f"🔧 執行 `{tc.name}`"
            return command, reply
        return None, response.text

    async def _chat_fallback(self, session: Session) -> tuple[Command | None, str]:
        """Regex JSON fallback for models without native tool calling."""
        llm_response = await self._llm.chat(
            messages=session.messages,
            system_prompt=self._get_system_prompt(),
        )
        reply = llm_response.content
        command = CommandParser.from_llm_output(reply)
        return command, reply

    async def _emit(self, event: object) -> None:
        if self._bus is not None:
            from src.core.domain.events import DomainEvent

            if isinstance(event, DomainEvent):
                await self._bus.publish(event)
