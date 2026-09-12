"""Regenerate the rotary concept and exercise a broken-link negative control."""

from pathlib import Path

from scripts.verify.generated_artifact_verify_real import BlenderSocketOracle


def main() -> None:
    script = Path(__file__).resolve().parents[1] / "model_lab_rotary.py"
    code = f"""import runpy, bpy, json
model = runpy.run_path({str(script)!r}, run_name='__main__')
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
print('Rotary concept motion and broken-link control passed; no load or print qualification')
"""
    print(BlenderSocketOracle("127.0.0.1", 9876).execute(code))


if __name__ == "__main__":
    main()
