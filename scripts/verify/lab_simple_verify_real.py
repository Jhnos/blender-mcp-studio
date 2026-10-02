"""Run the reduced assembly study and a displaced-material negative control."""

from pathlib import Path

from scripts.verify.generated_artifact_verify_real import BlenderSocketOracle
from scripts.verify.lab_electrode_readback_real import verify_saved_electrode
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
print('Electrode generation, motion and renders completed')
"""
    print(BlenderSocketOracle("127.0.0.1", 9876, timeout=300).execute(code))
    code = f"""import bpy, runpy, json
from mathutils import Matrix
model = runpy.run_path({str(script)!r})
def expect_failure(check, expected, artifact):
    try:
        check()
    except ValueError as error:
        if expected not in str(error):
            raise
        (model['OUTPUT'] / f'red-{{artifact}}.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Negative control accepted: ' + artifact)
for joint, artifact in (('elbow', 'unseated-chain'), ('shoulder', 'unseated-shoulder')):
    expect_failure(lambda: model['verify_seated']('capillary', joint), 'not simultaneously seated', artifact)
part = bpy.data.objects['S_capillary_head']
saved = part.matrix_world.copy()
try:
    part.matrix_world = saved @ Matrix.Rotation(0.1308996938995747, 4, 'X')
    bpy.context.view_layer.update()
    expect_failure(lambda: model['verify_local']('capillary'), 'Electrode self collision', 'wrist-half-index')
finally:
    part.matrix_world = saved
    bpy.context.view_layer.update()
model['verify_wrist_faces']('capillary', 0.2)
part = bpy.data.objects['S_capillary_follower']
saved = part.data.copy()
try:
    part.data.transform(Matrix.Translation((0.0168, 0, 0)))
    try:
        model['verify_forearm_stack']()
    except ValueError as error:
        if 'not in one axial layer' not in str(error):
            raise
        (model['OUTPUT'] / 'red-forearm-stack.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Separated forearm layers accepted')
finally:
    changed = part.data
    part.data = saved
    bpy.data.meshes.remove(changed)
model['verify_forearm_stack']()
part = bpy.data.objects['S_capillary_clamp_1_bolt']
saved = part.matrix_world.copy()
try:
    part.matrix_world = bpy.data.objects['S_capillary_follower'].matrix_world @ Matrix.Translation((0.0078, 0, 0.095))
    bpy.context.view_layer.update()
    try:
        model['verify_local']('capillary')
    except ValueError as error:
        if not all(name in str(error) for name in ('S_capillary_follower', 'S_capillary_clamp_1_bolt')):
            raise
        (model['OUTPUT'] / 'red-clamp-bolt-collision.json').write_text(json.dumps({{'rejected': True, 'reason': str(error)}}))
    else:
        raise RuntimeError('Clamp bolt collision was omitted from pose checks')
finally:
    part.matrix_world = saved
    bpy.context.view_layer.update()
model['verify_local']('capillary')
part = bpy.data.objects['S_capillary_upper']
saved = part.matrix_world.copy()
try:
    part.matrix_world = saved @ Matrix.Translation((0.002, 0, 0))
    bpy.context.view_layer.update()
    expect_failure(lambda: model['verify_joint_teeth']('capillary', 'shoulder'), 'engagement mismatch', 'shoulder-engagement')
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
for artifact, name, transform, check, expected in (
    ('head-depth', 'S_pH_temp_clamp_cap', Matrix.Translation((0, 0, -0.01)), lambda: model['verify_head_envelopes'](), 'hangs too far below wrist'),
    ('wrist-stack', 'S_capillary_tip_knob', Matrix.Translation((-0.004, 0, 0)), lambda: model['verify_knobs']('capillary'), 'Wrist fastener stack'),
    ('wrist-floor', 'S_pH_temp_tip_knob', Matrix.Diagonal((0.8, 1, 1, 1)), lambda: model['verify_wrist_geometry'](), 'Wrist knob floor'),
):
    part = bpy.data.objects[name]
    saved = part.data.copy()
    try:
        part.data.transform(transform)
        expect_failure(check, expected, artifact)
    finally:
        changed = part.data
        part.data = saved
        bpy.data.meshes.remove(changed)
    check()
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
    expect_failure(lambda: model['verify_joint_teeth']('capillary'), 'engagement mismatch', 'elbow-engagement')
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
for joint, artifact in (('proximal', 'retainer'), ('carrier', 'carrier-retainer')):
    part = bpy.data.objects[f'S_capillary_{{joint}}_clip']
    saved = part.matrix_world.copy()
    try:
        part.matrix_world = Matrix.Translation((0, 0, 0.1)) @ saved
        bpy.context.view_layer.update()
        expect_failure(lambda: model['verify_pins']('capillary'), 'axial stop', artifact)
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
(model['OUTPUT'] / 'released-untilted-service.json').write_text(json.dumps(model['verify_clamps']()))
try:
    model['set_electrode_wrist_pose']('capillary', 0, 0)
    expect_failure(lambda: model['verify_local']('capillary'), 'Electrode self collision', 'wrist-off-index')
finally:
    model['pose']('capillary', 0, 100)
model['verify_service_tilt']()
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
part = bpy.data.objects['S_pH_temp_head']
saved = part.matrix_world.copy()
try:
    part.matrix_world = bpy.data.objects['S_capillary_carrier_pin'].matrix_world @ Matrix.Translation((-0.025, 0, 0))
    bpy.context.view_layer.update()
    expect_failure(model['verify_pin_service'], 'S_pH_temp_head', 'pin-service-blocked')
finally:
    part.matrix_world = saved
    bpy.context.view_layer.update()
model['verify_pin_service']()
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
bpy.ops.wm.open_mainfile(filepath=str(model['OUTPUT'] / 'arm-seated.blend'))
"""
    # Fault injections run only after generation returns, in the same unchanged scene.
    print(BlenderSocketOracle("127.0.0.1", 9876, timeout=300).execute(code))
    verify_saved_electrode(script)


if __name__ == "__main__":
    main()
