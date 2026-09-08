"""Views of the V3 finger, and the flat layout it is printed from.

Uses `setup_render` with `FINGER_PROFILE` rather than a fourth copy of the same
camera-and-lights function — that is the whole reason the profile exists.
`capture` is borrowed from the V6 presentation for the same reason.

The print layout is what the readiness check reads: every distinct part laid
flat and apart, which is the arrangement a slicer would actually see. It is a separate
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
    copies: list[bpy.types.Object] = []
    gap = 10.0

    # `_LAY_FLAT` is a quarter turn about X, which maps extents (x, y, z) to
    # (x, z, y). So a part's printed footprint is its own x by its own z, and its
    # height is its y. Guessing that with max() and min() gave a 24 mm-wide
    # phalanx a 67 mm column and a 67 mm-deep row only 22 mm of room.
    footprints = [(part, part.dimensions.x / m(1.0), part.dimensions.z / m(1.0)) for part in parts]

    # Rows are built before anything is placed, because a row's depth is not known
    # until the row is finished — and a cursor advanced by one row's depth but
    # read as the next row's centre puts them half a row into each other.
    rows: list[list[tuple[bpy.types.Object, float, float]]] = [[]]
    used = 0.0
    for part, width, depth in footprints:
        if rows[-1] and used + gap + width > bed_mm:
            rows.append([])
            used = 0.0
        rows[-1].append((part, width, depth))
        used += width + (gap if len(rows[-1]) > 1 else 0.0)

    placements: list[tuple[bpy.types.Object, float, float]] = []
    row_top = 0.0
    for row in rows:
        row_depth = max(depth for _, _, depth in row)
        row_width = sum(width for _, width, _ in row) + gap * (len(row) - 1)
        left = -row_width / 2
        for part, width, _ in row:
            placements.append((part, left + width / 2, row_top + row_depth / 2))
            left += width + gap
        row_top += row_depth + gap
    total_depth = row_top - gap

    for index, (part, x_mm, y_mm) in enumerate(placements, start=1):
        placed = duplicate(part, f"HJ_V3_LAYOUT_PART_{index}", Matrix.Identity(4))
        placed.data = part.data.copy()
        # Centre the part in its slot on its own bounding box, not on its origin.
        # The origin sits wherever the geometry was built from, so slots computed
        # from measured widths still came out with the two rows touching edge to
        # edge — zero overlapping faces and zero clearance, which on a real plate
        # is two parts fused together.
        placed.data.transform(_LAY_FLAT)
        low = Vector(placed.bound_box[0])
        high = Vector(placed.bound_box[6])
        centre = (low + high) / 2
        placed.data.transform(
            Matrix.Translation((m(x_mm) - centre.x, m(y_mm - total_depth / 2) - centre.y, 0.0))
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
    camera, rig = setup_render(spec.link, floor_material, assign, FINGER_PROFILE)
    floor = rig[0]

    for obj in bpy.data.objects:
        obj.hide_render = True

    # Millimetres, like every other argument `capture` takes. Passing metres here
    # aims the camera at the floor and the finger walks out of frame.
    # Framed from the measured extent rather than a number that looked right:
    # at 260 the vertical field was 204 mm against a 229 mm finger, so the tips
    # were outside the frame in every render taken so far.
    def ground(objects: list[bpy.types.Object]) -> list[bpy.types.Object]:
        """Put the floor just under this view's subject and hand it to `capture`.

        `capture` only un-hides the objects it is given, and the floor was never
        one of them, so every view rendered the parts against empty background —
        they read as floating. The profile's fixed floor height is no use either:
        at -25 mm it cuts straight through a hand that spans -103 to +160.
        """
        low = min(
            (obj.matrix_world @ Vector(corner)).z / m(1.0)
            for obj in objects
            for corner in obj.bound_box
        )
        floor.location.z = m(low - 2.0)
        return [*objects, floor]

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
        ground(subject),
        (frame * 0.9, -frame * 1.6, mid[2] + frame * 0.25),
        mid,
        frame,
        "V3 hand: four fingers, an opposed thumb, one tendon each"
        if hand
        else "V3 finger: three units, one tendon",
        white,
    )
    capture(
        output,
        "finger_v3_joint_detail.png",
        camera,
        ground(parts),
        (110.0, -150.0, 55.0),
        (0.0, 0.0, spec.link.unit_pitch_mm),
        110.0,
        "Both hinge ends on one axis",
        white,
        # This view is a vertical stack up the middle of frame, so a centred
        # caption sits behind it. The empty space is to the side.
        label_offset=-0.30,
    )
    capture(
        output,
        "finger_v3_print_layout.png",
        camera,
        ground(layout),
        # Straight down. A print layout seen from an angle projects one row onto
        # the next, so parts that are 11 mm apart on the bed read as overlapping —
        # a blind reviewer called it a collision, and the measurement said the
        # geometry was clear. The view was the thing that was wrong.
        (0.0, 0.0, 420.0),
        (0.0, 0.0, 0.0),
        320.0,
        "Print layout: one plate, three phalanges and the palm",
        white,
    )

    for obj in bpy.data.objects:
        obj.hide_render = False
