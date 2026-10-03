"""Registered suites through canonical MCP; scene preservation through an independent oracle."""

import asyncio
import json
from pathlib import Path

from fastmcp import Client

from scripts.verify.generated_artifact_verify_real import BlenderSocketOracle
from scripts.verify.mcp_verify_real import DEFAULT_MCP_URL
from src.adapters.blender_response import decode_marked_json, execute_code_output, sequence
from src.infrastructure.narrowing import as_str_keyed_exact, required

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = """import bpy,json,hashlib
keys=('shoulder_release_mm','elbow_release_mm','wrist_release_mm')
rows={obj.name:{'basis':[[round(v,6) for v in row] for row in obj.matrix_basis],
 'props':{k:obj[k] for k in keys if k in obj},
 'selected':obj.select_get()} for obj in bpy.data.objects}
meshes={m.name:hashlib.sha256(str([(tuple(v.co)) for v in m.vertices]).encode()).hexdigest() for m in bpy.data.meshes}
print('SCENE_STATE_JSON:'+json.dumps({'objects':rows,'meshes':meshes,'active':bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,'file':bpy.data.filepath,'render':bpy.context.scene.render.filepath}))
"""


def snapshot(oracle: BlenderSocketOracle) -> object:
    response = oracle.execute(SNAPSHOT)
    return decode_marked_json(
        execute_code_output(response["result"], ValueError),
        "SCENE_STATE_JSON:",
        missing="Missing scene evidence",
        invalid="Invalid scene evidence",
        error=ValueError,
    )


async def verify() -> None:
    oracle = BlenderSocketOracle("127.0.0.1", 9876, timeout=60)
    source = ROOT / "tmp/lab-station-module-configurations/cable-clearance.blend"
    restore = ROOT / "tmp/lab-station-electrode-guides-aligned/arm-seated.blend"
    oracle.execute(f"import bpy\nbpy.ops.wm.open_mainfile(filepath={str(source)!r})")
    evidence: dict[str, object] = {}
    try:
        oracle.execute("""import bpy
bpy.ops.mesh.primitive_cube_add(size=.1,location=(2,2,2))
marker=bpy.context.object
marker.name='RESEARCH_route_mcp_preserve'
marker.hide_set(True)
head=bpy.data.objects['S_capillary_head']
head.select_set(True)
bpy.context.view_layer.objects.active=head
assert marker.hide_get() and head.select_get()
bpy.data.objects['S_capillary_head'].location.x += .007
bpy.data.objects['S_capillary_lower']['elbow_release_mm']=.123
""")
        before = snapshot(oracle)
        async with Client(DEFAULT_MCP_URL, timeout=360) as client:
            tools = await client.list_tools()
            assert {"list_verification_suites", "run_verification_suite"} <= {t.name for t in tools}
            catalog = await client.call_tool("list_verification_suites", {})
            assert not catalog.is_error
            for suite_id, count in (("cable-contact-controls", 8), ("electrode-head-routes", 4)):
                result = await client.call_tool("run_verification_suite", {"suite_id": suite_id})
                data = required(
                    result.structured_content,
                    as_str_keyed_exact,
                    message="No structured suite report",
                    error=ValueError,
                )
                assert data["passed"] is True and data["scene_restored"] is True
                assert len(sequence(data["checks"], "checks", ValueError)) == count
                after = snapshot(oracle)
                if after != before:
                    (ROOT / "tmp/lab-station-route-engine/mcp-state-mismatch.json").write_text(
                        json.dumps({"suite": suite_id, "before": before, "after": after}, indent=2)
                    )
                    raise AssertionError("MCP verification changed scene state: " + suite_id)
                evidence[suite_id] = data
            rejected = await client.call_tool(
                "run_verification_suite", {"suite_id": "unknown"}, raise_on_error=False
            )
            assert rejected.is_error and snapshot(oracle) == before
            rejected = await client.call_tool(
                "run_verification_suite",
                {"suite_id": "cable-contact-controls", "code": "print(1)"},
                raise_on_error=False,
            )
            assert rejected.is_error and snapshot(oracle) == before
            oracle.execute(
                "import bpy\nbpy.context.scene['MCP_verify_saved_config']=bpy.context.scene['electrode_configuration']\ndel bpy.context.scene['electrode_configuration']"
            )
            try:
                rejected = await client.call_tool(
                    "run_verification_suite",
                    {"suite_id": "electrode-head-routes"},
                    raise_on_error=False,
                )
                assert rejected.is_error and snapshot(oracle) == before
            finally:
                oracle.execute(
                    "bpy.context.scene['electrode_configuration']=bpy.context.scene.pop('MCP_verify_saved_config')"
                )
        oracle.execute(f"""import bpy,runpy
suite=runpy.run_path({str(ROOT / "scripts/verify/lab_cable_route_checks.py")!r})
try:
    with suite['preserve_current_scene']():
        bpy.data.objects['S_capillary_lower'].location.x += .123
        raise RuntimeError('injected verification interruption')
except RuntimeError as error:
    if str(error) != 'injected verification interruption':
        raise
""")
        assert snapshot(oracle) == before, "Exception path did not restore scene"
        evidence["scene_preserved"] = True
        evidence["exception_restores_scene"] = True
        evidence["unknown_extra_code_missing_model_rejected"] = True
        (ROOT / "tmp/lab-station-route-engine/mcp-verification.json").write_text(
            json.dumps(evidence, indent=2)
        )
        print(
            "MCP: 2 suites, 12 measured cases, scene preservation and 3 rejection controls passed"
        )
    finally:
        oracle.execute(f"import bpy\nbpy.ops.wm.open_mainfile(filepath={str(restore)!r})")


if __name__ == "__main__":
    asyncio.run(verify())
