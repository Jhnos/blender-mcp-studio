"""Real-Blender control: every serrated-joint Boolean must leave a valid closed surface.

The V10 arm readiness failure traced to one Boolean, not to finishing: a tooth
plate whose bore ring shared the exact radius of the bore already cut through the
link. Two tessellations of one cylinder produce slivers that the later distance
weld hides but never removes. This control observes each Boolean of the formal
`connect_serrated_joint` on the actual arm geometry and rejects any stage that
leaves zero-area triangles, open edges or self-intersecting triangle pairs, then
checks the integrated links and HMI back shell with the independent CGAL solver.
The actual screen-ear steps and radial bore probes exercise the same invariant. A deliberately
tangent bore control must still be rejected, so a silent oracle cannot pass.
"""

import hashlib
import json
from pathlib import Path

from scripts.verify.generated_artifact_verify_real import BlenderSocketOracle
from src.infrastructure.narrowing import as_nonempty_sequence, as_str_keyed_exact, required
from src.verification.artifact_files import binary_stl_surface
from src.verification.generator_imports import reload_modules_for
from src.verification.mesh_integrity import require_triangle_surface


def verify_screen_fold_binding(root: Path) -> None:
    """Real dependency-graph readback in both directions, preserving fixture ownership."""
    code = f"""import bpy,importlib,json,math,runpy
for name in ('src.core.domain.lab_station_joints','scripts.lab_station_rig','scripts.lab_station_joints'):
    importlib.reload(importlib.import_module(name))
namespace=runpy.run_path({str(root / "scripts/lab_station_screen_control.py")!r})
objects_before=set(bpy.data.objects)
try:
    screen=bpy.data.objects.new('SCREEN_SEQUENCE_fixture',None);bpy.context.collection.objects.link(screen)
    screen.location=(0,-.049,.124);screen['fold_angle_deg']=60.0
    child=bpy.data.objects.new('SCREEN_SEQUENCE_child',None);bpy.context.collection.objects.link(child)
    child.parent=screen;child.location=(.02,.03,.04)
    screw=bpy.data.objects.new('SCREEN_SEQUENCE_screw',None);bpy.context.collection.objects.link(screw)
    screw.location=(0,.008,.009)
    namespace['driver'](screen,screen,'rotation_euler',0,'(fold_angle_deg-60)*pi/180',('fold_angle_deg',))
    try:namespace['driver'](screw,screen,'location',0,'progress',('progress',),property_paths=())
    except ValueError:pass
    else:raise AssertionError('Mismatched driver variable bindings accepted')
    assert screw.animation_data is None,'Invalid variable binding mutated the screw'
    for invalid in ('same_part','wrong_pose','parented_screw','wrong_rotation'):
        screen['fold_angle_deg']=30.0 if invalid=='wrong_pose' else 60.0
        screw.parent=screen if invalid=='parented_screw' else None
        screen.rotation_mode='QUATERNION' if invalid=='wrong_rotation' else 'XYZ'
        try:namespace['bind_screen_fold_control'](screen,screen if invalid=='same_part' else screw)
        except ValueError:pass
        else:raise AssertionError('Invalid screen binding was accepted: '+invalid)
        assert '收折進度' not in screen and screw.animation_data is None,'Rejected binding mutated parts'
    screen.rotation_mode='XYZ';screen['fold_angle_deg']=60.0;screw.parent=None
    namespace['bind_screen_fold_control'](screen,screw)
    fixture_path={str(root / "tmp/lab-station-route-engine/screen-controller-fixture.blend")!r}
    from pathlib import Path
    Path(fixture_path).parent.mkdir(parents=True,exist_ok=True)
    bpy.data.libraries.write(fixture_path,{{screen,screw,child}})
    with bpy.data.libraries.load(fixture_path,link=False) as (source,destination):
        names=tuple(source.objects);destination.objects=list(names)
    loaded=dict(zip(names,destination.objects))
    for obj in destination.objects:bpy.context.collection.objects.link(obj)
    maximum=0.0;total=0
    fixtures=((screen,screw,child),(loaded[screen.name],loaded[screw.name],loaded[child.name]))
    for screen,screw,child in fixtures:
     observed=[]
     for progress in list(range(101))+list(range(100,-1,-1)):
         screen['收折進度']=float(progress);screen.update_tag();bpy.context.view_layer.update()
         q=progress/20
         # Independent phase cases; do not call the production pose evaluator.
         if q<=1:angle,release,travel=60,0,2*q
         elif q<=2:angle,release,travel=60,2*(q-1),2
         elif q<=3:angle,release,travel=60*(3-q),2,2
         elif q<=4:angle,release,travel=0,2*(4-q),2
         else:angle,release,travel=0,0,2*(5-q)
         actual=(screen.rotation_euler.x,screen.location.x,screw.location.x,screen['fold_angle_deg'])
         expected=(math.radians(angle-60),release/1000,travel/1000,angle)
         maximum=max(maximum,max(abs(a-b) for a,b in zip(actual,expected)))
         from mathutils import Matrix,Vector
         expected_child=Matrix.Translation((expected[1],-.049,.124)) @ Matrix.Rotation(expected[0],4,'X') @ Vector((.02,.03,.04))
         assert (child.matrix_world.translation-expected_child).length<1e-7,f'Screen child did not follow evaluated controller at {{progress}}: {{tuple(child.matrix_world.translation)}} expected {{tuple(expected_child)}} channels {{actual}}'
         observed.append(tuple(round(v,7) for v in actual))
     assert maximum<1e-5,f'Screen drivers disagree with the operation sequence: {{maximum}}'
     assert observed[:101]==list(reversed(observed[101:])),'Reverse operation depends on hidden state'
     for owner in (screen,screw):
         for curve in owner.animation_data.drivers:
             assert curve.driver.is_valid,'Invalid or cyclic screen driver'
             assert not curve.keyframe_points and not curve.modifiers,'Expression output is remapped'
             assert len(curve.driver.variables)==1,'Old driver variables were retained'
             assert curve.driver.variables[0].targets[0].data_path=='["收折進度"]'
     total+=len(observed)
    print(json.dumps({{'samples':total,'maximum_channel_error':maximum,'forward_reverse_match':True}}))
finally:
    for obj in list(bpy.data.objects):
        if obj not in objects_before:bpy.data.objects.remove(obj,do_unlink=True)
"""
    result = BlenderSocketOracle("127.0.0.1", 9876).execute_json(code)
    print("Screen fold sequence and evaluated descendants passed:", result)


