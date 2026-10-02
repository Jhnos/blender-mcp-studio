"""Reopen editable effects and independently validate 48 unclipped reproducible frames."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "models/living-effects"
CHECK = ROOT / "tmp/living-effects-verify"
CHECK.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(OUT / "living-effects.blend"))
scene = bpy.context.scene
scene.camera = bpy.data.objects["LF_camera"]
scene.render.resolution_x = scene.render.resolution_y = 128
assert scene.render.fps == 12 and scene.render.film_transparent
records = []
for kind in ("pickup", "unlock", "complete", "footsteps", "teleport", "blocked"):
    bpy.data.objects[f"LF_{kind}_root"].location = (0, 0, 0)
    meshes = [o for o in bpy.data.collections["LF_" + kind].objects if o.type == "MESH"]
    assert meshes and all(
        o.data.materials and o.animation_data and o.animation_data.action for o in meshes
    )
    for group in bpy.data.collections:
        if group.name.startswith("LF_"):
            for obj in group.objects:
                obj.hide_render = group.name != "LF_" + kind
    poses = set()
    for frame in range(1, 9):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        poses.add(
            tuple(tuple(o.location) + tuple(o.scale) + tuple(o.rotation_euler) for o in meshes)
        )
        for obj in meshes:
            for corner in obj.bound_box:
                p = world_to_camera_view(scene, scene.camera, obj.matrix_world @ Vector(corner))
                assert 0.015 < p.x < 0.985 and 0.015 < p.y < 0.985, (kind, frame, obj.name, list(p))
        name = f"{kind}/{frame - 1:02d}.png"
        scene.render.filepath = str(CHECK / name)
        bpy.ops.render.render(write_still=True)
        original = bpy.data.images.load(str(OUT / name), check_existing=False)
        rerender = bpy.data.images.load(str(CHECK / name), check_existing=False)
        assert tuple(original.size) == (128, 128) and original.channels == 4
        pixels = list(original.pixels)
        assert pixels == list(rerender.pixels), (name, "rerender mismatch")
        alpha = pixels[3::4]
        occupied = [(i % 128, i // 128) for i, a in enumerate(alpha) if a > 0.01]
        assert len(occupied) >= 20
        assert all(0 < x < 127 and 0 < y < 127 for x, y in occupied)
        records.append(
            {
                "file": name,
                "occupied_pixels": len(occupied),
                "rerender_equal": True,
                "sha256": hashlib.sha256((OUT / name).read_bytes()).hexdigest(),
            }
        )
        bpy.data.images.remove(original)
        bpy.data.images.remove(rerender)
    assert len(poses) == 8, (kind, "non-distinct animation poses")
(OUT / "verification.json").write_text(
    json.dumps(
        {
            "passed": True,
            "source_sha256": hashlib.sha256(
                (OUT / "living-effects.blend").read_bytes()
            ).hexdigest(),
            "frames": records,
        },
        indent=2,
    )
    + "\n"
)
print("LIVING_EFFECTS_VERIFIED", len(records))
