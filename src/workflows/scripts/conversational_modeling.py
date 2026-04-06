"""Conversational modeling workflow script.

This script is invoked by the WorkflowEngine for the 'translate_to_command' step.
Swapping this script changes the workflow behaviour without touching the engine.
"""

from __future__ import annotations

from src.core.domain.session import Session
from src.core.ports.llm_port import LLMPort

SYSTEM_PROMPT = """\
You are a 3D modeling assistant connected to Blender via MCP.
When the user describes a 3D scene or object, respond with a JSON object:
{
  "tool_name": "<mcp_tool_name>",
  "arguments": { ... }
}
Available tools: create_object, delete_object, modify_object, apply_material, get_scene_info.
If the request is unclear, ask for clarification first without emitting JSON.
Always respond in the same language the user used.
"""


async def run(session: Session, llm: LLMPort) -> str:
    """Translate user intent to a Blender command via the LLM."""
    response = await llm.chat(session.messages, system_prompt=SYSTEM_PROMPT)
    return response.content
