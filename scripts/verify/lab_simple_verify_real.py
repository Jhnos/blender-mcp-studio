"""Run the reduced assembly study and a displaced-material negative control."""

from pathlib import Path

from scripts.verify.generated_artifact_verify_real import BlenderSocketOracle
from src.verification.generator_imports import reload_modules_for


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts/model_lab_simple.py"
    modules = reload_modules_for(root, script)
    code = f"""import bpy, importlib, runpy, sys, json
from mathutils import Matrix
from pathlib import Path
sys.path.insert(0, {str(root)!r})
for name in {modules!r}:
    importlib.reload(importlib.import_module(name))
model = runpy.run_path({str(script)!r}, run_name='__main__')
source = Path({str(root / "tmp/lab-station-v10/lab_station_v10.blend")!r}).resolve()
if any(Path(bpy.path.abspath(lib.filepath)).resolve() == source for lib in bpy.data.libraries):
    raise RuntimeError('Simple model retains the regenerable source as a library')
part = bpy.data.objects['S_capillary_upper']
saved = part.data.copy()
try:
    part.data.transform(Matrix.Translation((0, 0.1, 0)))
    try:
        model['verify_interfaces']('capillary')
    except ValueError as error:
        if 'Simple joint material disconnected' not in str(error):
            raise
        (model['OUTPUT'] / 'red-disconnection.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Disconnected upper arm was accepted')
finally:
    changed = part.data
    part.data = saved
    bpy.data.meshes.remove(changed)
model['verify_interfaces']('capillary')
print('Reduced arm study and disconnected-material control passed')
"""
    print(BlenderSocketOracle("127.0.0.1", 9876, timeout=180).execute(code))
    script = root / "scripts/model_lab_platform.py"
    modules = reload_modules_for(root, script)
    code = f"""import bpy, importlib, runpy, sys, json
from mathutils import Matrix
sys.path.insert(0, {str(root)!r})
for name in {modules!r}:
    importlib.reload(importlib.import_module(name))
model = runpy.run_path({str(script)!r}, run_name='__main__')
try:
    model['verify_seated']('capillary')
except ValueError as error:
    if 'not simultaneously seated' not in str(error):
        raise
    (model['OUTPUT'] / 'red-unseated-chain.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
else:
    raise RuntimeError('Unseated bearing chain accepted as seated')
part = bpy.data.objects['S_capillary_upper']
saved = part.matrix_world.copy()
try:
    part.matrix_world = saved @ Matrix.Translation((0.002, 0, 0))
    bpy.context.view_layer.update()
    try:
        model['verify_joint_teeth']('capillary', 'shoulder')
    except ValueError as error:
        if 'engagement mismatch' not in str(error):
            raise
        (model['OUTPUT'] / 'red-shoulder-engagement.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Released shoulder accepted as engaged')
finally:
    part.matrix_world = saved
    bpy.context.view_layer.update()
model['verify_joint_teeth']('capillary', 'shoulder')
cup = bpy.data.objects['LS_REF_vessel_250ml_ENVELOPE']
saved = cup.matrix_world.copy()
try:
    cup.location.x -= 0.0035
    bpy.context.view_layer.update()
    try:
        model['verify_joint_release']('pH_temp', 'shoulder')
    except ValueError as error:
        if 'LS_REF_vessel_250ml_ENVELOPE' not in str(error):
            raise
        (model['OUTPUT'] / 'red-shoulder-cup-position.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Off-centre cup accepted along shoulder release')
finally:
    cup.matrix_world = saved
    bpy.context.view_layer.update()
model['verify_joint_release']('pH_temp', 'shoulder')
part = bpy.data.objects['S_pH_temp_clamp_cap']
saved = part.data.copy()
try:
    part.data.transform(Matrix.Translation((0, 0, -0.01)))
    try:
        model['verify_head_envelopes']()
    except ValueError as error:
        if 'hangs too far below wrist' not in str(error):
            raise
        (model['OUTPUT'] / 'red-head-depth.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Overlong wrist-to-clamp connection accepted')
finally:
    changed = part.data
    part.data = saved
    bpy.data.meshes.remove(changed)
model['verify_head_envelopes']()
part = bpy.data.objects['S_capillary_platform']
original = part.data
for name, transform, expected in (
    ('envelope', Matrix.Diagonal((1, 1.5, 1, 1)), 'compact envelope'),
    ('material', Matrix.Scale(0.5, 4), 'bore surround'),
):
    changed = original.copy()
    part.data = changed
    try:
        changed.transform(transform)
        try:
            model['verify_platform_geometry']()
        except ValueError as error:
            if expected not in str(error):
                raise
            (model['OUTPUT'] / f'red-platform-{{name}}.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
        else:
            raise RuntimeError('Invalid compact platform accepted')
    finally:
        part.data = original
        bpy.data.meshes.remove(changed)
model['verify_platform_geometry']()
first = model['ElectrodeArmSpec']().indexed_target(1)
second = model['ElectrodeArmSpec']().indexed_target(2)
try:
    model['pose']('capillary', *((a+b)/2 for a,b in zip(first, second)), elbow_release=0)
    try:
        model['verify_local']('capillary')
    except ValueError as error:
        if 'S_capillary_upper, S_capillary_lower' not in str(error):
            raise
        (model['OUTPUT'] / 'red-between-indices.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Between-tooth position accepted as engaged')
finally:
    model['pose']('capillary')
part = bpy.data.objects['S_capillary_lower']
saved = part.matrix_world.copy()
try:
    part.matrix_world = saved @ Matrix.Translation((-0.002, 0, 0))
    bpy.context.view_layer.update()
    try:
        model['verify_joint_teeth']('capillary')
    except ValueError as error:
        if 'engagement mismatch' not in str(error):
            raise
        (model['OUTPUT'] / 'red-elbow-engagement.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Disengaged elbow was accepted as locked')
finally:
    part.matrix_world = saved
    bpy.context.view_layer.update()
model['verify_joint_teeth']('capillary')
part = bpy.data.objects['S_capillary_follower']
saved = part.data.copy()
try:
    part.data.transform(Matrix.Translation((0, 0.1, 0)))
    try:
        model['verify_local']('capillary')
    except ValueError as error:
        (model['OUTPUT'] / 'red-disconnection.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Disconnected follower was accepted')
finally:
    changed = part.data
    part.data = saved
    bpy.data.meshes.remove(changed)
model['verify_local']('capillary')
part = bpy.data.objects['S_capillary_proximal_clip']
saved = part.matrix_world.copy()
try:
    part.matrix_world = Matrix.Translation((0, 0, 0.1)) @ saved
    bpy.context.view_layer.update()
    try:
        model['verify_pins']('capillary')
    except ValueError as error:
        if 'axial stop' not in str(error):
            raise
        (model['OUTPUT'] / 'red-retainer.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Displaced retaining clip was accepted')
finally:
    part.matrix_world = saved
    bpy.context.view_layer.update()
model['verify_pins']('capillary')
part = bpy.data.objects['S_capillary_elbow_bolt']
saved = part.matrix_world.copy()
try:
    part.matrix_world = saved @ Matrix.Translation((-0.03, 0, 0))
    bpy.context.view_layer.update()
    try:
        model['verify_knobs']('capillary')
    except ValueError as error:
        if 'Bearing contact missing' not in str(error):
            raise
        (model['OUTPUT'] / 'red-knob-drive.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Disconnected knob drive was accepted')
finally:
    part.matrix_world = saved
    bpy.context.view_layer.update()
model['verify_knobs']('capillary')
part = bpy.data.objects['S_capillary_elbow_bolt']
saved = part.data.copy()
try:
    for vertex in part.data.vertices:
        if vertex.co.x > 0.008:
            vertex.co.x += 0.005
    part.data.update()
    try:
        model['verify_knobs']('capillary')
    except ValueError as error:
        if 'exposed end outside budget' not in str(error):
            raise
        (model['OUTPUT'] / 'red-bolt-exposure.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Overlong knob bolt was accepted')
finally:
    changed = part.data
    part.data = saved
    bpy.data.meshes.remove(changed)
model['verify_knobs']('capillary')
try:
    model['verify_clamps']()
except ValueError as error:
    if 'LS_REF_vessel_250ml_ENVELOPE' not in str(error):
        raise
    (model['OUTPUT'] / 'red-service-in-cup.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
else:
    raise RuntimeError('In-cup lateral probe removal was accepted')
for label in ('capillary', 'pH_temp'):
    model['pose'](label, 0, 100)
part = bpy.data.objects['S_pH_temp_clamp_cap']
saved = part.data.copy()
try:
    part.data.transform(Matrix.Translation((0, 0.05, 0)))
    try:
        model['verify_clamps']()
    except ValueError as error:
        if 'axial stop' not in str(error):
            raise
        (model['OUTPUT'] / 'red-clamp-stop.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Detached probe cap was accepted')
finally:
    changed = part.data
    part.data = saved
    bpy.data.meshes.remove(changed)
model['verify_clamps']()
for label in ('capillary', 'pH_temp'):
    model['pose'](label)
clearance = model['verify_clearance']
scope = clearance.__globals__
original_tree = scope['tree']
counts = {{}}
def counted_tree(obj):
    counts[obj.name] = counts.get(obj.name, 0) + 1
    return original_tree(obj)
scope['tree'] = counted_tree
try:
    clearance()
finally:
    scope['tree'] = original_tree
if not counts or max(counts.values()) != 1:
    raise RuntimeError('Clearance rebuilt immutable geometry more than once')
(model['OUTPUT'] / 'clearance-builds.json').write_text(json.dumps(counts))
part = bpy.data.objects['S_pH_temp_upper']
saved = part.matrix_world.copy()
try:
    part.matrix_world = bpy.data.objects['S_capillary_upper'].matrix_world @ Matrix.Translation((0.007, 0.001, 0))
    bpy.context.view_layer.update()
    try:
        clearance()
    except ValueError as error:
        (model['OUTPUT'] / 'red-cross-arm.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Per-pose cache missed a new cross-arm collision')
finally:
    part.matrix_world = saved
    bpy.context.view_layer.update()
clearance()
print('Electrode arm, retainer, knob drive and per-pose clearance cache controls passed')
bpy.ops.wm.open_mainfile(filepath=str(model['OUTPUT'] / 'elbow-seated.blend'))
"""
    print(BlenderSocketOracle("127.0.0.1", 9876, timeout=180).execute(code))
    # A fresh addon command lets Blender refresh context after opening the saved artifact.
    code = f"""import runpy, json
model = runpy.run_path({str(script)!r})
gaps = {{label: model['verify_seated'](label) for label in ('capillary', 'pH_temp')}}
(model['OUTPUT'] / 'seated-file-check.json').write_text(json.dumps(gaps))
print('Saved seated elbow artifact passed surface readback')
"""
    print(BlenderSocketOracle("127.0.0.1", 9876, timeout=30).execute(code))


if __name__ == "__main__":
    main()
