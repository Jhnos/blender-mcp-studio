"""BlenderMCPAdapter is the socket-addon translation chokepoint.

The ahujasid socket addon only handles execute_code + read tools (it has no
create_object/delete_object/modify_object/apply_material handler). Rewriting
high-level modeling tools into an equivalent execute_code bpy script is an
*adapter* concern — the use cases speak the domain language (create_object) and
must not know this backend's limitation. So translation lives here, at the one
point every socket dispatch passes through, rather than in each use case (which
is how a second dispatch path — ModelingPipeline — reached the addon untranslated
and failed with "Unknown command type").

These tests pin translation to the adapter and prove no caller can bypass it.
"""

from __future__ import annotations

import logging

import pytest

from src.adapters.mcp.blender_mcp_adapter import BlenderMCPAdapter, BlenderMCPClient
from src.core.domain.command import Command
from src.core.ports.mcp_port import MCPPort, ToolDefinition, ToolResult


class _RecordingMCP:
    """Stands in for BlenderMCPClient — records the tool name that reached the socket."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.output: object = "ok"

    async def call_tool(self, tool_name: str, arguments: dict[str, object]) -> ToolResult:
        self.calls.append((tool_name, arguments))
        return ToolResult(success=True, output=self.output, error=None)


def _adapter_with_recording_mcp() -> tuple[BlenderMCPAdapter, _RecordingMCP]:
    adapter = BlenderMCPAdapter(host="localhost", port=9876)
    mcp = _RecordingMCP()
    adapter._mcp = mcp  # type: ignore[assignment]
    return adapter, mcp


@pytest.mark.asyncio
async def test_execute_translates_high_level_tool_to_execute_code() -> None:
    """A create_object Command must reach the socket as execute_code bpy."""
    adapter, mcp = _adapter_with_recording_mcp()

    await adapter.execute(
        Command(tool_name="create_object", arguments={"type": "MESH", "name": "BlackCat"})
    )

    assert len(mcp.calls) == 1
    sent_tool, sent_args = mcp.calls[0]
    assert sent_tool == "execute_code"
    code = sent_args["code"]
    assert isinstance(code, str)
    assert "primitive_cube_add" in code
    assert "BlackCat" in code


@pytest.mark.asyncio
async def test_call_tool_path_also_translates() -> None:
    """The direct call_tool entry must translate too — no bypass via that path."""
    adapter, mcp = _adapter_with_recording_mcp()

    await adapter.call_tool("apply_material", {"object_name": "Cube", "material_name": "Red"})

    assert len(mcp.calls) == 1
    sent_tool, _ = mcp.calls[0]
    assert sent_tool == "execute_code"


@pytest.mark.asyncio
async def test_translated_tool_unwraps_addon_execute_code_message() -> None:
    """Domain operations receive the addon's message, not its transport envelope."""
    adapter, mcp = _adapter_with_recording_mcp()
    mcp.output = {"result": "created Cube", "logs": []}

    result = await adapter.execute(
        Command(tool_name="create_object", arguments={"type": "MESH", "name": "Cube"})
    )

    assert result == ToolResult(success=True, output="created Cube", error=None)


@pytest.mark.asyncio
async def test_direct_execute_code_unwraps_addon_execute_code_message() -> None:
    """Direct bpy calls receive the payload text, not a transport mapping."""
    adapter, mcp = _adapter_with_recording_mcp()
    mcp.output = {"executed": True, "result": "undo ok\n"}

    result = await adapter.execute(
        Command(tool_name="execute_code", arguments={"code": "import bpy\nbpy.ops.ed.undo()"})
    )

    assert result == ToolResult(success=True, output="undo ok\n", error=None)


@pytest.mark.asyncio
async def test_read_tools_pass_through_untouched() -> None:
    """Read tools must be forwarded unchanged."""
    adapter, mcp = _adapter_with_recording_mcp()

    await adapter.call_tool("get_viewport_screenshot", {"filepath": "/tmp/x.png"})

    assert mcp.calls[0][0] == "get_viewport_screenshot"


