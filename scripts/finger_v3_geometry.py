"""One planar phalanx, and the stack of them that makes a finger.

Two departures from the archived hinge-chain geometry this borrows its shape
from, and both are forced by the same decision — that a finger bends in one
plane:

1. **Both hinge ends sit on X.** The archived link put its male lug on X and its
   female fork on Y, which is why its chain turned alternate units a quarter
   turn: the turn is what let a male end enter the next unit's female end at
   all. Ends on one axis is what lets the stack go together unrotated.
2. **The phalanges are not identical.** Each joint gets its own moment arm, and
   a joint's moment arm is just where the tendon passes it, so the tendon bore
   sits at a different offset in each phalanx. That difference is the whole
   mechanism: it is what makes one cable close three joints in order rather than
   all at once.

The tendon runs on the palmar side, at -Y. Nothing here claims a grip force —
these are offsets and diameters.
"""

from __future__ import annotations

import math

import bpy

from scripts.blender_mesh_primitives import add_cylinder, add_ellipsoid, boolean, cleanup_mesh
from scripts.hollow_hinge_geometry import create_box
from src.core.domain.finger_link import bearing_seat_cuts
from src.core.domain.finger_v3 import SingleTendonFingerSpec

#: Segments on every drilled bore. The readiness check samples a fixed triangle
#: budget and reports truncation past it, which the contracts treat as failure —
#: not a warning. `octopus_tip_geometry` dropped to this number for the same
#: reason. Adding a second bore per part at the 48-segment default pushed the
#: analysis to 21 228 triangles and truncated it.
_BORE_SEGMENTS = 24


def _cut_axial_bore(
    body: bpy.types.Object, spec: SingleTendonFingerSpec, offset_mm: float, name: str
) -> None:
    """One bore running the length of the unit, `offset_mm` towards the palm.

    V1 and V2 drilled four bores per body because four cables ran the arm. One
    cable needs one, and where the tendon's bore sits *is* the joint's moment arm.
    The wiring's bore is the same hole mirrored to the back, which is why this
    takes an offset and a name rather than knowing about either.
    """
    link = spec.link
    # Sized off the whole unit, not off the body. The lugs stand a lug radius
    # beyond the joint centres at each end, so a drill as long as the body stops
    # short of them and leaves the bore blind exactly where the tendon has to
    # pass. Invisible in the bounding box; the octopus tip learned this same
    # lesson about its centre channel, and this is the second time.
    reach = 2.0 * (link.joint_center_offset_mm + link.lug_outer_diameter_mm / 2.0) + 6.0
    boolean(
        body,
        add_cylinder(
            name,
            link.tendon_hole_diameter_mm / 2.0,
            reach,
            (0.0, -offset_mm, 0.0),
            vertices=_BORE_SEGMENTS,
        ),
        "DIFFERENCE",
    )


def _add_male_end(body: bpy.types.Object, spec: SingleTendonFingerSpec) -> None:
    """The tongue at the top, a disc whose pin bore runs along the finger's one axis."""
    link = spec.link
    axis = spec.male_hinge_axis
    # The neck, without which the lug is a disc floating above its own body.
    # The female fork has always had one; the male end did not, and once the
    # joint centre moved from 24 to 27 mm the disc left the body 0.5 mm behind.
    # Every phalanx then shipped as two watertight solids that no gate could
    # tell apart from one.
    boolean(
        body,
        create_box(
            "HJ_MALE_CONNECTOR",
            (
                link.male_tongue_thickness_mm,
                link.lug_outer_diameter_mm * 0.72,
                9.0,
            ),
            (0.0, 0.0, link.body_length_mm / 2.0 - 1.0),
        ),
        "UNION",
    )
    boolean(
        body,
        add_cylinder(
            "HJ_MALE_LUG",
            link.lug_outer_diameter_mm / 2.0,
            link.male_tongue_thickness_mm,
            (0.0, 0.0, link.joint_center_offset_mm),
            axis=axis,
        ),
        "UNION",
    )
    boolean(
        body,
        add_cylinder(
            "HJ_CUT_MALE_PIN_BORE",
            link.printed_pin_bore_mm / 2.0,
            link.male_tongue_thickness_mm + 4.0,
            (0.0, 0.0, link.joint_center_offset_mm),
            axis=axis,
            vertices=_BORE_SEGMENTS,
        ),
        "DIFFERENCE",
    )


