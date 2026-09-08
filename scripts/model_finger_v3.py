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
from mathutils import Vector

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.blender_artifact_export import export_stl_mm  # noqa: E402
from scripts.blender_generator_runner import run_generator  # noqa: E402
from scripts.blender_mesh_primitives import assign, collection, material  # noqa: E402
from scripts.finger_v3_geometry import build_finger  # noqa: E402
from scripts.finger_v3_presentation import build_print_layout, present_finger  # noqa: E402
from scripts.palm_v3_geometry import assemble_hand, build_palm  # noqa: E402
from src.core.domain.finger_v3 import SingleTendonFingerSpec  # noqa: E402
from src.core.domain.palm_v3 import AnthropomorphicPalmSpec  # noqa: E402

SPEC = SingleTendonFingerSpec()
PALM = AnthropomorphicPalmSpec()
OUTPUT = PROJECT_ROOT / "tmp" / "hand-v3"


def _shell_count(obj: bpy.types.Object) -> int:
    """How many disconnected solids this mesh actually contains."""
    mesh = obj.data
    parent = list(range(len(mesh.vertices)))

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for edge in mesh.edges:
        left, right = (find(index) for index in edge.vertices)
        if left != right:
            parent[left] = right
    return len({find(index) for index in range(len(mesh.vertices))})


def _refuse_a_disconnected_knuckle(palm: bpy.types.Object) -> None:
    """The palm's roots must reach the height the fingers' forks sit at.

    Nothing else looks at this. The palm was watertight, one shell, and passed
    both contracts while every knuckle sat 13.5 mm below its finger — the hand
    simply could not be assembled. Height is the cheap, decisive test: a root
    that does not reach cannot be coaxial with anything.
    """
    reach = PALM.finger.link.joint_center_offset_mm + PALM.finger.link.lug_outer_diameter_mm / 2
    top = max((palm.matrix_world @ Vector(corner)).z for corner in palm.bound_box) / 0.001
    if abs(top - reach) > 0.5:
        raise RuntimeError(
            f"the palm's knuckle roots reach {top:.2f} mm but the fingers' fork bores "
            f"sit at {PALM.finger.link.joint_center_offset_mm:.2f} mm, needing {reach:.2f} mm "
            "of root — the hand cannot be assembled"
        )


def _refuse_a_stale_scene() -> None:
    """Fail loudly if a previous run's objects are still in the scene.

    The contract caught this before the generator did, which is the wrong way
    round: the generator knows exactly how many of each thing it just made.
    """
    expected = {
        "HJ_V3_PHALANX_": 4,
        "HJ_V3_LAYOUT_PART_": 5,
        "HJ_V3_HAND_": 19,
        "HJ_V3_PALM": 1,
    }
    for prefix, count in expected.items():
        found = sum(1 for obj in bpy.data.objects if obj.name.startswith(prefix))
        if found != count:
            raise RuntimeError(
                f"{found} objects under {prefix!r}, expected {count} — a previous run "
                "was not cleared, and everything downstream is measuring two hands"
            )


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
        # Per-object material links, so alternating colours do not force the four
        # units apart into four meshes. Sharing the mesh is the point.
        assign(part, bone)
        part.material_slots[0].link = "OBJECT"
        part.material_slots[0].material = alt if index % 2 == 0 else bone

    if len({id(part.data) for part in parts}) != 1:
        raise RuntimeError(
            "the four units stopped sharing one mesh, so this finger is now four "
            "part numbers instead of one; that is a decision, not a side effect"
        )

    export_stl_mm(parts, OUTPUT / "finger_v3_mm.stl")
    export_stl_mm([parts[0]], OUTPUT / "phalanx_mm.stl")

    palm = build_palm(PALM)
    _refuse_a_disconnected_knuckle(palm)
    finger.objects.link(palm)
    if palm.users_collection and scene.collection in palm.users_collection:
        scene.collection.objects.unlink(palm)
    assign(palm, bone)
    # A printed part that is two shells is two parts, and a watertightness check
    # cannot see the difference: a detached solid is perfectly manifold. The
    # thumb root shipped as a loose 88-face object beside the palm until this
    # existed, passing every other check on the way out.
    if _shell_count(palm) != 1:
        raise RuntimeError(
            f"the palm came out as {_shell_count(palm)} disconnected solids; "
            "something is not joined to the plate"
        )
    export_stl_mm([palm], OUTPUT / "palm_mm.stl")

    hand = assemble_hand(PALM, palm)
    for unit in hand:
        if unit is not palm:
            finger.objects.link(unit)
            if scene.collection in unit.users_collection:
                scene.collection.objects.unlink(unit)
            assign(unit, bone)
    export_stl_mm(hand, OUTPUT / "hand_v3_mm.stl")
    scene["HJ_V3_HAND_STATIONS"] = ["F1", "F2", "F3", "F4", "T"]

    layout = build_print_layout([*parts, palm], SPEC)

    scene["HJ_V3_PHALANX_NAMES"] = [part.name for part in parts]
    scene["HJ_V3_DESIGN_NOTE"] = (
        "V3 finger: four planar units, both hinge ends on one axis so the stack "
        "goes together unrotated, and one tendon bore per unit at that joint's own "
        "moment arm. Unqualified fit prototype; no grip force, retention or "
        "strength claim. Never printed."
    )
    _refuse_a_stale_scene()
    present_finger(OUTPUT, SPEC, parts, layout, hand)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "finger_v3.blend"))
    print("FINGER_V3_READY", str(OUTPUT))


def main() -> None:
    # The prefix is not decoration. `run_generator` defaults to "HH_", which every
    # earlier generator uses; this one namespaces its output "HJ_". Left at the
    # default, `clear_previous` removed nothing of ours and each run in a live
    # Blender stacked another whole hand on the last — nine layout parts instead
    # of five, two of them intersecting. It cannot show up locally, because a
    # --factory-startup run always begins with an empty scene.
    run_generator(build, prefix="HJ_")


if __name__ == "__main__":
    main()
