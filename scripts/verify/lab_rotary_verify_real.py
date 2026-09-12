"""Regenerate the rotary concept and exercise a broken-link negative control."""

from pathlib import Path

from scripts.verify.generated_artifact_verify_real import BlenderSocketOracle
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
    print(BlenderSocketOracle("127.0.0.1", 9876).execute(code))


if __name__ == "__main__":
    main()
