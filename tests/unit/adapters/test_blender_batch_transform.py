"""Blender batch-transform anti-corruption layer tests."""

from __future__ import annotations

import base64
import json
import re

import pytest

from src.adapters.batch_transform.blender_batch_transform import (
    BlenderBatchTransformAdapter,
    _batch_transform_code,
)
from src.core.domain.batch_transform import BatchTransformSpec, TransformDelta
from src.core.domain.command import Command
from src.core.domain.exceptions import BatchTransformError, BlenderConnectionError
from src.core.domain.scene_operations import Vector3
from src.core.ports.mcp_port import ToolResult


class RecordingBlender:
    def __init__(self, output: object | None = None, *, success: bool = True) -> None:
        self.output = output
        self.success = success
        self.commands: list[Command] = []

    async def execute(self, command: Command) -> ToolResult:
        self.commands.append(command)
        if not self.success:
            return ToolResult(False, None, "operator unavailable")
        output = self.output
        if output is None:
            output = {
                "result": 'BATCH_TRANSFORM_JSON:{"object_names":["A","B"],'
                '"affected_count":2,"message":"Updated 2 objects"}'
            }
        return ToolResult(True, output)


def mixed_spec(*names: str) -> BatchTransformSpec:
    return BatchTransformSpec(
        tuple(names),
        TransformDelta(
            translation_mm=Vector3(10.0, -20.0, 30.0),
            rotation_deg=Vector3(0.0, 15.0, -90.0),
            scale_percent=Vector3(5.0, -10.0, 25.0),
        ),
    )


def test_generated_batch_script_is_valid_python() -> None:
    compile(_batch_transform_code(mixed_spec("A", "B")), "<batch-transform>", "exec")


def test_generated_batch_script_uses_one_undo_operator_and_preflight() -> None:
    code = _batch_transform_code(mixed_spec("A", "B"))

    assert code.count("bpy.ops.blender_mcp.batch_transform()") == 1
    assert "bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}" in code
    assert code.index("missing =") < code.index("for name in object_names:")
    assert "obj.location[axis] += translation_mm[axis] / 1000.0" in code
    assert "obj.rotation_euler[axis] += math.radians(rotation_deg[axis])" in code
    assert "obj.scale[axis] *= scale_factors[axis]" in code
    assert "bpy.ops.ed.undo_push" not in code


def test_generated_batch_script_carries_names_and_values_as_base64_json() -> None:
    hostile = "x'); bpy.ops.wm.quit_blender(); #"
    code = _batch_transform_code(mixed_spec(hostile))

    match = re.search(r'^payload_b64 = "([A-Za-z0-9+/=]+)"$', code, re.MULTILINE)
    assert match is not None
    payload = json.loads(base64.b64decode(match.group(1)).decode("utf-8"))
    assert payload == {
        "object_names": [hostile],
        "translation_mm": [10.0, -20.0, 30.0],
        "rotation_deg": [0.0, 15.0, -90.0],
        "scale_percent": [5.0, -10.0, 25.0],
    }
    assert hostile not in code


@pytest.mark.asyncio
async def test_adapter_parses_structured_receipt() -> None:
    blender = RecordingBlender()
    adapter = BlenderBatchTransformAdapter(blender)  # type: ignore[arg-type]

    receipt = await adapter.apply_transform(mixed_spec("A", "B"))

    assert blender.commands[0].tool_name == "execute_code"
    assert receipt.object_names == ("A", "B")
    assert receipt.affected_count == 2
    assert receipt.message == "Updated 2 objects"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "output",
    [
        "not a report",
        {"result": "BATCH_TRANSFORM_JSON:not-json"},
        {"result": "BATCH_TRANSFORM_JSON:{}"},
        {
            "result": 'BATCH_TRANSFORM_JSON:{"object_names":["A"],'
            '"affected_count":true,"message":"bad"}'
        },
        {"result": 'BATCH_TRANSFORM_JSON:{"object_names":[1],"affected_count":1,"message":"bad"}'},
    ],
)
async def test_adapter_rejects_untrustworthy_results(output: object) -> None:
    adapter = BlenderBatchTransformAdapter(  # type: ignore[arg-type]
        RecordingBlender(output=output)
    )

    with pytest.raises(BatchTransformError):
        await adapter.apply_transform(mixed_spec("A"))


@pytest.mark.asyncio
async def test_adapter_surfaces_blender_failure() -> None:
    adapter = BlenderBatchTransformAdapter(  # type: ignore[arg-type]
        RecordingBlender(success=False)
    )

    with pytest.raises(BatchTransformError, match="operator unavailable"):
        await adapter.apply_transform(mixed_spec("A"))


@pytest.mark.asyncio
async def test_adapter_preserves_connection_failure() -> None:
    class OfflineBlender(RecordingBlender):
        async def execute(self, command: Command) -> ToolResult:
            raise BlenderConnectionError("offline")

    adapter = BlenderBatchTransformAdapter(OfflineBlender())  # type: ignore[arg-type]

    with pytest.raises(BlenderConnectionError, match="offline"):
        await adapter.apply_transform(mixed_spec("A"))
