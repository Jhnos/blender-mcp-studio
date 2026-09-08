"""V3 finger: four planar units on one tendon, generated from the spec.

Reviving the hinge-chain line the way `scripts/archive/README.md` prescribes —
through a named `PresentationProfile`, not by moving a fork back into the live
tree. This generator owns composition and export only; the shape is in
`finger_v3_geometry`, the numbers are in `SingleTendonFingerSpec`, and the look
is `FINGER_PROFILE`.

Nothing here claims a grip force, a print success, or a fit. The finger has
never been printed.
"""

import sys
from pathlib import Path

import bpy

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.blender_artifact_export import export_stl_mm  # noqa: E402
from scripts.blender_generator_runner import run_generator  # noqa: E402
from scripts.blender_mesh_primitives import assign, collection, material  # noqa: E402
from scripts.finger_v3_geometry import build_finger  # noqa: E402
from src.core.domain.finger_v3 import SingleTendonFingerSpec  # noqa: E402

SPEC = SingleTendonFingerSpec()
OUTPUT = PROJECT_ROOT / "tmp" / "hand-v3"


def build() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.unit_settings.scale_length = 1.0

    bone = material("HJ_V3_BODY", (0.86, 0.80, 0.68, 1))
    alt = material("HJ_V3_ALT", (0.72, 0.66, 0.55, 1))
    finger = collection("HJ_V3_FINGER")

    parts = build_finger(SPEC)
    for index, part in enumerate(parts, start=1):
        finger.objects.link(part)
        if part.users_collection and scene.collection in part.users_collection:
            scene.collection.objects.unlink(part)
        assign(part, alt if index % 2 == 0 else bone)

    if len({part.data.name for part in parts}) != len(parts):
        raise RuntimeError(
            "the phalanges share a mesh, so they cannot be carrying different "
            "tendon offsets — the moment-arm gradient is the mechanism"
        )

    export_stl_mm(parts, OUTPUT / "finger_v3_mm.stl")
    export_stl_mm([parts[0]], OUTPUT / "phalanx_base_mm.stl")

    scene["HJ_V3_PHALANX_NAMES"] = [part.name for part in parts]
    scene["HJ_V3_DESIGN_NOTE"] = (
        "V3 finger: four planar units, both hinge ends on one axis so the stack "
        "goes together unrotated, and one tendon bore per unit at that joint's own "
        "moment arm. Unqualified fit prototype; no grip force, retention or "
        "strength claim. Never printed."
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "finger_v3.blend"))
    print("FINGER_V3_READY", str(OUTPUT))


def main() -> None:
    run_generator(build)


if __name__ == "__main__":
    main()
