from __future__ import annotations

import json

import pytest

from src.adapters.print_readiness.blender_print_readiness import (
    BlenderPrintReadinessAdapter,
    _analysis_code,
)
from src.core.domain.command import Command
from src.core.domain.exceptions import PrintReadinessError
from src.core.domain.print_readiness import (
    PrintIssueCode,
    PrintIssueSeverity,
    PrintReadinessSpec,
)
from src.core.ports.mcp_port import ToolResult


def raw_report() -> dict[str, object]:
    return {
        "metrics": {
            "object_count": 2,
            "triangle_count": 24,
            "dimensions_mm": [127.8, 87.0, 167.4],
            "estimated_volume_mm3": 32100.0,
            "surface_area_mm2": 12400.0,
        },
        "issues": [
            {
                "code": "intersections",
                "severity": "warning",
                "count": 3,
                "object_names": ["Base", "Back"],
                "message": "3 intersecting triangle pairs",
            }
        ],
        "analysis_truncated": False,
    }


class InspectingBlender:
    def __init__(self, output: object | None = None, *, success: bool = True) -> None:
        self.output = output
        self.success = success
        self.commands: list[Command] = []

    async def execute(self, command: Command) -> ToolResult:
        self.commands.append(command)
        if not self.success:
            return ToolResult(False, None, "analysis operator failed")
        payload = self.output
        if payload is None:
            payload = {"result": "PRINT_READINESS_JSON:" + json.dumps(raw_report())}
        return ToolResult(True, payload)


@pytest.mark.parametrize("apply_modifiers", [True, False])
def test_generated_analysis_script_is_valid_python(apply_modifiers: bool) -> None:
    code = _analysis_code(PrintReadinessSpec(apply_modifiers=apply_modifiers))

    compile(code, "<print-readiness>", "exec")


def test_overhang_threshold_is_measured_from_a_vertical_wall() -> None:
    code = _analysis_code(PrintReadinessSpec(overhang_angle_deg=90.0))

    assert "overhang_z = -math.sin(math.radians(OVERHANG_DEG))" in code


@pytest.mark.asyncio
async def test_adapter_generates_read_only_blender_51_analysis_code() -> None:
    blender = InspectingBlender()
    adapter = BlenderPrintReadinessAdapter(blender)  # type: ignore[arg-type]

    await adapter.inspect(
        PrintReadinessSpec(
            selection_only=True,
            apply_modifiers=False,
            min_wall_thickness_mm=0.6,
            overhang_angle_deg=50.0,
        )
    )

    command = blender.commands[0]
    code = str(command.arguments["code"])
    assert command.tool_name == "execute_code"
    assert "import bmesh" in code
    assert "from mathutils.bvhtree import BVHTree" in code
    assert "obj.select_get()" in code
    assert "evaluated_get" not in code
    assert "MIN_WALL_MM = 0.6" in code
    assert "OVERHANG_DEG = 50.0" in code
    assert "MAX_TRIANGLE_SAMPLES = 20000" in code
    assert "MAX_INTERSECTION_PAIRS = 5000" in code
    assert "bpy.ops" not in code


@pytest.mark.asyncio
async def test_adapter_parses_structured_report_without_silent_fallback() -> None:
    adapter = BlenderPrintReadinessAdapter(InspectingBlender())  # type: ignore[arg-type]

    inspection = await adapter.inspect(PrintReadinessSpec())

    assert inspection.metrics.dimensions_mm == (127.8, 87.0, 167.4)
    assert inspection.metrics.triangle_count == 24
    assert inspection.issues[0].code is PrintIssueCode.INTERSECTIONS
    assert inspection.issues[0].severity is PrintIssueSeverity.WARNING
    assert inspection.issues[0].object_names == ("Base", "Back")
    assert inspection.analysis_truncated is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "blender",
    [
        InspectingBlender(success=False),
        InspectingBlender(output={"result": "not a report"}),
        InspectingBlender(output={"result": "PRINT_READINESS_JSON:{}"}),
    ],
)
async def test_adapter_surfaces_untrustworthy_results(blender: InspectingBlender) -> None:
    adapter = BlenderPrintReadinessAdapter(blender)  # type: ignore[arg-type]

    with pytest.raises(PrintReadinessError):
        await adapter.inspect(PrintReadinessSpec())
