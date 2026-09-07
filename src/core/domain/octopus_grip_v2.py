"""Grip pads aimed at what the hand is closing on, rather than at the free rim.

V1 put its pads on the body's four diagonals and the docstring gave the reason: the
ears occupy the cardinal directions, so the diagonals are the only free rim. That
reason does not survive measurement. The ears and their roots are radially *inside*
the disc — the furthest any of them reaches is the connector envelope, and the pads
live out at the rim, well beyond it. The cardinals were never occupied out there.

It matters because of where an arm actually presses. A body sits at station angle A
turned by its own twist T, so a pad at local heading h faces global A + T + h, and
the direction of the thing being grasped — the palm's centre — is A + 180. Setting
h = 180 - T aims a pad straight at it, and since T alternates 0 and 90 down the
chain, both answers are cardinals. Putting pads on all four cardinals therefore gives
*every* body a pad facing the grasp, whatever its twist, from one shared mesh.

Measured on the real V1 mesh, 2026-09-06, sweeping the joint through its full
-34..+34 degrees: pad-to-pad clearance is 0.204 mm with pads on the diagonals and
0.553 mm with them on the cardinals. The aimed placement is also the roomier one.

No grip-force claim: these are contact areas and clearances, not a rated gripper.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.core.domain.octopus_grip import GripSurfaceSpec


@dataclass(frozen=True, slots=True)
class AimedGripSurfaceSpec(GripSurfaceSpec):
    """No grip-force claim: contact areas aimed at the grasp, not a rated gripper."""

    #: Taken off the pad's upward face so it eases into the disc instead of ending on
    #: a square edge. Upward-looking, so it never needs support. Kept small because it
    #: is subtracted from the gripping face itself and the face is what does the work:
    #: at 1.0 mm it costs a fifth of the contact area, at 0.6 mm about an eighth.
    pad_top_chamfer_mm: float = 0.6
    #: How deep the pad's inner face is buried in the disc. Deliberately NOT the
    #: tip's fuse depth: at the same value the pad's inner face and the terminal
    #: cap's base ring land on one radius, and the union leaves that face behind.
    pad_fuse_mm: float = 0.8

    #: How far the cap's flare must miss the disc's rim by, at the plane the tip is
    #: trimmed on. Far above numerical noise, far below anything mechanical.
    _RIM_TANGENCY_MARGIN_MM = 0.05

    def __post_init__(self) -> None:
        GripSurfaceSpec.__post_init__(self)
        # Measured 2026-09-06 on real geometry: with the flare at exactly 45 degrees
        # the cap's radius at the trim plane equals the disc's own radius, so the cap
        # surface grazes the trimmed rim edge instead of crossing it, and the next
        # Boolean opens twelve boundary edges at the cap's facet corners. V1 survives
        # it only because its diagonal pads happen to bury four of the six corners in
        # solid material — luck, not design, and the luck runs out when the pads move.
        # flare 3.0 -> 18.000 vs 18.0 -> 12 boundary edges; 3.5 -> 17.889 -> none.
        rim = self.arm.body_outer_diameter_mm / 2
        at_trim = self.tip_cap_radius_at_mm(self.tip_feature_base_z_mm)
        if abs(at_trim - rim) < self._RIM_TANGENCY_MARGIN_MM:
            raise ValueError("the cap's flare grazes the disc rim at the trim plane")

    # ------------------------------------------------------------ where they aim

    @property
    def grip_pad_angles_deg(self) -> tuple[float, ...]:
        """The four cardinals — the set that contains `180 - twist` for every twist.

        Also unchanged by the chain's ninety degree twist, exactly as the diagonals
        were, so one mesh still serves every body in the arm.
        """
        return tuple(float(index * 90) for index in range(4))

    @property
    def pad_inner_radius_mm(self) -> float:
        """Where the pad's buried face sits, one fuse depth inside the disc rim."""
        return self.arm.body_outer_diameter_mm / 2 - self.pad_fuse_mm

    @property
    def pad_span_deg(self) -> tuple[float, float]:
        """The angular reach of one pad, which is what any "is it clear" must use.

        A pad is not a ray at its heading. It spans half its arc either side, and the
        hardware's own reach varies across that span — the female root's far corner
        stands at 17.92 mm out at 68.7 degrees, which falls *inside* the span of a pad
        aimed at 90. So the pad and that root corner do overlap, by design and
        harmlessly: both are body material and the pads are unioned onto the body, so
        an overlap fuses rather than fouls. What must not overlap is anything that
        moves, and that is measured by sweeping the joint in Blender, not here.
        """
        half = self.grip_pad_arc_deg / 2
        return (-half, half)

    # -------------------------------------------------------- how they meet the disc

    @property
    def grip_flat_face_height_mm(self) -> float:
        """The gripping face left once both chamfers have taken their cut.

        V1 chamfered only the underside, because only the underside would have been an
        overhang. The top is chamfered here for the shape's sake, so it is taken off
        the gripping face too and every downstream check sees the smaller number.

        `super()` is spelled out because a zero-argument `super()` is broken inside a
        `slots=True` dataclass: the decorator returns a *new* class, so the implicit
        `__class__` cell points at the pre-decoration one and the call raises. Do not
        "simplify" this back.
        """
        parent = super(AimedGripSurfaceSpec, self).grip_flat_face_height_mm
        return parent - self.pad_top_chamfer_mm

    @property
    def pad_face_chord_mm(self) -> float:
        """Width of one pad's flat face — a chord, which is why its ends stand proud."""
        return (
            2
            * (self.grip_outer_diameter_mm / 2)
            * math.sin(math.radians(self.grip_pad_arc_deg / 2))
        )

    @property
    def grip_face_area_mm2(self) -> float:
        """Total flat contact area the body presents, over all four pads.

        Made a named quantity because the top chamfer is subtracted from it, so the
        cost of softening the pad's edge is measurable rather than asserted.
        """
        return (
            len(self.grip_pad_angles_deg) * self.grip_flat_face_height_mm * self.pad_face_chord_mm
        )

    @property
    def pad_profile_mm(self) -> tuple[tuple[float, float], ...]:
        """The pad's closed section, walked as (radius, height) from the top inward.

        Five points rather than V1's four: the extra one is the top chamfer, which is
        what turns the pad's square upper edge into a face that eases into the disc.
        """
        outer = self.grip_outer_diameter_mm / 2
        top = self.grip_pad_height_mm / 2
        bottom = -top
        chamfer = top - self.pad_top_chamfer_mm - self.grip_flat_face_height_mm
        return (
            (self.pad_inner_radius_mm, top),
            (outer - self.pad_top_chamfer_mm, top),
            (outer, top - self.pad_top_chamfer_mm),
            (outer, chamfer),
            (self.pad_inner_radius_mm, bottom),
        )

    # --------------------------------------------------------------- the tip bores

    @property
    def tip_cable_bore_angles_deg(self) -> tuple[float, float]:
        """Taken from the tendons, not from the pads.

        In V1 these were the same list: pads sat on the tendon diagonals, so reading
        the bores off the pad headings happened to give the right answer. Aiming the
        pads at the cardinals breaks that coincidence, and a bore on a cardinal would
        cross no tendon pair at all — so the bores are read from the tendons directly.
        """
        headings = sorted(
            math.degrees(math.atan2(y, x)) % 360 for x, y in self.arm.tendon_positions_mm
        )
        first, second, *_ = headings
        return (first, second)
