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
from src.infrastructure.narrowing import (  # noqa: E402
    as_finite_number,
    as_sequence,
    as_str_keyed_exact,
)
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


def section_probe_code(config: object) -> str:
    """Build one read-only section observation; no model, output or script selection."""
    value = as_str_keyed_exact(config)
    if value is None or set(value) != {"owners", "frame", "planes_x_mm"}:
        raise ValueError("section request requires owners, frame and plane coordinates")
    owners, planes = as_sequence(value["owners"]), as_sequence(value["planes_x_mm"])
    frame = value["frame"]
    if owners is None or not 1 <= len(owners) <= 64 or planes is None or not 1 <= len(planes) <= 32:
        raise ValueError("section request has an empty or oversized population")
    if any(not isinstance(name, str) or not name or len(name) > 128 for name in (*owners, frame)):
        raise ValueError("section request needs bounded object and frame names")
    if len(set(owners)) != len(owners):
        raise ValueError("section object names must be unique")
    coordinates = [as_finite_number(v) for v in planes]
    if any(v is None for v in coordinates):
        raise ValueError("section plane coordinates must be finite numbers")
    payload = {"owners": list(owners), "frame": frame, "planes_x_mm": coordinates}
    program = (
        "section_config = "
        + repr(payload)
        + "\n"
        + r"""
import bpy, bmesh, json, math
from mathutils import Vector
bpy.context.view_layer.update()
frame = bpy.data.objects[section_config["frame"]].matrix_world.copy()
axes = [frame.to_3x3().col[i] for i in range(3)]
if (any(abs(axis.length-1)>1e-6 for axis in axes)
    or any(abs(axes[i].dot(axes[j]))>1e-6 for i in range(3) for j in range(i))
    or any(not math.isfinite(v) for row in frame for v in row)):
    raise ValueError("section coordinate frame must be finite and rigid in metres")
inverse = frame.inverted()
records = {}
for name in section_config["owners"]:
    part = bpy.data.objects[name]
    if part.type != "MESH" or part.mode != "OBJECT" or part.modifiers or part.data.shape_keys:
        raise ValueError("section observation requires an unmodified rigid object mesh")
    sections = []
    for coordinate in section_config["planes_x_mm"]:
        editable = bmesh.new()
        try:
            editable.from_mesh(part.data)
            if not editable.faces or any(not edge.is_manifold for edge in editable.edges):
                raise ValueError("section source must be a nonempty closed manifold mesh")
            editable.transform(inverse @ part.matrix_world)
            cut = bmesh.ops.bisect_plane(editable,
                geom=[*editable.verts,*editable.edges,*editable.faces],
                dist=0.0,plane_co=Vector((coordinate/1000,0,0)),
                plane_no=Vector((1,0,0)),clear_inner=False,clear_outer=False)
            edges = {edge for edge in cut["geom_cut"] if isinstance(edge,bmesh.types.BMEdge)}
            neighbors = {vertex:[] for edge in edges for vertex in edge.verts}
            for edge in edges:
                first,second = edge.verts
                neighbors[first].append(second)
                neighbors[second].append(first)
            if any(len(adjacent)!=2 for adjacent in neighbors.values()):
                raise ValueError("section intersection has an open or branching contour")
            remaining = set(neighbors)
            loops = []
            while remaining:
                start = next(iter(remaining))
                previous,current = None,start
                points = []
                while True:
                    if current not in remaining:
                        raise ValueError("section contour revisited a non-start vertex")
                    points.append(tuple(float(v)*1000 for v in current.co))
                    remaining.remove(current)
                    following = next(v for v in neighbors[current] if v!=previous)
                    previous,current = current,following
                    if current==start:
                        break
                offset = min(range(len(points)),key=lambda index:points[index])
                points = points[offset:]+points[:offset]
                reverse = [points[0],*reversed(points[1:])]
                points = min(points,reverse)
                loops.append({"closed":True,"points_mm":points})
            loops.sort(key=lambda row:(row["points_mm"][0],len(row["points_mm"])))
            sections.append({"plane_x_mm":coordinate,"loops":loops})
        finally:
            editable.free()
    records[name] = sections
print("SECTION_PROBE:"+json.dumps({"scope":"raw closed mesh sections only; not hole or assembly acceptance","frame":section_config["frame"],"parts":records}))
"""
    )
    return "exec(" + repr(program) + ", {})\n"


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
