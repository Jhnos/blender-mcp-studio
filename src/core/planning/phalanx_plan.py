"""One phalanx as an ordered list of named solids, and the stack that makes a finger.

Every number `finger_v3_geometry.py` carried as a bare literal is a named
constant here with the V3 value, and the order is part of the plan because it
is load-bearing: the male lug is a 13 mm disc straddling the axis, so a bore
drilled before it is filled straight back in by the union. Bores go last.

A finger with equal moment arms is one part copied; a finger with a gradient
is one part per distinct arm. Either way the units say which part they are,
so the executor copies datablocks and never decides.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.domain.finger_link import bearing_seat_cuts
from src.core.domain.finger_v3 import SingleTendonFingerSpec
from src.core.planning.csg import Box, Cylinder, Ellipsoid, Operation, difference, union
from src.core.planning.naming import NamingPolicy

#: The neck that joins a lug to the body: a fraction of the lug's diameter wide,
#: this tall, overlapping the body by this much so the union has volume to work with.
NECK_WIDTH_RATIO = 0.72
NECK_HEIGHT_MM = 9.0
NECK_OVERLAP_MM = 1.0
#: How far a pin bore overshoots the lug it drills, and an axial bore the unit.
PIN_BORE_OVERRUN_MM = 4.0
AXIAL_BORE_OVERRUN_MM = 6.0
#: Facets on every drilled bore. The readiness check samples a fixed triangle
#: budget and treats truncation as failure; 48 facets on a second bore blew it.
BORE_SEGMENTS = 24


@dataclass(frozen=True, slots=True)
class PhalanxPlan:
    name: str
    body: Ellipsoid
    operations: tuple[Operation, ...]
    tendon_offset_mm: float
    wiring_offset_mm: float


@dataclass(frozen=True, slots=True)
class UnitPlan:
    name: str
    #: Index into `FingerPlan.parts`: which part number this unit is a print of.
    part_index: int
    lift_mm: float
    rotation_deg: float


@dataclass(frozen=True, slots=True)
class FingerPlan:
    parts: tuple[PhalanxPlan, ...]
    units: tuple[UnitPlan, ...]


def _male_end(finger: SingleTendonFingerSpec, naming: NamingPolicy) -> list[Operation]:
    link = finger.link
    axis = finger.male_hinge_axis
    return [
        union(
            Box(
                naming.scratch("MALE_CONNECTOR"),
                (
                    link.male_tongue_thickness_mm,
                    link.lug_outer_diameter_mm * NECK_WIDTH_RATIO,
                    NECK_HEIGHT_MM,
                ),
                (0.0, 0.0, link.body_length_mm / 2.0 - NECK_OVERLAP_MM),
            )
        ),
        union(
            Cylinder(
                naming.scratch("MALE_LUG"),
                link.lug_outer_diameter_mm / 2.0,
                link.male_tongue_thickness_mm,
                (0.0, 0.0, link.joint_center_offset_mm),
                axis,
            )
        ),
        difference(
            Cylinder(
                naming.scratch("CUT_MALE_PIN_BORE"),
                link.printed_pin_bore_mm / 2.0,
                link.male_tongue_thickness_mm + PIN_BORE_OVERRUN_MM,
                (0.0, 0.0, link.joint_center_offset_mm),
                axis,
                BORE_SEGMENTS,
            )
        ),
    ]


def _female_end(finger: SingleTendonFingerSpec, naming: NamingPolicy) -> list[Operation]:
    link = finger.link
    axis = finger.female_hinge_axis
    centre_z = -link.joint_center_offset_mm
    lug_x = link.fork_gap_mm / 2.0 + link.fork_lug_thickness_mm / 2.0
    connector_z = -link.body_length_mm / 2.0 + NECK_OVERLAP_MM
    operations: list[Operation] = []
    for side in (-1.0, 1.0):
        x_mm = side * lug_x
        operations.append(
            union(
                Box(
                    naming.scratch(f"FEMALE_CONNECTOR_{side:+.0f}"),
                    (
                        link.fork_lug_thickness_mm,
                        link.lug_outer_diameter_mm * NECK_WIDTH_RATIO,
                        NECK_HEIGHT_MM,
                    ),
                    (x_mm, 0.0, connector_z),
                )
            )
        )
        operations.append(
            union(
                Cylinder(
                    naming.scratch(f"FEMALE_LUG_{side:+.0f}"),
                    link.lug_outer_diameter_mm / 2.0,
                    link.fork_lug_thickness_mm,
                    (x_mm, 0.0, centre_z),
                    axis,
                )
            )
        )
    operations.append(
        difference(
            Cylinder(
                naming.scratch("CUT_FEMALE_PIN_BORE"),
                link.printed_pin_bore_mm / 2.0,
                link.fork_total_width_mm + PIN_BORE_OVERRUN_MM,
                (0.0, 0.0, centre_z),
                axis,
                BORE_SEGMENTS,
            )
        )
    )
    # Asked for, not assumed: a bearingless link contributes no cuts here.
    for index, seat in enumerate(bearing_seat_cuts(link)):
        operations.append(
            difference(
                Cylinder(
                    naming.scratch(f"CUT_BEARING_SEAT_{index}"),
                    seat.diameter_mm / 2.0,
                    seat.width_mm,
                    (seat.offset_mm, 0.0, centre_z),
                    axis,
                    BORE_SEGMENTS,
                )
            )
        )
    return operations


def _axial_bore(finger: SingleTendonFingerSpec, name: str, y_mm: float) -> Operation:
    """One bore the length of the unit. Sized off the whole unit, lugs included:
    a drill as long as the body stops short of the lugs and leaves the bore
    blind exactly where the tendon has to pass."""
    link = finger.link
    reach = 2.0 * (link.joint_center_offset_mm + link.lug_outer_diameter_mm / 2.0)
    return difference(
        Cylinder(
            name,
            link.tendon_hole_diameter_mm / 2.0,
            reach + AXIAL_BORE_OVERRUN_MM,
            (0.0, y_mm, 0.0),
            "Z",
            BORE_SEGMENTS,
        )
    )


def phalanx_plan(
    finger: SingleTendonFingerSpec, naming: NamingPolicy, part_index: int, tendon_offset_mm: float
) -> PhalanxPlan:
    """One printable unit carrying its own tendon offset, palmar hence negative y."""
    link = finger.link
    name = naming.phalanx(part_index)
    operations = (
        *_male_end(finger, naming),
        *_female_end(finger, naming),
        _axial_bore(finger, naming.scratch("CUT_TENDON"), -tendon_offset_mm),
        _axial_bore(finger, naming.scratch("CUT_WIRING"), finger.wiring_bore_offset_mm),
    )
    return PhalanxPlan(
        name=name,
        body=Ellipsoid(
            name, (link.body_width_mm, link.body_depth_mm, link.body_length_mm), (0.0, 0.0, 0.0)
        ),
        operations=operations,
        tendon_offset_mm=tendon_offset_mm,
        wiring_offset_mm=finger.wiring_bore_offset_mm,
    )


def finger_plan(finger: SingleTendonFingerSpec, naming: NamingPolicy) -> FingerPlan:
    """The stack: the base unit carries the base arm, each unit after its joint's arm.

    One part per distinct arm, named after the first unit that is a print of it;
    every later unit with the same arm is a copy of that part's datablock.
    """
    link = finger.link
    offsets = (*finger.moment_arms_mm, finger.moment_arms_mm[-1])
    parts: list[PhalanxPlan] = []
    part_of: dict[float, int] = {}
    units: list[UnitPlan] = []
    for index, (offset, rotation) in enumerate(
        zip(offsets, finger.joint_rotations_deg, strict=True), start=1
    ):
        if offset not in part_of:
            part_of[offset] = len(parts)
            parts.append(phalanx_plan(finger, naming, index, offset))
        units.append(
            UnitPlan(
                name=naming.phalanx(index),
                part_index=part_of[offset],
                lift_mm=(index - 1) * link.unit_pitch_mm,
                rotation_deg=rotation,
            )
        )
    return FingerPlan(tuple(parts), tuple(units))