@pytest.mark.asyncio
async def test_modeling_pipeline_stage_reaches_socket_as_execute_code() -> None:
    """The production bug this fix closes: ModelingPipeline dispatched a
    create_object stage untranslated, so the addon rejected it.

    Exercises the real composition — ModelingPipelineUseCase → BlenderMCPAdapter
    → socket — that MockBlender-based pipeline tests cannot reach, because the
    mock replaces the very adapter that now owns translation.
    """
    from src.core.domain.pipeline import PipelineStage
    from src.core.use_cases.modeling_pipeline import ModelingPipelineUseCase

    adapter, mcp = _adapter_with_recording_mcp()
    use_case = ModelingPipelineUseCase(blender=adapter)
    stage = PipelineStage(
        name="create_base",
        description="",
        tool_name="create_object",
        arguments_template={"type": "MESH", "name": "{{ object_name }}"},
    )

    await use_case.execute([stage], context={"object_name": "Widget"})

    assert len(mcp.calls) == 1
    sent_tool, sent_args = mcp.calls[0]
    assert sent_tool == "execute_code"
    assert "Widget" in str(sent_args["code"])


@pytest.mark.asyncio
async def test_socket_client_rejects_untranslated_high_level_tool() -> None:
    """Defense in depth: if a high-level tool ever reaches the socket boundary,
    translation was bypassed — fail loud rather than send "Unknown command type"."""
    client = BlenderMCPClient(socket=None)  # type: ignore[arg-type]

    result = await client.call_tool("create_object", {"type": "MESH"})

    assert not result.success
    assert result.error is not None
    assert "translat" in result.error.lower()


# ---------------------------------------------------------------------------
# get_scene_info — narrowing + fallback contract.
#
# Salvaged from an unmerged parallel-session commit (d5d3b07): the get_scene_info
# narrowing fix reached main but its dedicated tests did not. Guards the
# 2026-07-18 fix — get_scene_info must return a genuine dict[str, object] via
# as_str_keyed (keys actually checked), and degrade to {} with a warning on a
# non-mapping reply, never smuggling a dict[Any, Any] through. See
# docs/LESSONS_LEARNED.md 2026-07-18.
# ---------------------------------------------------------------------------


class _StubMCP(MCPPort):
    """Returns a preset output for any tool call — isolates get_scene_info."""

    def __init__(self, output: object) -> None:
        self._output = output

    async def call_tool(self, tool_name: str, arguments: dict[str, object]) -> ToolResult:
        return ToolResult(success=True, output=self._output)

    async def list_tools(self) -> list[ToolDefinition]:
        return []

    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...


def _adapter_with(output: object) -> BlenderMCPAdapter:
    adapter = BlenderMCPAdapter("localhost", 9999)
    adapter._mcp = _StubMCP(output)  # type: ignore[assignment]  # inject fake transport
    return adapter


@pytest.mark.asyncio
async def test_get_scene_info_returns_mapping_unchanged() -> None:
    """A str-keyed mapping is returned as-is."""
    scene = {"objects": ["Cube"], "description": "one cube"}
    info = await _adapter_with(scene).get_scene_info()
    assert info == scene


@pytest.mark.asyncio
async def test_get_scene_info_drops_non_string_keys() -> None:
    """Keys are actually checked — non-str keys are dropped, not smuggled through.

    This is the exact difference from the old isinstance-only code, which
    returned a dict[Any, Any] as dict[str, object] without ever looking at keys.
    """
    info = await _adapter_with({"objects": [], True: "yes"}).get_scene_info()
    assert info == {"objects": []}


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [None, ["not", "a", "map"], "raw string", 42])
async def test_get_scene_info_returns_empty_and_warns_on_non_mapping(bad, caplog) -> None:
    """Non-mapping output → {} with a warning (NO_SILENT_FALLBACK), never a lie-typed dict."""
    with caplog.at_level(logging.WARNING):
        info = await _adapter_with(bad).get_scene_info()
    assert info == {}
    assert any("get_scene_info" in record.message for record in caplog.records)
