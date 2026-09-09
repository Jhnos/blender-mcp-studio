"""The generator tools a conversation may call, and what running one means.

Split out of `conversational_modeling` at its line budget, and the seam is
real: that module is about turning dialogue into a command, while this one
describes a capability and executes it. They change for different reasons.

Distinct from the public MCP catalogue, which `docs/01-architecture.md` fixes
at nine curated tools. That catalogue is what an outside client may call; this
list is what the LLM inside this process may call, and the two have never been
the same set. `tests/e2e/test_mcp_streamable_http.py` watches for them merging.
"""

from __future__ import annotations

import json

from src.core.domain.command import Command
from src.core.domain.exceptions import DomainError
from src.core.domain.hand_instances import HAND_INSTANCES
from src.core.ports.llm_port import ToolDefinition
from src.core.ports.mcp_port import ToolResult
from src.core.ports.mechanical_generation_port import InstanceCatalogPort

#: The slug is an enum rather than a free string so the closed set is visible to
#: the model. It is not the enforcement — the application resolves the slug
#: against the registry and refuses anything else — but a model shown the
#: choices asks for one of them instead of inventing "hand-v4".
GENERATION_TOOLS: list[ToolDefinition] = [
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
GENERATION_TOOL_NAMES = frozenset(tool.name for tool in GENERATION_TOOLS)


async def run_generation_tool(service: InstanceCatalogPort, command: Command) -> ToolResult:
    """Execute one generation tool and report it the way a tool call is reported.

    Domain errors become a failed result, not an exception. A conversation turn
    that raises loses the assistant's reply along with it; the user asked for a
    hand that does not exist, and the honest answer is a message saying so, in
    the same turn.
    """
    try:
        if command.tool_name == "list_instances":
            summaries = await service.list_instances()
            payload: object = [
                {
                    "slug": summary.slug,
                    "family": summary.family,
                    "parts": list(summary.declared_parts),
                }
                for summary in summaries
            ]
            return ToolResult(
                success=True, output=json.dumps(payload, ensure_ascii=False), error=None
            )

        slug = command.arguments.get("slug")
        if not isinstance(slug, str):
            return ToolResult(
                success=False, output=None, error="build_instance needs a slug string"
            )
        build = await service.build(slug)
        payload = {
            "slug": build.slug,
            "output_dir": build.output_dir,
            "parts": [{"name": part.name, "faces": part.face_count} for part in build.parts],
        }
        return ToolResult(success=True, output=json.dumps(payload, ensure_ascii=False), error=None)
    except DomainError as exc:
        return ToolResult(success=False, output=None, error=str(exc))
