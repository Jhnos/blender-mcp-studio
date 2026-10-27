"""Real coupon export + independent mating-surface positive/negative controls."""

import json
from collections.abc import Sequence
from math import atan2, cos, hypot, pi, sin
from pathlib import Path

from scripts.verify.generated_artifact_verify_real import BlenderSocketOracle
from src.core.domain.lab_station_joints import SerratedJointSpec
from src.core.planning.serrated_contact_plan import Triangle, plan_contact_triangulation
from src.verification.artifact_files import binary_stl_surface
from src.verification.generator_imports import reload_modules_for
from src.verification.mesh_integrity import (
    cgal_self_intersects,
    parse_closed_surface,
    require_triangle_surface,
)


def verify_serrated_contact_plan(root: Path) -> None:
    """Exercise existing Blender geometry/export, then use CGAL on complete solids."""
    output = root / "tmp/lab-station-route-engine/contact-plan"
    output.mkdir(parents=True, exist_ok=True)
    modules = reload_modules_for(root, root / "scripts/lab_station_joints.py")
    code = f"""import bpy,importlib,json,sys
from pathlib import Path
project={str(root)!r}
if project not in sys.path:sys.path.insert(0,project)
for name in {modules!r}:
    importlib.reload(importlib.import_module(name))
joints=importlib.reload(importlib.import_module('scripts.lab_station_joints'))
exporter=importlib.reload(importlib.import_module('scripts.blender_artifact_export'))
objects_before=set(bpy.data.objects);meshes_before=set(bpy.data.meshes)
try:
    body=joints.serrated_plate('CONTACT_PATCH_fixture',None)
    exporter.export_stl_mm([body],Path({str(output / "source.stl")!r}))
finally:
    for o in list(bpy.data.objects):
        if o not in objects_before:bpy.data.objects.remove(o,do_unlink=True)
    for m in list(bpy.data.meshes):
        if m not in meshes_before and m.users==0:bpy.data.meshes.remove(m)
assert set(bpy.data.objects)==objects_before
print(json.dumps({{'scene_preserved':True}}))
"""
    result = BlenderSocketOracle("127.0.0.1", 9876).execute_json(code)
    surface = binary_stl_surface((output / "source.stl").read_bytes())
    local, faces = parse_closed_surface(surface)
    # Independent rigid/reflected placement of the opposite-facing same coupon.
    spec = SerratedJointSpec()
    vertices = [(z, x, y) for x, y, z in local]
    angle = pi / spec.teeth
    mate = [
        (
            2 * spec.base_mm + spec.tooth_height_mm + spec.assembly_gap_mm - x,
            y * cos(angle) - z * sin(angle),
            y * sin(angle) + z * cos(angle),
        )
        for x, y, z in vertices
    ]
    reversed_faces = [(f[2], f[1], f[0]) for f in faces]
    bounds = (
        spec.base_mm - 0.01,
        spec.base_mm + spec.tooth_height_mm + spec.assembly_gap_mm + 0.01,
    )
    one = plan_contact_triangulation(vertices, faces, spec, axial_bounds_mm=bounds)
    two = plan_contact_triangulation(mate, reversed_faces, spec, axial_bounds_mm=bounds)
    for points, triangles in ((vertices, one.faces), (mate, two.faces)):
        require_triangle_surface({"vertices": points, "faces": triangles})

    def intersects(
        left_faces: Sequence[Triangle], right_faces: Sequence[Triangle], stroke: float
    ) -> bool:
        points = vertices + [(x - stroke, y, z) for x, y, z in mate]
        triangles = list(left_faces) + [
            (a + len(vertices), b + len(vertices), c + len(vertices)) for a, b, c in right_faces
        ]
        return cgal_self_intersects(points, triangles)

    # Keep a deliberately incompatible diagonal on one mate, while preserving vertices.
    wrong = list(two.faces)
    cells: dict[int, tuple[list[int], dict[tuple[int, int], int]]] = {}
    count = spec.teeth * 8
    for fi in two.face_indices:
        corners = {
            (
                int(hypot(mate[i][1], mate[i][2]) > 12),
                round(atan2(mate[i][2], mate[i][1]) * count / (2 * pi)) % count,
            ): i
            for i in two.faces[fi]
        }
        qs = {q for _, q in corners}
        q = next(q for q in qs if (q + 1) % count in qs)
        ids, index = cells.setdefault(q, ([], {}))
        ids.append(fi)
        index.update(corners)
    for q, (ids, index) in cells.items():
        a, b, c, d = [
            index[k] for k in ((0, q), (1, q), (1, (q + 1) % count), (0, (q + 1) % count))
        ]
        wrong[ids[0]], wrong[ids[1]] = (d, b, a), (d, c, b)
    require_triangle_surface({"vertices": mate, "faces": wrong})
    assert intersects(one.faces, wrong, 0.05), "Opposite diagonal control did not fire"
    rows = []
    for stroke in (0, 0.05, 0.1, 0.15, 0.19, 0.199):
        crossed = intersects(one.faces, two.faces, stroke)
        assert not crossed, (stroke, crossed)
        rows.append({"seating_stroke_mm": stroke, "crossed": crossed})
    assert intersects(one.faces, two.faces, 0.21), "Overtravel control did not fire"
    report = {
        "scene_preserved": result["scene_preserved"],
        "patched_triangles_per_part": len(one.face_indices),
        "opposite_diagonal_rejected": True,
        "overtravel_rejected": True,
        "rows": rows,
        "scope": "Real exported coupon only; not current delivery clamp/thread/printing qualification.",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2))
    print("Shared contact triangulation passed:", report)
