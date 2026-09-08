"""Views of the V3 finger, and the flat layout it is printed from.

Uses `setup_render` with `FINGER_PROFILE` rather than a fourth copy of the same
camera-and-lights function — that is the whole reason the profile exists.
`capture` is borrowed from the V6 presentation for the same reason.

The print layout is what the readiness check reads: four copies laid flat and
apart, which is the arrangement a slicer would actually see. It is a separate
set of objects from the assembled finger so that measuring one never disturbs
the other.
"""

from __future__ import annotations

from pathlib import Path

import bpy
from mathutils import Matrix

from scripts.biaxial_hinge_presentation import capture, duplicate
from scripts.blender_mesh_primitives import assign, collection, material
from scripts.hollow_hinge_render import m, setup_render
from scripts.presentation_profile import FINGER_PROFILE
from src.core.domain.finger_v3 import SingleTendonFingerSpec

#: Laid on its side, because a phalanx printed standing on its 61 mm axis is a
#: tall thin column with a small footprint. On its side the bores become
#: bridges, which is a real trade and one only a physical print can settle.
_LAY_FLAT = Matrix.Rotation(1.5707963267948966, 4, "X")


def build_print_layout(
    parts: list[bpy.types.Object], spec: SingleTendonFingerSpec
) -> list[bpy.types.Object]:
    """Every distinct printed part, flat and spaced, under the readiness prefix.

    The palm belongs here as much as the phalanges do: it is the part most likely
    to have a thin wall or an unsupported overhang, and leaving it out of the
    layout would leave it out of the readiness check entirely — a gap that reads
    exactly like a clean result.
    """
    layout = collection("HJ_V3_LAYOUT")
    pitch = spec.link.body_width_mm + 8.0
    copies: list[bpy.types.Object] = []
    for index, part in enumerate(parts):
        placed = duplicate(
            part,
            f"HJ_V3_LAYOUT_PART_{index + 1}",
            Matrix.Translation((m((index - 1.5) * pitch), 0.0, 0.0)) @ _LAY_FLAT,
        )
        for existing in list(placed.users_collection):
            existing.objects.unlink(placed)
        layout.objects.link(placed)
        copies.append(placed)
    bpy.context.view_layer.update()
    return copies


def present_finger(
    output: Path,
    spec: SingleTendonFingerSpec,
    parts: list[bpy.types.Object],
    layout: list[bpy.types.Object],
) -> None:
    """Three views: the assembled finger, its joints up close, and the print bed."""
    floor_material = material("HJ_V3_FLOOR", (0.05, 0.06, 0.08, 1))
    white = material("HJ_V3_LABEL", (0.95, 0.95, 0.95, 1))
    camera, _rig = setup_render(spec.link, floor_material, assign, FINGER_PROFILE)

    for obj in bpy.data.objects:
        obj.hide_render = True

    # Millimetres, like every other argument `capture` takes. Passing metres here
    # aims the camera at the floor and the finger walks out of frame.
    height = (spec.link.assembly_unit_count - 1) * spec.link.unit_pitch_mm
    mid = (0.0, 0.0, height / 2)
    capture(
        output,
        "finger_v3_assembly.png",
        camera,
        parts,
        (250.0, -430.0, 150.0),
        mid,
        260.0,
        "V3 finger: four units, one tendon",
        white,
    )
    capture(
        output,
        "finger_v3_joint_detail.png",
        camera,
        parts,
        (110.0, -150.0, 55.0),
        (0.0, 0.0, spec.link.unit_pitch_mm),
        110.0,
        "Both hinge ends on one axis",
        white,
    )
    capture(
        output,
        "finger_v3_print_layout.png",
        camera,
        layout,
        (0.0, -300.0, 210.0),
        (0.0, 0.0, 0.0),
        190.0,
        "Print layout: one part, four times",
        white,
    )

    for obj in bpy.data.objects:
        obj.hide_render = False
