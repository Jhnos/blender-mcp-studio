"""Transport/bootstrap only; cases and Blender fixtures live in reusable modules."""

from pathlib import Path

from scripts.verify.generated_artifact_verify_real import BlenderSocketOracle
from src.adapters.verification.authorized_code import VERIFICATION_TIMEOUT_S
from src.verification.cable_route_cases import registered_suites
from src.verification.generator_imports import reload_modules_for


def verify_cable_routes(root: Path) -> None:
    runner = root / "scripts/verify/lab_cable_route_checks.py"
    oracle = BlenderSocketOracle("127.0.0.1", 9876, timeout=60)
    source = root / "tmp/lab-station-module-configurations/cable-clearance.blend"
    restore = root / "tmp/lab-station-electrode-guides-aligned/arm-seated.blend"
    print(oracle.execute(f"import bpy\nbpy.ops.wm.open_mainfile(filepath={str(source)!r})"))
    code = f"""import bpy,runpy,importlib
from pathlib import Path
try:
    for name in {reload_modules_for(root, runner)!r}:
        importlib.reload(importlib.import_module(name))
    suite=runpy.run_path({str(runner)!r})
    suite['run'](Path({str(root / "tmp/lab-station-route-engine")!r}))
finally:
    bpy.ops.wm.open_mainfile(filepath={str(restore)!r})
"""
    batch = BlenderSocketOracle(
        "127.0.0.1", 9876, timeout=VERIFICATION_TIMEOUT_S * len(registered_suites())
    )
    print(batch.execute(code))


if __name__ == "__main__":
    verify_cable_routes(Path(__file__).resolve().parents[2])
