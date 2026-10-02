"""Reopen the saved six-item scene and verify geometry, anchors and reproducible pixels."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "models/living-items"
CHECK = ROOT / "tmp/living-items-verify"
CHECK.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(OUT / "living-items.blend"))
scene = bpy.context.scene
assert scene.unit_settings.scale_length == 1
expected = {
    "key": "bow",
    "letter": "seal",
    "potion": "cork",
    "purse": "tie",
    "tool": "head",
    "parcel": "ribbon",
}
records = []
for kind, feature in expected.items():
    group = bpy.data.collections["LI_" + kind]
    root = bpy.data.objects["LI_" + kind + "_root"]
    root.location = (0, 0, 0)
    meshes = [o for o in group.objects if o.type == "MESH"]
    assert any(o.name == f"LI_{kind}_{feature}" for o in meshes)
    assert all(o.data.polygons and o.data.materials for o in meshes)
    assert all(o.parent == root for o in meshes)
    for other in expected:
        for obj in bpy.data.collections["LI_" + other].objects:
            obj.hide_render = other != kind
    bpy.context.view_layer.update()
    corners = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    assert min(c.z for c in corners) >= -0.002
    assert max(c.z for c in corners) < 0.8
    assert max(c.x for c in corners) - min(c.x for c in corners) < 1
    for view, size in [("ground", (128, 192)), ("inventory", (64, 64))]:
        scene.camera = bpy.data.objects["LI_" + view + "_camera"]
        scene.render.resolution_x, scene.render.resolution_y = size
        if view == "ground":
            foot = world_to_camera_view(scene, scene.camera, Vector((0, 0, 0)))
            assert abs(foot.x - 0.5) < 1e-5 and abs(foot.y - 0.25) < 1e-5
        for c in corners:
            p = world_to_camera_view(scene, scene.camera, c)
            assert 0.02 < p.x < 0.98 and 0.02 < p.y < 0.98, (kind, view, list(p))
        name = f"{kind}-{view}.png"
        scene.render.filepath = str(CHECK / name)
        bpy.ops.render.render(write_still=True)
        original = bpy.data.images.load(str(OUT / name), check_existing=False)
        rerender = bpy.data.images.load(str(CHECK / name), check_existing=False)
        assert tuple(original.size) == size
        assert original.channels == 4
        pixels = list(original.pixels)
        assert pixels == list(rerender.pixels), (name, "rerender mismatch")
        alpha = pixels[3::4]
        occupied = [(i % size[0], i // size[0]) for i, a in enumerate(alpha) if a > 0.01]
        assert len(occupied) >= (35 if view == "ground" else 100), (name, len(occupied))
        assert all(0 < x < size[0] - 1 and 0 < y < size[1] - 1 for x, y in occupied)
        records.append(
            {
                "file": name,
                "size": size,
                "opaque_pixels": len(occupied),
                "rerender_equal": True,
                "sha256": hashlib.sha256((OUT / name).read_bytes()).hexdigest(),
            }
        )
        bpy.data.images.remove(original)
        bpy.data.images.remove(rerender)
(OUT / "verification.json").write_text(
    json.dumps(
        {
            "passed": True,
            "source_sha256": hashlib.sha256((OUT / "living-items.blend").read_bytes()).hexdigest(),
            "images": records,
        },
        indent=2,
    )
    + "\n"
)
print("LIVING_ITEMS_VERIFIED", len(records))
