"""Regenerate the rotary concept and exercise a broken-link negative control."""

from pathlib import Path

from scripts.verify.generated_artifact_verify_real import BlenderSocketOracle
from src.infrastructure.narrowing import as_finite_number, as_sequence
from src.verification.artifact_files import binary_stl_metrics
from src.verification.generator_imports import reload_modules_for


def main() -> None:
    script = Path(__file__).resolve().parents[1] / "model_lab_rotary.py"
    root = script.parents[1]
    modules = reload_modules_for(root, script)
    code = f"""import runpy, bpy, json, importlib, sys
if {str(root)!r} not in sys.path:
    sys.path.insert(0, {str(root)!r})
for name in {modules!r}:
    importlib.reload(importlib.import_module(name))
model = runpy.run_path({str(script)!r}, run_name='__main__')
chassis = bpy.data.objects['LS_FIT_chassis']
saved_chassis = chassis.data.copy()
try:
    plug = model['add_cylinder']('LR_TOOL_lid_collision', 2, 1, (-88, 45, 76))
    model['boolean'](chassis, plug, 'UNION')
    try:
        model['verify_base_mounts']()
    except ValueError as error:
        if 'Base support penetrates lid' not in str(error):
            raise
        (model['OUTPUT'] / 'red-base-lid.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Tower penetration into lid was accepted')
finally:
    changed = chassis.data
    chassis.data = saved_chassis
    if changed.users == 0:
        bpy.data.meshes.remove(changed)
model['verify_base_mounts']()
stop = bpy.data.objects['LR_BASE_capillary_washer_upper']
saved_stop = stop.matrix_world.copy()
try:
    stop.location.x += 0.1
    bpy.context.view_layer.update()
    try:
        model['verify_base_mounts']()
    except ValueError as error:
        if 'Base retaining stop absent' not in str(error):
            raise
        (model['OUTPUT'] / 'red-base-stop.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Disconnected base stop was accepted')
finally:
    stop.matrix_world = saved_stop
    bpy.context.view_layer.update()
model['verify_base_mounts']()
import bmesh
support = bpy.data.objects['LR_capillary_support_envelope_0']
original_mesh = support.data
broken_mesh = original_mesh.copy()
support.data = broken_mesh
edit = bmesh.new()
edit.from_mesh(broken_mesh)
edit.faces.ensure_lookup_table()
bmesh.ops.delete(edit, geom=[edit.faces[0]], context='FACES_ONLY')
edit.to_mesh(broken_mesh)
edit.free()
try:
    try:
        model['verify_rotary_support_meshes']()
    except ValueError as error:
        if 'Rotary support mesh invalid' not in str(error):
            raise
        (model['OUTPUT'] / 'red-support-mesh.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Open support mesh was accepted')
finally:
    support.data = original_mesh
    bpy.data.meshes.remove(broken_mesh)
model['verify_rotary_support_meshes']()
bolt = bpy.data.objects['LR_capillary_elbow_bolt']
original_bolt_mesh = bolt.data.copy()
center = bpy.data.objects['LR_PIVOT_capillary_elbow'].matrix_world.translation * 1000
try:
    plug = model['add_cylinder']('LR_TOOL_closed_drive', 2.6, 3.8, (center.x - 31.3, center.y, center.z), 'X')
    model['boolean'](bolt, plug, 'UNION')
    try:
        model['verify_rotary_elbow_tools']()
    except ValueError as error:
        if 'Rotary elbow tool obstructed' not in str(error):
            raise
        (model['OUTPUT'] / 'red-elbow-drive.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Closed hex drive was accepted')
finally:
    changed_mesh = bolt.data
    bolt.data = original_bolt_mesh
    if changed_mesh.users == 0:
        bpy.data.meshes.remove(changed_mesh)
model['verify_rotary_elbow_tools']()
fork = bpy.data.objects['LR_capillary_support_envelope_1']
saved_fork_location = fork.location.copy()
try:
    fork.location.y += 0.1
    bpy.context.view_layer.update()
    try:
        model['verify_rotary_wrist_interfaces']()
    except ValueError as error:
        if 'Rotary wrist' not in str(error):
            raise
        (model['OUTPUT'] / 'red-wrist-disconnection.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Disconnected wrist was accepted')
finally:
    fork.location = saved_fork_location
    bpy.context.view_layer.update()
model['verify_rotary_wrist_interfaces']()
joint = bpy.data.objects['LR_PIVOT_capillary_yaw']
failed_driver = joint.animation_data.drivers[0].driver
saved_expression = failed_driver.expression
try:
    failed_driver.expression = '0'
    try:
        model['verify_rotary_articulation']()
    except ValueError as error:
        if 'Articulation independence failed' not in str(error):
            raise
        (model['OUTPUT'] / 'red-articulation.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Disabled articulation driver was accepted')
finally:
    failed_driver.expression = saved_expression
    joint.update_tag()
    bpy.context.view_layer.update()
model['verify_rotary_articulation']()
hinge = bpy.data.objects['LR_capillary_hinge_0']
rotation = hinge.animation_data.drivers[0].driver
original = rotation.expression
try:
    rotation.expression = '0'
    try:
        model['verify']()
    except ValueError as error:
        if 'physical pivot' not in str(error):
            raise
        (model['OUTPUT'] / 'red-broken-link.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Broken rotary linkage was accepted')
finally:
    rotation.expression = original
    hinge.update_tag()
    bpy.context.view_layer.update()
model['verify']()
source = bpy.data.objects['LR_pH_temp_probe_pH']
fixture = source.copy()
fixture.data = source.data.copy()
fixture.name = 'LR_capillary_intrusion_fixture'
bpy.context.collection.objects.link(fixture)
fixture.parent = None
fixture.matrix_world = source.matrix_world.copy()
fixture.location.x += 0.001
bpy.context.view_layer.update()
try:
    try:
        model['verify_coupled_motion']()
    except ValueError as error:
        if 'Cross-head rotary collision' not in str(error):
            raise
        (model['OUTPUT'] / 'red-cross-head.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Cross-head intrusion was accepted')
finally:
    bpy.data.objects.remove(fixture, do_unlink=True)
model['verify_coupled_motion']()
print('Rotary concept motion and broken-link control passed; no load or print qualification')
"""
    oracle = BlenderSocketOracle("127.0.0.1", 9876)
    print(oracle.execute(code))
    dimensions = oracle.execute_json("""import bpy, json
rows = {}
for obj in bpy.data.objects:
    if obj.name.startswith('LR_CHECK_'):
        points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        rows[obj.name] = [(max(p[a] for p in points)-min(p[a] for p in points))*1000 for a in range(3)]
print(json.dumps(rows))
""")
    if len(dimensions) != 4:
        raise ValueError("Rotary STL comparison requires exactly four meshes")
    for name, expected in dimensions.items():
        values = as_sequence(expected)
        if values is None or len(values) != 3:
            raise ValueError("Invalid source dimensions")
        wanted_dimensions = [as_finite_number(value) for value in values]
        if any(value is None for value in wanted_dimensions):
            raise ValueError("Non-finite source dimensions")
        metrics = binary_stl_metrics(
            (root / "tmp/lab-station-rotary/fit-prototypes" / (name + "_mm.stl")).read_bytes()
        )
        if any(
            wanted is None or abs(actual - wanted) > 0.02
            for actual, wanted in zip(metrics.dimensions_mm, wanted_dimensions, strict=True)
        ):
            raise ValueError(f"Rotary STL dimensions differ: {name}")
    print("Four binary STL dimensions match Blender world vertices within 0.02 mm")


if __name__ == "__main__":
    main()
