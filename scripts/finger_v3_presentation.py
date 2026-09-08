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
from mathutils import Matrix, Vector

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
    parts: list[bpy.types.Object], spec: SingleTendonFingerSpec, bed_mm: float = 256.0
) -> list[bpy.types.Object]:
    """Every distinct printed part, laid flat and nested to fit one plate.

    The palm belongs here as much as the phalanges do: it is the part most likely
    to carry a thin wall or an unsupported overhang, and leaving it out would
    leave it out of the readiness check entirely — a gap that reads exactly like
    a clean result.

    Three things this had to learn, each measured rather than assumed. Parts are
    spaced by their own width, because a pitch chosen for a 24 mm phalanx puts a
    140 mm palm straight through its neighbours. The placement is baked into each
    copy's mesh rather than carried on its object transform, because carried
    there it survived every in-process check and came back as identity when the
    .blend was reopened. And the row wraps at the bed, because five parts in a
    line is 413.5 mm and a layout that does not fit the plate is a picture of a
    layout, not a plan for one.
    """
    layout = collection("HJ_V3_LAYOUT")
    gap = 10.0
    copies: list[bpy.types.Object] = []
    placements: list[tuple[bpy.types.Object, float, float]] = []
    cursor_x = 0.0
    cursor_y = 0.0
    row_depth = 0.0
    for part in parts:
        # Laid on its side, so its printed footprint is length by width.
        width = max(part.dimensions.x, part.dimensions.z) / m(1.0)
        depth = min(part.dimensions.x, part.dimensions.y) / m(1.0)
        if cursor_x and cursor_x + width > bed_mm:
            cursor_x = 0.0
            cursor_y += row_depth + gap
            row_depth = 0.0
        placements.append((part, cursor_x + width / 2, cursor_y))
        cursor_x += width + gap
        row_depth = max(row_depth, depth)

    span_x = max(x for _, x, _ in placements) + gap
    span_y = cursor_y
    for index, (part, x_mm, y_mm) in enumerate(placements, start=1):
        placed = duplicate(part, f"HJ_V3_LAYOUT_PART_{index}", Matrix.Identity(4))
        placed.data = part.data.copy()
        placed.data.transform(
            Matrix.Translation((m(x_mm - span_x / 2), m(y_mm - span_y / 2), 0.0)) @ _LAY_FLAT
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
    hand: list[bpy.types.Object] | None = None,
) -> None:
    """Three views: the assembled finger, its joints up close, and the print bed."""
    floor_material = material("HJ_V3_FLOOR", (0.05, 0.06, 0.08, 1))
    white = material("HJ_V3_LABEL", (0.95, 0.95, 0.95, 1))
    camera, _rig = setup_render(spec.link, floor_material, assign, FINGER_PROFILE)

    for obj in bpy.data.objects:
        obj.hide_render = True

    # Millimetres, like every other argument `capture` takes. Passing metres here
    # aims the camera at the floor and the finger walks out of frame.
    # Framed from the measured extent rather than a number that looked right:
    # at 260 the vertical field was 204 mm against a 229 mm finger, so the tips
    # were outside the frame in every render taken so far.
    subject = hand if hand else parts
    zs = [
        (obj.matrix_world @ Vector(corner)).z / m(1.0)
        for obj in subject
        for corner in obj.bound_box
    ]
    xs = [
        (obj.matrix_world @ Vector(corner)).x / m(1.0)
        for obj in subject
        for corner in obj.bound_box
    ]
    mid = (0.0, 0.0, (min(zs) + max(zs)) / 2)
    tall = max(zs) - min(zs)
    wide = max(xs) - min(xs)
    frame = 1.25 * max(wide, tall * 1400 / 1100)
    capture(
        output,
        "finger_v3_assembly.png",
        camera,
        subject,
        (frame * 0.9, -frame * 1.6, mid[2] + frame * 0.25),
        mid,
        frame,
        "V3 hand: four fingers, an opposed thumb, one tendon each"
        if hand
        else "V3 finger: four units, one tendon",
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
        (0.0, -430.0, 250.0),
        (0.0, 0.0, 0.0),
        320.0,
        "Print layout: one plate, four phalanges and the palm",
        white,
    )

    for obj in bpy.data.objects:
        obj.hide_render = False