def verify_serrated_joint_integration(root: Path) -> None:
    """Observe each formal joint Boolean on real arm geometry; reject any defect."""
    verify_screen_fold_binding(root)
    script = root / "scripts/model_lab_station.py"
    modules = reload_modules_for(root, script)
    code = f"""import bpy, bmesh, importlib, json, math, runpy, sys
from pathlib import Path
from mathutils import Vector
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
joints = importlib.import_module('scripts.lab_station_joints')
original_joints_boolean = joints.boolean
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
    # Actual HMI back shell before its production ear integration; no finish/weld.
    back = model['box']('JOINT_control_screen', (150, 110, 36), (0, 0, -18), mat)
    original(back, model['box']('JOINT_control_cut', (144, 104, 38), (0, 0, -13), mat), 'DIFFERENCE')
    for x in (-69.0, 69.0):
        for y in (-49.0, 49.0):
            original(back, model['cylinder']('JOINT_control_boss', 4, 31, (x, y, -16.5), mat), 'UNION')
            model['hole'](back, (x, y, -5), 1.6, 12)
    original(back, model['box']('JOINT_control_cut', (50, 10, 18), (0, -54, -16), mat), 'DIFFERENCE')
    tracked[back.name] = 'screen'
    rows.append({{'part': 'screen', 'stage': 'input', **inspect(back)[0]}})
    joints.boolean = observed
    joints.add_screen_ears(back, mat)
    row, mesh = inspect(back)
    rows.append({{'part': 'screen', 'stage': 'integrated', **row}})
    if mesh is not None:
        finals['screen'] = mesh
    # Independent spatial probes: both bores clear at r=2.7 mm; r=2.9 hits material.
    back.data.calc_loop_triangles()
    tree = BVHTree.FromPolygons(
        [back.matrix_world @ v.co for v in back.data.vertices],
        [tuple(t.vertices) for t in back.data.loop_triangles], all_triangles=True)
    bore_controls = []
    for side in (-1, 1):
        for radius, expected in ((2.7, False), (2.9, True)):
            for index in range(16):
                angle = index * math.tau / 16
                origin = Vector((side * .086, (-55 + radius * math.cos(angle)) / 1000, radius * math.sin(angle) / 1000))
                hit = tree.ray_cast(origin, Vector((-side, 0, 0)), .0144)[0] is not None
                bore_controls.append({{'side': side, 'radius_mm': radius, 'index': index, 'hit': hit, 'expected': expected}})
    # Exercise the production print-origin placement and millimetre STL exporter.
    model['export_prototype'].__globals__['OUTPUT'] = Path(project) / 'tmp/lab-station-route-engine/screen-source-control'
    model['export_prototype'](back, 'lcd_back')
    control = model['beam']('JOINT_control_tangent', necks[1], lower_end, mat)
    x, y, z = elbow
    original(control, primitives.add_cylinder('JOINT_control_hub', 14, 20, (x + 14, y, z), 'X'), 'UNION')
    original(control, primitives.add_cylinder('JOINT_control_bore', 2.7, 70, elbow, 'X'), 'DIFFERENCE')
    original(control, arm['placed_plate']('JOINT_control_teeth', mat, (x + 4.7, y, z), -1, 2.7), 'UNION')
    tangent, _ = inspect(control)
finally:
    namespace['boolean'] = original
    joints.boolean = original_joints_boolean
    for obj in list(bpy.data.objects):
        if obj.name not in objects_before:
            bpy.data.objects.remove(obj, do_unlink=True)
    for name in list(bpy.data.meshes.keys()):
        if name not in meshes_before and bpy.data.meshes[name].users == 0:
            bpy.data.meshes.remove(bpy.data.meshes[name])
print(json.dumps({{'rows': rows, 'tangent_control': tangent, 'finals': finals, 'bore_controls': bore_controls}}))
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
    bore_controls = [
        required(row, as_str_keyed_exact, message="Malformed bore probe", error=ValueError)
        for row in required(
            result.get("bore_controls"),
            as_nonempty_sequence,
            message="Missing bore probes",
            error=ValueError,
        )
    ]
    if len(bore_controls) != 64 or any(
        row.get("hit") != row.get("expected") for row in bore_controls
    ):
        raise AssertionError(f"Screen bores changed: {bore_controls}")
    failures = [
        row
        for row in rows
        if row.get("rejected")
        or row.get("zero_area")
        or row.get("thin")
        or row.get("open_edges")
        or row.get("self_pairs")
    ]
    expected_finals = {"upper", "lower", "rotor", "rotor_yaw", "screen"}
    if set(finals) != expected_finals:
        failures.append({"stage": "integrated", "missing": sorted(expected_finals - set(finals))})
    errors: dict[str, str] = {}
    for part, raw in finals.items():
        mesh = required(raw, as_str_keyed_exact, message="Malformed mesh payload", error=ValueError)
        try:
            require_triangle_surface(mesh)
        except ValueError as error:
            errors[part] = str(error)
    exported_reports: dict[str, dict[str, object]] = {}
    exported_paths = {
        "screen_stl": root
        / "tmp/lab-station-route-engine/screen-source-control/fit-prototypes/lcd_back_mm.stl",
        "screen_production_stl": root / "tmp/lab-station-v10/fit-prototypes/lcd_back_mm.stl",
    }
    for name, path in exported_paths.items():
        payload = path.read_bytes()
        try:
            measured = require_triangle_surface(binary_stl_surface(payload))
            exported_reports[name] = {"sha256": hashlib.sha256(payload).hexdigest(), **measured}
        except ValueError as error:
            errors[name] = str(error)
    output = root / "tmp/lab-station-route-engine/serrated-joint-stages.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "rows": rows,
                "tangent_control": tangent,
                "cgal_errors": errors,
                "bore_controls": bore_controls,
                "exported_stl": exported_reports,
            },
            indent=1,
        )
    )
    if not (tangent.get("rejected") or tangent.get("zero_area") or tangent.get("self_pairs")):
        raise AssertionError(f"Tangent bore control was accepted: {tangent}")
    if failures or errors:
        raise ValueError(f"Serrated joint Booleans left defects: stages={failures} cgal={errors}")
    print(
        f"{len(rows)} Boolean stages, {len(bore_controls)} bore probes, {len(exported_reports)} STL files and tangent-bore control passed"
    )
