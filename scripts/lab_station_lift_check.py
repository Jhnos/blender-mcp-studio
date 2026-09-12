"""Artifact-level extraction verification, including a conservative full-stroke hull."""

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from scripts.lab_station_motion_check import tree, verify_motion
from scripts.lab_station_rig import set_pose


def owned_by(obj: bpy.types.Object, ancestor: bpy.types.Object) -> bool:
    while obj is not None:
        if obj == ancestor:
            return True
        obj = obj.parent
    return False


def vertices(obj: bpy.types.Object) -> list[Vector]:
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def sweep(obj: bpy.types.Object, travel: float) -> BVHTree:
    """A convex enclosure of all intermediate geometry: conservative, never undersized."""
    mesh = bmesh.new()
    for point in vertices(obj):
        mesh.verts.new(point)
        mesh.verts.new(point + Vector((0, 0, travel / 1000)))
    bmesh.ops.convex_hull(mesh, input=list(mesh.verts))
    result = BVHTree.FromBMesh(mesh)
    mesh.free()
    return result


def inside(point: Vector, solid: BVHTree) -> bool:
    direction = Vector((1, 0.371, 0.217)).normalized()
    origin = point.copy()
    for count in range(1000):
        hit, _, _, _ = solid.ray_cast(origin, direction)
        if hit is None:
            return count % 2 == 1
        origin = hit + direction * 1e-7
    raise ValueError("Containment ray did not terminate")


def verify_lifts(travel: float = 100) -> dict[str, object]:
    all_meshes = [
        o
        for o in bpy.context.scene.objects
        if o.type == "MESH"
        and o.name.startswith("LS_")
        and not o.name.startswith(("LS_CHECK_", "LS_DIAG_"))
        and not o.hide_render
    ]
    assert all_meshes, "Empty assembly is not evidence"
    reports = []
    probe_names = {
        "capillary": ("LS_REF_glass_capillary",),
        "pH_temp": ("LS_REF_E201C", "LS_REF_DS18B20"),
    }
    for label, names in probe_names.items():
        control = bpy.data.objects["LS_CTRL_" + label]
        slide = bpy.data.objects["LS_PIVOT_" + label + "_slide"]
        moving = [o for o in all_meshes if owned_by(o, slide)]
        fixed = [o for o in all_meshes if o not in moving]
        rods = [o for o in fixed if o.name.startswith("LS_REF_" + label + "_guide_rod_")]
        assert len(moving) >= 3 and len(rods) == 2 and len(fixed) >= 20
        fixed_matrices = {o.name: o.matrix_world.copy() for o in fixed}
        fixed_trees = {o.name: tree(o) for o in fixed}
        probes = [bpy.data.objects[name] for name in names]
        initial = {o.name: vertices(o) for o in probes}
        samples = []
        try:
            for height in range(0, int(travel) + 1, 5):
                set_pose(control, probe_slide_mm=height)
                moving_trees = {o.name: tree(o) for o in moving}
                intersections = [
                    (a.name, b.name)
                    for a in moving
                    for b in fixed
                    if moving_trees[a.name].overlap(fixed_trees[b.name])
                ]
                drift = max(
                    abs(o.matrix_world[i][j] - fixed_matrices[o.name][i][j])
                    for o in fixed
                    for i in range(4)
                    for j in range(4)
                )
                xy = max(
                    abs(v[axis] - initial[o.name][i][axis]) * 1000
                    for o in probes
                    for i, v in enumerate(vertices(o))
                    for axis in (0, 1)
                )
                samples.append(
                    {
                        "height_mm": height,
                        "intersections": intersections,
                        "fixed_matrix_delta": drift,
                        "xy_drift_mm": xy,
                    }
                )
                if intersections or drift > 1e-8 or xy > 0.01:
                    raise ValueError(f"Extraction {label}: {samples[-1]}")
            bottoms = {o.name: min(v.z for v in vertices(o)) * 1000 for o in probes}
            if min(bottoms.values()) < 120:
                raise ValueError(f"Probe remains below clearance plane: {bottoms}")
            carrier = bpy.data.objects["LS_FIT_" + label + "_lift_carrier"]
            zmin, zmax = min(v.z for v in vertices(carrier)), max(v.z for v in vertices(carrier))
            for rod in rods:
                rz = [v.z for v in vertices(rod)]
                assert min(rz) < zmin - travel / 1000 and max(rz) > zmax
            set_pose(control, probe_slide_mm=0)
            swept_hits = []
            for a in moving:
                swept = sweep(a, travel)
                # The enclosing hull fills intentional rod bores. Actual rods were
                # checked against the real carrier above; never exempt other obstacles.
                for b in fixed:
                    if b in rods:
                        continue
                    if (
                        swept.overlap(fixed_trees[b.name])
                        or inside(vertices(b)[0], swept)
                        or inside(vertices(a)[0], fixed_trees[b.name])
                    ):
                        swept_hits.append((a.name, b.name))
            if swept_hits:
                raise ValueError(f"Full-stroke envelope intersects {label}: {swept_hits}")
            reports.append(
                {
                    "head": label,
                    "moving": [o.name for o in moving],
                    "fixed": [o.name for o in fixed],
                    "samples": samples,
                    "tip_bottoms_mm": bottoms,
                    "swept_intersections": swept_hits,
                    "guide_rods": [o.name for o in rods],
                }
            )
        finally:
            set_pose(control, probe_slide_mm=0)
    return {
        "travel_mm": travel,
        "rim_mm": 110,
        "clearance_plane_mm": 120,
        "heads": reports,
        "scope": "Straight extraction at the documented arm pose; rigid geometry only, not load or cable qualification.",
    }