def _add_female_end(body: bpy.types.Object, spec: SingleTendonFingerSpec) -> None:
    """The fork at the bottom, straddling along the same axis the male end uses.

    The archived version separated its fork lugs along Y. Separating them along
    X instead is the whole of what makes the stack planar; every dimension is
    the borrowed one, only the coordinate role changes.
    """
    link = spec.link
    centre_z = -link.joint_center_offset_mm
    lug_x = link.fork_gap_mm / 2.0 + link.fork_lug_thickness_mm / 2.0
    connector_z = -link.body_length_mm / 2.0 + 1.0
    for side in (-1.0, 1.0):
        x_mm = side * lug_x
        boolean(
            body,
            create_box(
                f"HJ_FEMALE_CONNECTOR_{side:+.0f}",
                (link.fork_lug_thickness_mm, link.lug_outer_diameter_mm * 0.72, 9.0),
                (x_mm, 0.0, connector_z),
            ),
            "UNION",
        )
        boolean(
            body,
            add_cylinder(
                f"HJ_FEMALE_LUG_{side:+.0f}",
                link.lug_outer_diameter_mm / 2.0,
                link.fork_lug_thickness_mm,
                (x_mm, 0.0, centre_z),
                axis=spec.female_hinge_axis,
            ),
            "UNION",
        )

    boolean(
        body,
        add_cylinder(
            "HJ_CUT_FEMALE_PIN_BORE",
            link.printed_pin_bore_mm / 2.0,
            link.fork_total_width_mm + 4.0,
            (0.0, 0.0, centre_z),
            axis=spec.female_hinge_axis,
            vertices=_BORE_SEGMENTS,
        ),
        "DIFFERENCE",
    )

    # Asked for rather than assumed. A bearingless link returns no cuts, where
    # the old unconditional loop would have subtracted a zero-height cylinder.
    for index, seat in enumerate(bearing_seat_cuts(link)):
        boolean(
            body,
            add_cylinder(
                f"HJ_CUT_BEARING_SEAT_{index}",
                seat.diameter_mm / 2.0,
                seat.width_mm,
                (seat.offset_mm, 0.0, centre_z),
                axis=spec.female_hinge_axis,
                vertices=_BORE_SEGMENTS,
            ),
            "DIFFERENCE",
        )


def create_phalanx(
    spec: SingleTendonFingerSpec, index: int, tendon_offset_mm: float
) -> bpy.types.Object:
    """One printable unit, carrying its own tendon offset.

    `index` is 1 for the unit that mounts into the palm; the offsets are what
    make the units differ, so they cannot share a mesh datablock.
    """
    link = spec.link
    body = add_ellipsoid(
        f"HJ_V3_PHALANX_{index}",
        (link.body_width_mm, link.body_depth_mm, link.body_length_mm),
        (0.0, 0.0, 0.0),
    )
    _add_male_end(body, spec)
    _add_female_end(body, spec)
    # Drilled last, on purpose. The male lug is a 13 mm disc straddling the axis,
    # so any bore closer in than its radius is filled straight back in by the
    # union that follows it. Measured on the first build: only the 7.1 mm bore
    # survived; the other three units came out solid, watertight and blind.
    # `octopus_tip_geometry._open_cable_paths` already carries this lesson —
    # re-drill everything the added feature covered.
    _cut_axial_bore(body, spec, tendon_offset_mm, "HJ_CUT_TENDON")
    # The wiring path, mirrored onto the back. There is no central channel to put
    # it in: this link's pin runs through the axis, so a channel there would open
    # into the pin bore. Dorsal is the side nothing else uses.
    _cut_axial_bore(body, spec, -spec.wiring_bore_offset_mm, "HJ_CUT_WIRING")
    cleanup_mesh(body)
    return body


def build_finger(spec: SingleTendonFingerSpec) -> list[bpy.types.Object]:
    """The whole stack, each unit lifted by one pitch and turned by nothing.

    Turned by nothing is the point: `joint_rotations_deg` is all zeros, and it
    is only coherent because both hinge ends share an axis. The assertion that
    keeps those two facts together lives in the spec's own tests.
    """
    link = spec.link
    offsets = (*spec.moment_arms_mm, spec.moment_arms_mm[-1])
    if spec.phalanx_part_count != 1:
        raise RuntimeError(
            "this builder copies one master, so the moment arms must be equal; "
            f"got {spec.moment_arms_mm}"
        )

    master = create_phalanx(spec, 1, offsets[0])
    parts = [master]
    # Copies share the master's mesh datablock on purpose. It is what makes the
    # whole stack one part number instead of one per unit, and it is the thing
    # the contract oracle checks when it asks for a shared mesh.
    for index, rotation_deg in enumerate(spec.joint_rotations_deg[1:], start=2):
        copy = master.copy()
        copy.data = master.data
        copy.name = f"HJ_V3_PHALANX_{index}"
        bpy.context.collection.objects.link(copy)
        copy.location.z = 0.001 * ((index - 1) * link.unit_pitch_mm)
        copy.rotation_euler.z = math.radians(rotation_deg)
        parts.append(copy)
    bpy.context.view_layer.update()
    return parts
