"""Saved-file geometry/animation oracle, independent of generator implementation."""

from __future__ import annotations

import json
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "models/living-actors"
TEMP = ROOT / "tmp/living-actors-verify"
TEMP.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(OUT / "living-actors.blend"))
scene = bpy.context.scene
assert scene.unit_settings.scale_length == 1
camera = bpy.data.objects["LW_sprite_camera"]
foot = world_to_camera_view(scene, camera, Vector((0, 0, 0)))
assert abs(foot.x - 0.5) < 1e-5 and abs(foot.y - 0.25) < 1e-5
records = []
for role in ("traveler", "guide", "guard", "artisan"):
    rig = bpy.data.objects[f"LW_{role}_rig"]
    rig.location = (0, 0, 0)
    rig.rotation_euler = (0, 0, 0)
    assert {b.name for b in rig.data.bones} == {
        "root",
        "spine",
        "head",
        "arm.L",
        "arm.R",
        "leg.L",
        "leg.R",
    }
    assert tuple(rig.data.bones["root"].head_local) == (0, 0, 0)
    meshes = [o for o in bpy.data.collections["LW_" + role].objects if o.type == "MESH"]
    assert len(meshes) >= 20
    assert all(
        o.data.materials and len(o.data.polygons) > 0 and not o.hide_viewport for o in meshes
    )
    assert all(any(m.type == "ARMATURE" and m.object == rig for m in o.modifiers) for o in meshes)
    for other in ("traveler", "guide", "guard", "artisan"):
        for obj in bpy.data.collections["LW_" + other].objects:
            obj.hide_render = other != role
    for clip, count in [("idle", 2), ("walk", 6), ("interact", 4)]:
        action = bpy.data.actions[f"LW_{role}_{clip}"]
        assert action.use_fake_user
        rig.animation_data.action = action
        rotations = []
        for frame in range(1, count + 1):
            scene.frame_set(frame)
            rotations.append(tuple(round(v, 6) for b in rig.pose.bones for v in b.rotation_euler))
            assert tuple(rig.pose.bones["root"].location) == (0, 0, 0)
        assert len(set(rotations)) > 1, "static animation"
        records.append(
            {"actor": role, "clip": clip, "frames": count, "unique_poses": len(set(rotations))}
        )
    bpy.context.view_layer.update()
    portrait = bpy.data.objects["LW_portrait_camera"]
    portrait_scene = bpy.context.scene
    portrait_scene.render.resolution_x = portrait_scene.render.resolution_y = 256
    for obj in meshes:
        if "head" in obj.name or "eye" in obj.name or "nose" in obj.name or "hair" in obj.name:
            for corner in obj.bound_box:
                point = world_to_camera_view(
                    portrait_scene, portrait, obj.matrix_world @ Vector(corner)
                )
                assert 0.02 < point.x < 0.98 and 0.02 < point.y < 0.98, (
                    role,
                    obj.name,
                    list(point),
                )
    scene.render.resolution_x, scene.render.resolution_y = 128, 192
    rig.animation_data.action = bpy.data.actions[f"LW_{role}_idle"]
    scene.frame_set(1)
    scene.render.filepath = str(TEMP / (role + "-00.png"))
    bpy.ops.render.render(write_still=True)
    bpy.context.view_layer.update()
    corners = [o.matrix_world @ Vector(v) for o in meshes for v in o.bound_box]
    height = max(v.z for v in corners) - min(v.z for v in corners)
    assert 1.6 <= height <= 1.85, height
bpy.ops.wm.open_mainfile(filepath=str(OUT / "living-markers.blend"))
assert (
    len(
        [
            c
            for c in bpy.data.collections
            if c.name.startswith(
                (
                    "LM_talk_",
                    "LM_quest_",
                    "LM_deliver_",
                    "LM_investigate_",
                    "LM_locked_",
                    "LM_exit_",
                )
            )
        ]
    )
    == 18
)
(OUT / "verification.json").write_text(
    json.dumps(
        {
            "passed": True,
            "records": records,
            "marker_count": 18,
            "anchor": [0.5, 0.75],
            "measured_root_projection": [foot.x, 1 - foot.y],
            "root_world": [0, 0, 0],
        },
        indent=2,
    )
    + "\n"
)
print("LIVING_ACTORS_VERIFIED", len(records))
