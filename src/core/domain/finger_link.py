"""What a finger link owes the V3 stack, and nothing more.

The finger, the palm and both generators between them read exactly nineteen
attributes off whatever link they are handed. Writing those down as an interface
is what turns "a hand at human scale" from a fork into a parameter: any spec
that provides them drops into `SingleTendonFingerSpec` and the geometry, the
contracts and the print package all keep working.

Deliberately structural rather than nominal. `HingePhalanxSpec` predates this
file and must not learn about it — it is a frozen deliverable shared with V1,
V2 and V6, and a Protocol is the one way to state a shared shape without
reaching back into something that has already shipped.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class FingerLinkSpec(Protocol):
    """One printable phalanx: its body, its joint, and what the joint needs.

    Every member here is read somewhere in `finger_v3`, `palm_v3`,
    `finger_v3_geometry` or `palm_v3_geometry`. Adding one means a new
    obligation on every link; the list is short on purpose.
    """

    # Read-only on purpose. A Protocol that declares plain attributes demands
    # *settable* ones, which no frozen dataclass can offer — and settable is
    # the opposite of what is wanted here: the V3 stack only ever reads a
    # link, and a link that could be written to mid-build is a bug waiting.
    @property
    def joint_count(self) -> int: ...

    @property
    def body_length_mm(self) -> float: ...

    @property
    def body_width_mm(self) -> float: ...

    @property
    def body_depth_mm(self) -> float: ...

    @property
    def joint_center_offset_mm(self) -> float: ...

    @property
    def tendon_hole_diameter_mm(self) -> float: ...

    @property
    def pin_diameter_mm(self) -> float: ...

    @property
    def printed_radial_clearance_mm(self) -> float: ...

    @property
    def bearing_seat_diameter_mm(self) -> float: ...

    @property
    def bearing_width_mm(self) -> float: ...

    @property
    def lug_outer_diameter_mm(self) -> float: ...

    @property
    def male_tongue_thickness_mm(self) -> float: ...

    @property
    def fork_gap_mm(self) -> float: ...

    @property
    def fork_lug_thickness_mm(self) -> float: ...

    @property
    def minimum_wall_mm(self) -> float: ...

    @property
    def maximum_articulation_deg(self) -> float: ...

    @property
    def assembly_unit_count(self) -> int: ...

    @property
    def printed_pin_bore_mm(self) -> float: ...

    @property
    def fork_total_width_mm(self) -> float: ...

    @property
    def unit_pitch_mm(self) -> float: ...

    @property
    def common_hardware(self) -> tuple[str, ...]: ...

    @property
    def has_bearing_seat(self) -> bool:
        """Whether the lug is bored out for a rolling element.

        Not cosmetic. The bearing is what forces the lug wide, the lug is what
        forces the body deep, and the body depth is the ceiling on every moment
        arm — so a link that carries no bearing is a different machine, and the
        generator has to know which one it is holding rather than infer it from
        a seat diameter that happens to equal the bore.
        """
        ...


@dataclass(frozen=True, slots=True)
class BearingSeatCut:
    """One counterbore in a fork lug, along the hinge axis."""

    offset_mm: float
    diameter_mm: float
    width_mm: float


def bearing_seat_cuts(link: FingerLinkSpec) -> list[BearingSeatCut]:
    """Which seats this link wants bored, if any.

    Domain knowledge rather than Blender knowledge: whether a joint carries a
    rolling element is a fact about the link, and the generator's job is only to
    subtract what it is told. Keeping it here is also what lets it be checked at
    all — the geometry module imports `bpy` at the top, so nothing in it can be
    exercised on a machine without Blender.

    A bearingless link returns an empty list, **not** one cut of zero width.
    Those are different instructions: the second hands a degenerate cylinder to
    a boolean, which produces either nothing or something non-manifold, and no
    per-dimension rule would have objected.
    """
    if not link.has_bearing_seat:
        return []
    centre = link.fork_total_width_mm / 2.0 - link.bearing_width_mm / 2.0
    return [
        BearingSeatCut(
            offset_mm=side * centre,
            diameter_mm=link.bearing_seat_diameter_mm,
            width_mm=link.bearing_width_mm,
        )
        for side in (-1.0, 1.0)
    ]
