"""Independent saved-file oracle; never repairs the artifacts it inspects."""

from __future__ import annotations

import json
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1] / "models/world-kit"
manifest = json.loads((ROOT / "manifest.json").read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "world-kit.blend"))
assert len(manifest["assets"]) == 44
assert bpy.context.scene.unit_settings.scale_length == 1
scene = bpy.context.scene
scene.render.resolution_x = 128
scene.render.resolution_y = 192
foot = world_to_camera_view(scene, bpy.data.objects["WK_sprite_camera"], Vector((0, 0, 0)))
assert abs(foot.x - 0.5) < 1e-5 and abs(foot.y - 0.25) < 1e-5, "sprite footpoint projection drift"
records = []
for asset in manifest["assets"]:
    group = bpy.data.collections[asset["collection"]]
    assert len(group.objects) > 0
    assert all(
        o.type == "MESH"
        and len(o.data.polygons) > 0
        and len(o.data.materials) > 0
        and not o.hide_viewport
        and not o.hide_render
        for o in group.objects
    )
    assert all(
        abs(a - b) < 1e-5
        for a, b in zip(group.instance_offset, asset["catalog_offset_m"], strict=True)
    )
    if asset["id"].startswith("lever_"):
        handle = next(o for o in group.objects if o.name.endswith("_handle"))
        grip = next(o for o in group.objects if o.name.endswith("_grip"))
        endpoint = handle.matrix_world @ Vector((0, 0, 0.285))
        assert (endpoint - grip.location).length < 0.03, "lever grip detached from handle"
    vertices = [o.matrix_world @ Vector(v) for o in group.objects for v in o.bound_box]
    dimensions = [max(v[i] for v in vertices) - min(v[i] for v in vertices) for i in range(3)]
    assert all(abs(a - b) < 0.001 for a, b in zip(dimensions, asset["dimensions_m"], strict=True))
    records.append({"id": asset["id"], "palette": asset["palette"], "dimensions_m": dimensions})
for kind in manifest["families"].values():
    for name in kind:
        dims = [a["dimensions_m"] for a in manifest["assets"] if a["id"] == name]
        assert dims[0] == dims[1], name
for palette in ("wood-stone", "metal"):
    for family in manifest["families"]:
        bpy.ops.wm.open_mainfile(filepath=str(ROOT / f"{palette}-{family}.blend"))
        group = bpy.data.collections[f"WK_scene_{palette}_{family}"]
        visible = {
            o.name for o in bpy.context.scene.objects if o.type == "MESH" and not o.hide_viewport
        }
        assert visible == {o.name for o in group.objects}, "source scaffolding visible"
        assert bpy.context.scene.render.filepath.startswith("//")
(ROOT / "verification.json").write_text(
    json.dumps({"passed": True, "assets": records, "assembly_count": 6}, indent=2) + "\n"
)
print("WORLD_KIT_VERIFIED", len(records))
