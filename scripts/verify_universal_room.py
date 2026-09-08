"""Independently reopen the delivered Blender library and inspect mesh/image data."""

from __future__ import annotations

import json
from pathlib import Path

import bpy
from mathutils import Vector


def verify() -> None:
    root = Path(__file__).resolve().parents[1] / "models/universal-room"
    manifest = json.loads((root / "manifest.json").read_text())
    bpy.ops.wm.open_mainfile(filepath=str(root / "universal-room.blend"))
    assert bpy.context.scene.unit_settings.scale_length == 1
    assert bpy.context.scene.render.filepath.startswith("//")
    assert len(manifest["assets"]) == 30
    results = []
    for asset in manifest["assets"]:
        group = bpy.data.collections[asset["collection"]]
        assert len(group.objects) > 0
        frame = asset["frame"]
        expected_offset = (
            (frame % 7) * 2.2,
            (frame // 7) * 3 + (0 if asset["palette"] == "wood-stone" else 7),
            0,
        )
        assert all(
            abs(a - b) < 0.0001 for a, b in zip(group.instance_offset, expected_offset, strict=True)
        )
        assert all(
            o.type == "MESH" and len(o.data.polygons) > 0 and o.data.materials
            for o in group.objects
        )
        assert all(not o.hide_viewport and not o.hide_render for o in group.objects)
        vertices = [o.matrix_world @ Vector(v) for o in group.objects for v in o.bound_box]
        size = [max(v[i] for v in vertices) - min(v[i] for v in vertices) for i in range(3)]
        assert all(abs(a - b) < 0.001 for a, b in zip(size, asset["dimensions_m"], strict=True)), (
            asset
        )
        sprite = bpy.data.images.load(str(root / asset["palette"] / (asset["id"] + ".png")))
        expected = (64, 64) if asset["id"] == "floor" else (128, 192)
        assert tuple(sprite.size) == expected
        alpha = list(sprite.pixels)[3::4]
        assert max(alpha) > 0.9
        if asset["id"] != "floor":
            assert min(alpha) == 0
        results.append({"asset": asset["collection"], "dimensions_m": size, "pixels": expected})
    bpy.ops.wm.open_mainfile(filepath=str(root / "warehouse.blend"))
    assert bpy.context.scene.render.filepath.startswith("//")
    assembled = bpy.data.collections["UR_warehouse"]
    assert len(assembled.objects) > 100
    assert any("noticeboard" in o.name for o in assembled.objects)
    report = {"passed": True, "source_assets": results, "assembled_objects": len(assembled.objects)}
    (root / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print("UNIVERSAL_ROOM_VERIFIED", len(results), len(assembled.objects))


if __name__ == "__main__":
    verify()
