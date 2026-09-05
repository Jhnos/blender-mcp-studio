"""Blender anti-corruption layer for atomic incremental transforms."""

from __future__ import annotations

import base64
import json

from src.adapters.blender_response import (
    execute_code_output,
    integer,
    mapping,
    sequence,
    text,
)
from src.core.domain.batch_transform import (
    BatchTransformReceipt,
    BatchTransformSpec,
)
from src.core.domain.command import Command
from src.core.domain.exceptions import BatchTransformError
from src.core.ports.blender_port import BlenderPort

_MARKER = "BATCH_TRANSFORM_JSON:"


def _batch_transform_code(spec: BatchTransformSpec) -> str:
    payload = {
        "object_names": list(spec.object_names),
        "translation_mm": spec.delta.translation_mm.as_list(),
        "rotation_deg": spec.delta.rotation_deg.as_list(),
        "scale_percent": spec.delta.scale_percent.as_list(),
    }
    payload_b64 = base64.b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return f'''import base64
import bpy
import json
import math

payload_b64 = "{payload_b64}"
payload = json.loads(base64.b64decode(payload_b64).decode("utf-8"))

class BLENDER_MCP_OT_batch_transform(bpy.types.Operator):
    bl_idname = "blender_mcp.batch_transform"
    bl_label = "Blender MCP Batch Transform"
    bl_options = {{'REGISTER', 'UNDO', 'INTERNAL'}}

    def execute(self, context):
        object_names = payload["object_names"]
        translation_mm = payload["translation_mm"]
        rotation_deg = payload["rotation_deg"]
        scale_percent = payload["scale_percent"]
        missing = [name for name in object_names if bpy.data.objects.get(name) is None]
        scale_factors = [1.0 + value / 100.0 for value in scale_percent]
        if missing:
            self.report({{'ERROR'}}, "Missing objects: " + ", ".join(missing))
            return {{'CANCELLED'}}
        if any(factor <= 0.0 for factor in scale_factors):
            self.report({{'ERROR'}}, "Scale factors must remain positive")
            return {{'CANCELLED'}}

        for name in object_names:
            obj = bpy.data.objects[name]
            for axis in range(3):
                obj.location[axis] += translation_mm[axis] / 1000.0
                obj.rotation_euler[axis] += math.radians(rotation_deg[axis])
                obj.scale[axis] *= scale_factors[axis]
        return {{'FINISHED'}}

bpy.utils.register_class(BLENDER_MCP_OT_batch_transform)
try:
    operator_result = bpy.ops.blender_mcp.batch_transform('EXEC_DEFAULT', True)
    if 'FINISHED' not in operator_result:
        raise RuntimeError("Batch transform was cancelled")
    receipt = {{
        "object_names": payload["object_names"],
        "affected_count": len(payload["object_names"]),
        "message": f"Updated {{len(payload['object_names'])}} objects",
    }}
    print("{_MARKER}" + json.dumps(receipt, separators=(",", ":")))
finally:
    bpy.utils.unregister_class(BLENDER_MCP_OT_batch_transform)
'''


def _integer(value: object, context: str) -> int:
    return integer(value, context, BatchTransformError)


def _parse_receipt(output: str) -> BatchTransformReceipt:
    marker_index = output.rfind(_MARKER)
    if marker_index < 0:
        raise BatchTransformError("Blender batch transform returned no structured receipt")
    encoded = output[marker_index + len(_MARKER) :].strip().splitlines()[0]
    try:
        raw: object = json.loads(encoded)
    except json.JSONDecodeError as exc:
        raise BatchTransformError("Blender batch transform returned invalid JSON") from exc
    receipt = mapping(raw, "batch-transform receipt", BatchTransformError)
    required = {"object_names", "affected_count", "message"}
    if not required.issubset(receipt):
        raise BatchTransformError("Blender batch-transform receipt is missing required fields")
    names = tuple(
        text(name, "batch-transform object name", BatchTransformError)
        for name in sequence(
            receipt["object_names"], "batch-transform object names", BatchTransformError
        )
    )
    return BatchTransformReceipt(
        object_names=names,
        affected_count=_integer(receipt["affected_count"], "affected count"),
        message=text(receipt["message"], "batch-transform message", BatchTransformError),
    )


class BlenderBatchTransformAdapter:
    """Apply all target deltas through one Blender Undo-capable operator."""

    def __init__(self, blender: BlenderPort) -> None:
        self._blender = blender

    async def apply_transform(self, spec: BatchTransformSpec) -> BatchTransformReceipt:
        result = await self._blender.execute(
            Command(
                tool_name="execute_code",
                arguments={"code": _batch_transform_code(spec)},
            )
        )
        if not result.success:
            raise BatchTransformError(
                result.error or "Blender batch transform failed without a reason"
            )
        return _parse_receipt(execute_code_output(result.output, BatchTransformError))
