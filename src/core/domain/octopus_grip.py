"""What the hand grips with: rim pads on every body, and the terminal cap.

Split out of `octopus_hand` because it answers a different question. That module
lays the hand out — where arms sit, how the palm carries them, whether the whole
thing fits the bed. This one owns the surfaces that press on an object, and the
rules those surfaces must keep: reach far enough to be worth having, leave the
cables their path, and print upright without support.

The arm profile is a field rather than an argument, so every dimension here reads
as a plain property and nothing has to be threaded through call sites.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields

from src.core.domain.biaxial_hinge import BiaxialHingeSpec


@dataclass(frozen=True, slots=True)
class GripSurfaceSpec:
    """No grip-force claim: these are contact areas, not a rated gripper."""

    arm: BiaxialHingeSpec = BiaxialHingeSpec(joint_count=4)
    grip_outer_diameter_mm: float = 42.0
    grip_pad_height_mm: float = 8.0
    grip_pad_arc_deg: float = 50.0
    grip_pad_slope_deg: float = 45.0
    tip_facet_count: int = 6
    tip_cap_flare_mm: float = 3.0
    tip_cap_height_mm: float = 14.0
    tip_cap_top_diameter_mm: float = 22.0
    tip_cable_bore_diameter_mm: float = 3.0
    tip_feature_fuse_mm: float = 1.0

    def __post_init__(self) -> None:
        numbers = [
            getattr(self, field.name)
            for field in fields(self)
            if isinstance(getattr(self, field.name), (int, float))
        ]
        if any(
            isinstance(value, bool) or not math.isfinite(value) or value <= 0 for value in numbers
        ):
            raise ValueError("dimensions must be finite and positive")
        if type(self.tip_facet_count) is not int or self.tip_facet_count < 3:
            raise ValueError("tip facet count must be an integer of at least 3")

        arm = self.arm
        if self.grip_outer_diameter_mm <= arm.body_outer_diameter_mm:
            raise ValueError("a grip pad flush with the body adds no gripping surface")
        if self.grip_outer_diameter_mm / 2 - arm.tendon_radius_mm <= arm.tendon_hole_diameter_mm:
            raise ValueError("grip pad leaves no wall outside the tendon holes")
        if not 0 < self.grip_pad_arc_deg < 360 / len(arm.tendon_positions_mm):
            raise ValueError("grip pads would run into each other around the rim")
        if self.grip_pad_slope_deg > 45:
            raise ValueError("grip pad underside would need support when printed upright")
        if self.grip_flat_face_height_mm <= 0:
            raise ValueError("the pad's chamfer consumed its whole gripping face")

        if self.tip_cap_top_diameter_mm >= self.grip_outer_diameter_mm:
            raise ValueError("the tip cap must taper, not widen, on its way up")
        if self.tip_cap_flare_slope_deg > 45:
            raise ValueError("tip cap flare would need support when printed upright")
        if self.tip_feature_base_z_mm <= 0:
            raise ValueError("tip features would cross the body's mid-plane")
        if (
            self.tip_feature_base_z_mm
            <= -arm.joint_center_offset_mm + arm.lug_outer_diameter_mm / 2
        ):
            raise ValueError("tip features reach into the ear the tip hangs from")
        if self.tip_cap_radius_at_mm(self.tip_cable_bore_z_mm) <= arm.tendon_radius_mm:
            raise ValueError("cable bore sits where the cap no longer covers the tendons")
        if self.tip_cable_bore_diameter_mm <= arm.tendon_hole_diameter_mm:
            raise ValueError("cable bore must pass the cable the tendon holes carry")

    # -------------------------------------------------------------- the pads

    @property
    def grip_pad_angles_deg(self) -> tuple[float, ...]:
        """Headings of the plain rim sectors, taken from the tendon diagonals.

        Ears occupy the cardinal directions, so the diagonals are the only free
        rim. They are also unchanged by the chain's ninety degree twist, which is
        why every body can carry the same pad pattern whatever its own twist.
        """
        return tuple(
            sorted(math.degrees(math.atan2(y, x)) % 360 for x, y in self.arm.tendon_positions_mm)
        )

    @property
    def grip_pad_projection_mm(self) -> float:
        return (self.grip_outer_diameter_mm - self.arm.body_outer_diameter_mm) / 2

    @property
    def grip_envelope_radius_mm(self) -> float:
        """Farthest the pad reaches, which is its corners, not its face.

        The flat face is a chord: its ends stand further from the axis than its
        middle does. Spacing the arms on the face radius is what let neighbouring
        pads intersect at the corners while every per-arm check stayed green.
        """
        return self.grip_outer_diameter_mm / 2 / math.cos(math.radians(self.grip_pad_arc_deg / 2))

    @property
    def grip_flat_face_height_mm(self) -> float:
        """Height of the pad's flat outer face once the chamfer has taken its cut.

        Printed upright the pad stands proud of a vertical disc, so its underside
        is chamfered back to the body; what is left above the chamfer is the face
        that actually presses on an object.
        """
        drop = self.grip_pad_projection_mm / math.tan(math.radians(self.grip_pad_slope_deg))
        return self.grip_pad_height_mm - drop

    # --------------------------------------------------------------- the cap

    @property
    def tip_feature_base_z_mm(self) -> float:
        """Height above the body centre where the cap fuses into the disc."""
        return self.arm.body_length_mm / 2 - self.tip_feature_fuse_mm

    @property
    def tip_cap_base_z_mm(self) -> float:
        """Where the cap's closed bottom sits — buried inside the disc, not on it.

        A base face flush with the disc's own surface leaves the Boolean two
        coplanar sheets to resolve, which is where readiness found non-manifold
        edges. Starting a fuse depth lower keeps the tool strictly inside solid.
        """
        return self.tip_feature_base_z_mm - self.tip_feature_fuse_mm

    @property
    def tip_cap_base_radius_mm(self) -> float:
        """Strictly inside the disc's rim, for the same reason."""
        return self.arm.body_outer_diameter_mm / 2 - self.tip_feature_fuse_mm

    @property
    def tip_cap_shoulder_z_mm(self) -> float:
        """Where the cap stops flaring outward and starts tapering in."""
        return self.tip_feature_base_z_mm + self.tip_cap_flare_mm

    @property
    def tip_cap_top_z_mm(self) -> float:
        return self.tip_cap_shoulder_z_mm + self.tip_cap_height_mm

    @property
    def tip_cap_max_radius_mm(self) -> float:
        return self.grip_outer_diameter_mm / 2

    @property
    def tip_cap_flare_slope_deg(self) -> float:
        """Lean of the flare from vertical. Over 45 degrees and it needs support."""
        run = self.tip_cap_max_radius_mm - self.tip_cap_base_radius_mm
        rise = self.tip_cap_shoulder_z_mm - self.tip_cap_base_z_mm
        return math.degrees(math.atan2(run, rise))

    @property
    def tip_cap_taper_slope_deg(self) -> float:
        """Lean of the tapering face. Narrowing upward never overhangs."""
        run = self.tip_cap_max_radius_mm - self.tip_cap_top_diameter_mm / 2
        return math.degrees(math.atan2(run, self.tip_cap_height_mm))

    def tip_cap_radius_at_mm(self, z_mm: float) -> float:
        """Circumradius of the cap at height `z_mm` above the body centre."""
        base_z = self.tip_cap_base_z_mm
        if z_mm <= base_z:
            return self.tip_cap_base_radius_mm
        if z_mm <= self.tip_cap_shoulder_z_mm:
            fraction = (z_mm - base_z) / (self.tip_cap_shoulder_z_mm - base_z)
            return self.tip_cap_base_radius_mm + fraction * (
                self.tip_cap_max_radius_mm - self.tip_cap_base_radius_mm
            )
        if z_mm >= self.tip_cap_top_z_mm:
            return self.tip_cap_top_diameter_mm / 2
        fraction = (z_mm - self.tip_cap_shoulder_z_mm) / self.tip_cap_height_mm
        return self.tip_cap_max_radius_mm - fraction * (
            self.tip_cap_max_radius_mm - self.tip_cap_top_diameter_mm / 2
        )

    @property
    def tip_cable_bore_angles_deg(self) -> tuple[float, float]:
        """Two through-bores serve four cables: each crosses one opposed pair."""
        first, second, *_ = self.grip_pad_angles_deg
        return (first, second)

    @property
    def tip_cable_bore_z_mm(self) -> float:
        """Low enough in the taper that the cap still covers the tendon radius."""
        return self.tip_cap_shoulder_z_mm + 0.4 * self.tip_cap_height_mm
