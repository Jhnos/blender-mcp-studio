"""Read-only geometric measurements; JSON contracts work with any repeated mesh."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.verify.generated_artifact_verify_real import BlenderSocketOracle  # noqa: E402
from src.verification.mesh_measurements import measurements_pass  # noqa: E402


def probe_code(config: dict[str, object]) -> str:
    return (
        "config = "
        + repr(config)
        + "\n"
        + r"""
import bpy, bmesh, math, json
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
body = bpy.data.objects[config["master_object"]]
local_mesh = bmesh.new()
local_mesh.from_mesh(body.data)
bmesh.ops.triangulate(local_mesh, faces=list(local_mesh.faces))
local_tree = BVHTree.FromBMesh(local_mesh)
local_mesh.free()
points = [v.co for v in body.data.vertices]
dimensions = [(max(p[i] for p in points)-min(p[i] for p in points))*1000 for i in range(3)]
radius = max(math.hypot(p.x, p.y)*1000 for p in points)
hits = []
for x, y, r in config["holes_mm"]:
    samples = [(x, y)] + [(x+r*.8*math.cos(i*math.pi/4), y+r*.8*math.sin(i*math.pi/4)) for i in range(8)]
    for px, py in samples:
        hits.append(local_tree.ray_cast(Vector((px/1000, py/1000, -.1)), Vector((0,0,1)))[0] is not None)
slopes = []
for origin in config["surface_origins_mm"]:
    point, normal, face, distance = local_tree.ray_cast(Vector(tuple(v/1000 for v in origin)), Vector((0,0,-1)))
    slopes.append(math.degrees(math.acos(min(1, abs(normal.z)))) if point is not None else None)
bodies = [o for o in bpy.data.objects if o.name.startswith(config["body_prefix"]) and o.type == "MESH"]
pins = [o for o in bpy.data.objects if o.name.startswith(config["hardware_prefix"]) and o.type == "MESH"]
def world_tree(obj, translation=(0,0,0)):
    mesh = bmesh.new()
    try:
        mesh.from_mesh(obj.data)
        matrix = Matrix.Translation(Vector(translation)) @ obj.matrix_world
        bmesh.ops.transform(mesh, matrix=matrix, verts=mesh.verts)
        bmesh.ops.triangulate(mesh, faces=list(mesh.faces))
        return BVHTree.FromBMesh(mesh)
    finally:
        mesh.free()
body_trees = [world_tree(o) for o in bodies]
pin_trees = [world_tree(o) for o in pins]
overlaps = [len(pin.overlap(body)) for pin in pin_trees for body in body_trees]
pin_points = [o.matrix_world @ v.co for o in pins for v in o.data.vertices]
retention = []
for test in config.get("retention_tests", []):
    moving = [bpy.data.objects[name] for name in test["moving_objects"]]
    for displacement in test["displacements_mm"]:
        shifted = [world_tree(o, tuple(v/1000 for v in displacement)) for o in moving]
        retention.append(sum(len(a.overlap(b)) for a in shifted for b in body_trees))
evidence = {
    "dimensions_mm": dimensions,
    "radius_mm": radius,
    "slope_angles_deg": slopes,
    "hole_hits": hits,
    "hardware_count": len(pins),
    "hardware_inner_radius_mm": min((math.hypot(p.x,p.y)*1000 for p in pin_points), default=-1),
    "hardware_outer_radius_mm": max((math.hypot(p.x,p.y)*1000 for p in pin_points), default=-1),
    "hardware_overlaps": overlaps,
    "retention_overlaps": retention,
}
print(json.dumps(evidence))
"""
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--blender-host", default="127.0.0.1")
    parser.add_argument("--blender-port", type=int, default=9876)
    args = parser.parse_args()
    config = json.loads(args.contract.read_text())
    report = BlenderSocketOracle(args.blender_host, args.blender_port).execute_json(
        probe_code(config)
    )
    passed = measurements_pass(report, config["limits"])
    print(json.dumps({"passed": passed, "measurements": report}, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
