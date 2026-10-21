"""Real-Blender control: every serrated-joint Boolean must leave a valid closed surface.

The V10 arm readiness failure traced to one Boolean, not to finishing: a tooth
plate whose bore ring shared the exact radius of the bore already cut through the
link. Two tessellations of one cylinder produce slivers that the later distance
weld hides but never removes. This control observes each Boolean of the formal
`connect_serrated_joint` on the actual arm geometry and rejects any stage that
leaves zero-area triangles, open edges or self-intersecting triangle pairs, then
checks the integrated links with the independent CGAL solver. A deliberately
tangent bore control must still be rejected, so a silent oracle cannot pass.
"""

import json
from pathlib import Path

from scripts.verify.generated_artifact_verify_real import BlenderSocketOracle
from src.infrastructure.narrowing import as_nonempty_sequence, as_str_keyed_exact, required
from src.verification.generator_imports import reload_modules_for
from src.verification.mesh_integrity import require_triangle_surface


def verify_serrated_joint_integration(root: Path) -> None:
    """Observe each formal joint Boolean on real arm geometry; reject any defect."""
    script = root / "scripts/model_lab_station.py"
    modules = reload_modules_for(root, script)
    code = f"""import bpy, bmesh, importlib, json, runpy, sys
from mathutils.bvhtree import BVHTree
project = {str(root)!r}
if project not in sys.path:
    sys.path.insert(0, project)
for name in {modules!r}:
    importlib.reload(importlib.import_module(name))
arm = runpy.run_path(project + '/scripts/lab_station_arm.py')
base = runpy.run_path(project + '/scripts/lab_station_base.py')
model = runpy.run_path(project + '/scripts/model_lab_station.py')
primitives = importlib.import_module('scripts.blender_mesh_primitives')
triangulation = importlib.import_module('scripts.blender_mesh_triangulation')
spec = importlib.import_module('src.core.domain.lab_station').LabStationSpec()
objects_before = {{o.name for o in bpy.data.objects}}
meshes_before = {{m.name for m in bpy.data.meshes}}
def inspect(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    try:
        triangulation.triangulate_faces(bm)
    except ValueError as error:
        bm.free()
        return {{'faces': len(obj.data.polygons), 'rejected': str(error)}}, None
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    zero = sum(1 for f in bm.faces if primitives.zero_area_triangle(f))
    thin = sum(1 for f in bm.faces if f.calc_area() < 1e-12)
    open_edges = sum(1 for e in bm.edges if not e.is_manifold)
    tree = BVHTree.FromBMesh(bm, epsilon=0.0)
    sets = [frozenset(v.index for v in f.verts) for f in bm.faces]
    pairs = sum(1 for l, r in tree.overlap(tree) if l < r and not (sets[l] & sets[r]))
    mesh = {{'vertices': [list(v.co) for v in bm.verts], 'faces': [[v.index for v in f.verts] for f in bm.faces]}}
    bm.free()
    return {{'faces': len(mesh['faces']), 'zero_area': zero, 'thin': thin, 'open_edges': open_edges, 'self_pairs': pairs}}, mesh
rows = []
tracked = {{}}
namespace = arm['connect_serrated_joint'].__globals__
original = namespace['boolean']
def observed(target, tool, operation):
    stage = tool.name + ':' + operation
    original(target, tool, operation)
    if target.name in tracked:
        rows.append({{'part': tracked[target.name], 'stage': stage, **inspect(target)[0]}})
namespace['boolean'] = observed
finals = {{}}
try:
    mat = primitives.material('LS_AMBER', (0.95, 0.47, 0.10, 1))
    side = -1
    root, elbow, wrist = spec.arm_points(side)
    necks = spec.elbow_necks(side)
    lower_end = (wrist[0], wrist[1], wrist[2] + 26)
    upper = model['beam']('JOINT_control_upper', spec.shoulder_neck(side), necks[0], mat)
    lower = model['beam']('JOINT_control_lower', necks[1], lower_end, mat)
    rotor = primitives.add_cylinder('JOINT_control_rotor', 26, 5, (root[0], root[1], 82.5))
    tracked = {{upper.name: 'upper', lower.name: 'lower', rotor.name: 'rotor'}}
    arm['connect_serrated_joint'](upper, lower, elbow, necks, 'control', mat, model['beam'])
    fixed_neck = (root[0] - 13, root[1], 84)
    arm['connect_serrated_joint'](rotor, upper, root, (fixed_neck, spec.shoulder_neck(side)), 'control', mat, model['beam'], 'shoulder')
    for obj in (upper, lower, rotor):
        row, mesh = inspect(obj)
        rows.append({{'part': tracked[obj.name], 'stage': 'integrated', **row}})
        if mesh is not None:
            finals[tracked[obj.name]] = mesh
    # The rotary base drills its yaw bolt through the finished shoulder rotor.
    arm['finish_link'](rotor)
    base['yaw_spigot'](rotor, root[0], root[1])
    row, mesh = inspect(rotor)
    rows.append({{'part': 'rotor', 'stage': 'yaw_spigot', **row}})
    if mesh is not None:
        finals['rotor_yaw'] = mesh
    control = model['beam']('JOINT_control_tangent', necks[1], lower_end, mat)
    x, y, z = elbow
    original(control, primitives.add_cylinder('JOINT_control_hub', 14, 20, (x + 14, y, z), 'X'), 'UNION')
    original(control, primitives.add_cylinder('JOINT_control_bore', 2.7, 70, elbow, 'X'), 'DIFFERENCE')
    original(control, arm['placed_plate']('JOINT_control_teeth', mat, (x + 4.7, y, z), -1, 2.7), 'UNION')
    tangent, _ = inspect(control)
finally:
    namespace['boolean'] = original
    for obj in list(bpy.data.objects):
        if obj.name not in objects_before:
            bpy.data.objects.remove(obj, do_unlink=True)
    for name in list(bpy.data.meshes.keys()):
        if name not in meshes_before and bpy.data.meshes[name].users == 0:
            bpy.data.meshes.remove(bpy.data.meshes[name])
print(json.dumps({{'rows': rows, 'tangent_control': tangent, 'finals': finals}}))
"""
    result = BlenderSocketOracle("127.0.0.1", 9876, timeout=300).execute_json(code)
    rows = [
        required(row, as_str_keyed_exact, message="Malformed stage row", error=ValueError)
        for row in required(
            result.get("rows"), as_nonempty_sequence, message="Missing stage rows", error=ValueError
        )
    ]
    tangent = required(
        result.get("tangent_control"),
        as_str_keyed_exact,
        message="Missing control",
        error=ValueError,
    )
    finals = required(
        result.get("finals"),
        as_str_keyed_exact,
        message="Missing integrated meshes",
        error=ValueError,
    )
    failures = [
        row
        for row in rows
        if row.get("rejected")
        or row.get("zero_area")
        or row.get("thin")
        or row.get("open_edges")
        or row.get("self_pairs")
    ]
    expected_finals = {"upper", "lower", "rotor", "rotor_yaw"}
    if set(finals) != expected_finals:
        failures.append({"stage": "integrated", "missing": sorted(expected_finals - set(finals))})
    errors: dict[str, str] = {}
    for part, raw in finals.items():
        mesh = required(raw, as_str_keyed_exact, message="Malformed mesh payload", error=ValueError)
        try:
            require_triangle_surface(mesh)
        except ValueError as error:
            errors[part] = str(error)
    output = root / "tmp/lab-station-route-engine/serrated-joint-stages.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"rows": rows, "tangent_control": tangent, "cgal_errors": errors}, indent=1)
    )
    if not (tangent.get("rejected") or tangent.get("zero_area") or tangent.get("self_pairs")):
        raise AssertionError(f"Tangent bore control was accepted: {tangent}")
    if failures or errors:
        raise ValueError(f"Serrated joint Booleans left defects: stages={failures} cgal={errors}")
    print(f"{len(rows)} serrated joint Boolean stages and tangent-bore control passed")