def verify_parking() -> dict[str, object]:
    """Sample both raised arms rotating outward; keep this separate from straight sweep proof."""
    controls = [bpy.data.objects["LS_CTRL_" + name] for name in ("capillary", "pH_temp")]
    meshes = [
        o
        for o in bpy.context.scene.objects
        if o.type == "MESH"
        and o.name.startswith("LS_")
        and not o.name.startswith(("LS_CHECK_", "LS_DIAG_"))
        and not o.hide_render
    ]
    samples = []
    try:
        for control in controls:
            set_pose(control, probe_slide_mm=100)
        for control, sign, label in zip(controls, (-1, 1), ("capillary", "pH_temp"), strict=True):
            moving = [o for o in meshes if owned_by(o, control)]
            fixed = [o for o in meshes if o not in moving and o.name != "LS_REF_" + label + "_root"]
            assert moving and fixed
            fixed_trees = {o.name: tree(o) for o in fixed}
            for angle in range(0, 46, 3):
                set_pose(control, yaw_deg=sign * angle)
                moving_trees = {o.name: tree(o) for o in moving}
                hits = [
                    (a.name, b.name)
                    for a in moving
                    for b in fixed
                    if moving_trees[a.name].overlap(fixed_trees[b.name])
                ]
                samples.append({"head": label, "yaw_deg": sign * angle, "intersections": hits})
                if hits:
                    raise ValueError(f"Raised parking path: {samples[-1]}")
    finally:
        for control in controls:
            set_pose(control, probe_slide_mm=0, yaw_deg=0)
    return {
        "samples": samples,
        "scope": "3-degree yaw samples with both probes raised; no continuous rotational sweep or self-collision qualification.",
    }


def verify_screen_at_lift_extremes() -> dict[str, object]:
    controls = [bpy.data.objects["LS_CTRL_" + name] for name in ("capillary", "pH_temp")]
    reports: dict[str, object] = {}
    try:
        for height in (0, 100):
            for control in controls:
                set_pose(control, probe_slide_mm=height)
            reports[str(height)] = verify_motion()
    finally:
        for control in controls:
            set_pose(control, probe_slide_mm=0)
    return reports
