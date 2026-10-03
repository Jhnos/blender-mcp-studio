"""Fresh-command readbacks and transfer scenarios for saved electrode artifacts."""

from pathlib import Path

from scripts.verify.generated_artifact_verify_real import BlenderSocketOracle


def verify_saved_electrode(script: Path) -> None:
    # A fresh addon command lets Blender refresh context after opening the saved artifact.
    code = f"""import bpy, runpy, json
model = runpy.run_path({str(script)!r})
gaps = {{label: {{joint: model['verify_seated'](label, joint) for joint in ('shoulder', 'elbow', 'tip')}} for label in ('capillary', 'pH_temp')}}
model['verify_guides'](required=True)
(model['OUTPUT'] / 'guide-file-check.json').write_text(json.dumps(model['verify_guide_geometry']()))
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


def verify_electrode_configurations(script: Path) -> None:
    """Rebuild variants through one entry and read meshes, never patch source strings."""
    code = f"""import bpy, bmesh, runpy, json
from pathlib import Path
model = runpy.run_path({str(script)!r})
output = model['ROOT'] / 'tmp/lab-station-module-configurations'
output.mkdir(parents=True, exist_ok=True)
def snapshot():
    rows = {{}}
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or not obj.name.startswith('S_'):
            continue
        rows[obj.name] = {{
            'bounds': [[min(v.co[i] for v in obj.data.vertices), max(v.co[i] for v in obj.data.vertices)] for i in range(3)],
            'matrix': [list(row) for row in obj.matrix_world],
        }}
        if obj.get('compact_head_part') and not obj.get('nominal_hardware'):
            mesh = bmesh.new()
            mesh.from_mesh(obj.data)
            try:
                if any(not edge.is_manifold for edge in mesh.edges):
                    raise ValueError('Configured head is not manifold: ' + obj.name)
                pending = set(mesh.verts)
                stack = [pending.pop()]
                while stack:
                    vertex = stack.pop()
                    for edge in vertex.link_edges:
                        other = edge.other_vert(vertex)
                        if other in pending:
                            pending.remove(other)
                            stack.append(other)
                if pending:
                    raise ValueError('Configured head has disconnected material: ' + obj.name)
            finally:
                mesh.free()
    return rows
reports = {{}}
for preset in ('baseline', 'cable-clearance', 'cable-clearance'):
    spec = model['ELECTRODE_ASSEMBLIES'][preset]
    model['build_scene'](spec, output=output / preset)
    actual = json.loads(bpy.context.scene['electrode_configuration'])
    expected = json.loads(json.dumps(model['asdict'](spec)))
    if actual != expected:
        raise ValueError('Saved configuration differs from builder input')
    current = snapshot()
    for label in ('capillary', 'pH_temp'):
        model['verify_pose'](label)
    vessel = list(bpy.data.objects['LS_REF_vessel_250ml_ENVELOPE'].location)
    if preset == 'baseline':
        baseline, base_vessel = current, vessel
    else:
        if current.keys() != baseline.keys():
            raise ValueError('Configured build changed the part population')
        for name, original in baseline.items():
            if name.startswith('S_capillary_') and current[name] != original:
                raise ValueError('Independent capillary module changed')
            shifted = name.startswith('S_pH_temp_') and ('_clamp_' in name or '_probe_' in name)
            if shifted:
                for axis in range(3):
                    delta = 0.014 if axis == 1 else 0
                    if any(abs(a - b - delta) > 1e-6 for a, b in zip(current[name]['bounds'][axis], original['bounds'][axis])):
                        raise ValueError('Configured collar/probe shift mismatch: ' + name)
        for suffix in ('tip_bolt', 'platform', 'upper', 'lower'):
            if current['S_pH_temp_' + suffix] != baseline['S_pH_temp_' + suffix]:
                raise ValueError('Wrist or arm interface changed')
        if any(abs(a - b - delta) > 1e-6 for a, b, delta in zip(vessel, base_vessel, (0, -0.006, 0))):
            raise ValueError('Configured vessel shift mismatch')
        if preset in reports and reports[preset] != current:
            raise ValueError('Repeated build accumulated configuration offsets')
    reports[preset] = current
    bpy.ops.wm.save_as_mainfile(filepath=str(output / (preset + '.blend')))
