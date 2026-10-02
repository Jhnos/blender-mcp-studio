"""Fresh-command readbacks and transfer scenarios for saved electrode artifacts."""

from pathlib import Path

from scripts.verify.generated_artifact_verify_real import BlenderSocketOracle


def verify_saved_electrode(script: Path) -> None:
    # A fresh addon command lets Blender refresh context after opening the saved artifact.
    code = f"""import bpy, runpy, json
model = runpy.run_path({str(script)!r})
gaps = {{label: {{joint: model['verify_seated'](label, joint) for joint in ('shoulder', 'elbow', 'tip')}} for label in ('capillary', 'pH_temp')}}
model['verify_forearm_stack']()
model['verify_wrist_geometry']()
wrist = {{label: model['verify_wrist_faces'](label, 0) for label in ('capillary', 'pH_temp')}}
(model['OUTPUT'] / 'wrist-file-check.json').write_text(json.dumps(wrist))
(model['OUTPUT'] / 'seated-file-check.json').write_text(json.dumps(gaps))
for label in ('capillary', 'pH_temp'):
    model['set_electrode_wrist_pose'](label, 0, 2)
    model['verify_wrist_faces'](label, 2.2)
    model['verify_interference'](label, 'tip')
    model['set_electrode_wrist_pose'](label, 0, 0)
    model['verify_wrist_faces'](label, 0.2)
    model['apply_take_up'](label, model['closure_spec']('tip').stroke_mm, 'tip')
    for joint in ('shoulder', 'elbow', 'tip'):
        model['verify_seated'](label, joint)
    model['verify_interference'](label, 'tip')
print('Saved three-joint seating and wrist reopening passed')
bpy.ops.wm.open_mainfile(filepath=str(model['OUTPUT'] / 'service.blend'))
"""
    print(BlenderSocketOracle("127.0.0.1", 9876, timeout=30).execute(code))
    code = f"""import bpy, runpy, json, math
model = runpy.run_path({str(script)!r})
angles = {{}}
for label in ('capillary', 'pH_temp'):
    model['verify_pose'](label)
    head = bpy.data.objects[f'S_{{label}}_head'].matrix_world
    pivot = bpy.data.objects[f'S_{{label}}_tip_bolt'].matrix_world
    angles[label] = math.degrees((pivot.inverted() @ head).to_quaternion().angle)
    if abs(angles[label] - model['ElectrodeArmSpec']().wrist_indexed_angle(0, 100, 1)) > 0.01:
        raise ValueError('Saved service angle mismatch')
report = {{'wrist_tooth_gaps': {{label: model['verify_wrist_faces'](label, 0.2) for label in ('capillary', 'pH_temp')}}, 'wrist_angles_deg': angles, 'clamps': model['verify_clamps'](), 'pin_service_samples': model['verify_pin_service']()}}
(model['OUTPUT'] / 'service-file-check.json').write_text(json.dumps(report))
print('Saved service artifact passed angle and removal readback')
bpy.ops.wm.open_mainfile(filepath=str(model['OUTPUT'] / 'service-seated.blend'))
"""
    print(BlenderSocketOracle("127.0.0.1", 9876, timeout=60).execute(code))
    code = f"""import bpy, runpy, json
model = runpy.run_path({str(script)!r})
r = {{label: model['verify_seated'](label, 'tip') for label in ('capillary', 'pH_temp')}}
for label in ('capillary', 'pH_temp'):
    model['verify_interference'](label, 'tip')
(model['OUTPUT'] / 'service-seated-file-check.json').write_text(json.dumps(r))
bpy.ops.wm.open_mainfile(filepath=str(model['OUTPUT'] / 'wrist-released.blend'))
"""
    print(BlenderSocketOracle("127.0.0.1", 9876, timeout=60).execute(code))

    code = f"""import bpy, runpy, json
from mathutils import Matrix
model = runpy.run_path({str(script)!r})
wrist = {{label: model['verify_wrist_faces'](label, 2.2) for label in ('capillary', 'pH_temp')}}
for label in ('capillary', 'pH_temp'):
    model['verify_pose'](label)
(model['OUTPUT'] / 'wrist-release-file-check.json').write_text(json.dumps(wrist))
model['render_shoulder_transfer']()
part = bpy.data.objects['S_pH_temp_head']
saved = part.matrix_world.copy()
try:
    part.matrix_world = bpy.data.objects['S_capillary_upper'].matrix_world @ Matrix.Translation((0.0042, 0, 0.075))
    bpy.context.view_layer.update()
    try:
        model['verify_shoulder_transfer'](model['pose'])
    except ValueError as error:
        if 'S_pH_temp_head' not in str(error):
            raise
        (model['OUTPUT'] / 'red-shoulder-transfer-blocked.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Blocked shoulder transfer accepted')
finally:
    part.matrix_world = saved
    bpy.context.view_layer.update()
bpy.ops.wm.open_mainfile(filepath=str(model['OUTPUT'] / 'transfer-end-pH_temp.blend'))
"""
    print(BlenderSocketOracle("127.0.0.1", 9876, timeout=300).execute(code))
    code = f"""import bpy, runpy, json
model = runpy.run_path({str(script)!r})
gaps = {{joint: model['verify_seated']('pH_temp', joint) for joint in ('shoulder', 'elbow', 'tip')}}
model['verify_pins']('pH_temp')
(model['OUTPUT'] / 'transfer-file-check.json').write_text(json.dumps(gaps))
print('Saved shoulder transfer endpoint passed three bearing chains and pins')
bpy.ops.wm.open_mainfile(filepath=str(model['OUTPUT'] / 'arm-seated.blend'))
"""
    print(BlenderSocketOracle("127.0.0.1", 9876, timeout=30).execute(code))
