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
print('Electrode arm and displaced-follower control passed')
"""
    print(BlenderSocketOracle("127.0.0.1", 9876, timeout=180).execute(code))


if __name__ == "__main__":
    main()