(output / 'configuration-readback.json').write_text(json.dumps({{'presets': list(reports), 'part_counts': {{key: len(value) for key, value in reports.items()}}, 'repeat_matches': True}}, indent=2))
print('Shared builder: baseline, variant and repeated variant passed mesh readback')
bpy.ops.wm.open_mainfile(filepath=str(model['OUTPUT'] / 'arm-seated.blend'))
"""
    print(BlenderSocketOracle("127.0.0.1", 9876, timeout=300).execute(code))

    verify_single_head_service(script)


def verify_single_head_service(script: Path) -> None:
    """One raised head is serviced while every part of its neighbour stays in place."""
    root = script.parents[1]
    oracle = BlenderSocketOracle("127.0.0.1", 9876, timeout=120)
    source = root / "tmp/lab-station-module-configurations/cable-clearance.blend"
    restore = root / "tmp/lab-station-electrode-guides-aligned/arm-seated.blend"
    oracle.execute(f"import bpy\nbpy.ops.wm.open_mainfile(filepath={str(source)!r})")
    try:
        code = f"""import bpy, runpy, json
from pathlib import Path
model = runpy.run_path({str(script)!r})
checks = runpy.run_path({str(root / "scripts/verify/lab_cable_route_checks.py")!r})
fields = ('location', 'rotation_euler', 'rotation_quaternion', 'rotation_axis_angle', 'scale',
          'delta_location', 'delta_rotation_euler', 'delta_rotation_quaternion', 'delta_scale')
def state(prefix=''):
    return {{o.name: {{f: tuple(getattr(o, f)) for f in fields}}
            for o in bpy.data.objects if o.name.startswith(prefix)}}
initial = state()
rows = {{}}
with checks['preserve_current_scene']():
    for head, printed, samples in (('capillary', 4, 134), ('pH_temp', 6, 164)):
        for name in ('capillary', 'pH_temp'):
            model['pose'](name, 0, 100 if name == head else 0)
        model['set_electrode_service_tilt'](head)
        other = 'pH_temp' if head == 'capillary' else 'capillary'
        neighbour = state('S_' + other + '_')
        observations = []
        def observe(label, moving, removed, step):
            assert label == head and moving and set(moving).isdisjoint(removed)
            assert all(name.startswith('S_' + head + '_') for name in (*moving, *removed))
            observations.append((moving, removed, step))
        result = model['verify_clamps'](labels=(head,), observe=observe)
        assert result == {{'closed_printed_parts': printed, 'assembly_and_stop_samples': samples}}
        assert len(observations) == (130 if head == 'capillary' else 156)
        assert {{row[2] for row in observations}} == set(range(-25, 26))
        assert any(row[1] for row in observations), 'Removed parts were not reported'
        assert state('S_' + other + '_') == neighbour, 'Service moved the other head'
        original = state()
        def interrupt(label, moving, removed, step):
            if step == 1:
                raise RuntimeError('injected service observer failure')
        try:
            with checks['preserve_current_scene']():
                model['verify_clamps'](labels=(head,), observe=interrupt)
        except RuntimeError as error:
            assert str(error) == 'injected service observer failure', str(error)
        else:
            raise AssertionError('Service observer failure was swallowed')
        assert state() == original, 'Service observer failure left changed transforms'
        result['removal_observations'] = len(observations)
        model['pose'](head)
        try:
            model['verify_clamps'](labels=(head,))
        except ValueError as error:
            assert str(error).startswith('Probe clamp removal blocked: S_' + head + '_'), str(error)
            result['working_pose_rejected'] = str(error)
        else:
            raise AssertionError('Working-pose service was accepted: ' + head)
        rows[head] = result
    for invalid in ((), ('unknown',), ('capillary', 'capillary')):
        try:
            model['verify_clamps'](labels=invalid)
        except ValueError as error:
            assert 'nonempty, distinct and known' in str(error), str(error)
        else:
            raise AssertionError('Invalid service head selection accepted')
assert state() == initial, 'Single-head checks did not restore original transforms'
Path({str(root / "tmp/lab-station-module-configurations/single-head-service.json")!r}).write_text(json.dumps(rows, indent=2))
print('Independent clamp service: 298 samples, both working-pose controls and restoration passed')
"""
        print(oracle.execute(code))
    finally:
        oracle.execute(f"import bpy\nbpy.ops.wm.open_mainfile(filepath={str(restore)!r})")
