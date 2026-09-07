"""The buttress behind an arm socket, and the swung arm it has to live under.

Split out of `octopus_hand_v2` because it answers a different question. That module
lays the plate out — how big the pentagon is, where the corners fall, what is drilled
through it. This one owns a moving problem: the first arm body turns about the base
joint's pin, so its underside sweeps down and out across the plate, and the stem is
only sound if it stays under that swept floor at every radius it occupies.

The distinction matters because static clearance is not the question. A stem sized
against the arm at rest passes every check and still fouls the joint at full travel;
the narrowest point of the swept floor is a throat partway out, at neither end.

The arm profile is a field rather than an argument, so every dimension reads as a
plain property and nothing has to be threaded through call sites — the same shape
`GripSurfaceSpec` uses.

No strength claim is made. This sizes a buttress so it clears a moving part; it does
not qualify it to carry a load.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields

from src.core.domain.biaxial_hinge import BiaxialHingeSpec


@dataclass(frozen=True, slots=True)
class ReinforcingStemSpec:
    """No load claim: this is a printable buttress that clears the joint above it."""

    arm: BiaxialHingeSpec = BiaxialHingeSpec(joint_count=4)
    station_radius_mm: float = 41.5
    palm_wall_mm: float = 2.0
    height_mm: float = 8.0
    length_mm: float = 12.0
    #: The ramp stops here rather than at zero: a feather edge is finer than the weld
    #: distance the mesh cleanup uses, so it would be dissolved rather than printed.
    edge_height_mm: float = 1.2
    half_width_mm: float = 6.0
    #: How far the stem must stay under the arm's swept underside.
    clearance_mm: float = 2.0
    #: Radii the swept-envelope invariant is sampled at, per millimetre of stem.
    sample_density: int = 8

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
        if type(self.sample_density) is not int:
            raise ValueError("sample density must be an integer")

        if self.edge_height_mm >= self.height_mm:
            raise ValueError("stem does not taper: its edge is as tall as its root")
        if self.half_width_mm + self.palm_wall_mm >= self.arm.side_female_center_mm - (
            self.arm.lug_thickness_mm / 2
        ):
            raise ValueError("stem is wide enough to foul the ears the arm hangs by")
        # A hinge turns about its pin, so the arm's underside sweeps down over the
        # plate as the base joint opens. Static clearance says nothing about that: the
        # stem has to stay under the *swept* floor at every radius it occupies, not
        # merely under the arm at rest.
        for radius in self.sample_radii_mm:
            floor = self.swept_floor_mm(radius)
            if floor is not None and self.top_z_mm(radius) + self.clearance_mm > floor:
                raise ValueError("stem reaches into the base joint's swept envelope")

    # -------------------------------------------------------------- where it sits

    @property
    def palm_top_face_z_mm(self) -> float:
        """The plate's top face, which the palm treats as a body centre plane."""
        return self.arm.body_length_mm / 2

    @property
    def inner_radius_mm(self) -> float:
        """Where the stem starts: just clear of the socket root it braces.

        The socket is a V6 root turned a quarter turn, so the root's tangential
        half-width is what stands out along the palm's radius.
        """
        return self.station_radius_mm + self.arm.root_profile_mm[0][2]

    @property
    def outer_radius_mm(self) -> float:
        return self.inner_radius_mm + self.length_mm

    def top_z_mm(self, radius_mm: float) -> float:
        """Top of the stem's ramp at `radius_mm`, in palm coordinates.

        A straight ramp from `height_mm` at the socket down to a finite edge, so the
        face looks upward the whole way and needs no support printed palm-down.
        """
        span = self.outer_radius_mm - self.inner_radius_mm
        travelled = min(max(radius_mm - self.inner_radius_mm, 0.0), span) / span
        return (
            self.palm_top_face_z_mm
            + self.height_mm
            - travelled * (self.height_mm - self.edge_height_mm)
        )

    @property
    def sample_radii_mm(self) -> tuple[float, ...]:
        span = self.outer_radius_mm - self.inner_radius_mm
        steps = max(int(span * self.sample_density), 1)
        return tuple(self.inner_radius_mm + span * index / steps for index in range(steps + 1))

    @property
    def slope_deg(self) -> float:
        """Lean of the ramp from horizontal. Upward-facing, so it never overhangs."""
        return math.degrees(math.atan2(self.height_mm - self.edge_height_mm, self.length_mm))

    # ------------------------------------------------------- what swings above it

    def swept_floor_mm(self, radius_mm: float) -> float | None:
        """Lowest the first arm body's underside gets at `radius_mm`, over the swing.

        The body is taken as its disc — underside and outer rim — carried round the
        base joint's pin. Off the arm's centreline the disc reaches less far radially,
        so the centreline is the worst case and this bound is conservative for a stem
        standing on it. Returns None where the arm never passes over that radius.

        Discrete samples over the articulation range, not a continuous proof; the real
        geometry is measured again in Blender.
        """
        pivot_z = self.arm.joint_center_offset_mm
        body_centre_z = self.arm.unit_pitch_mm
        under = body_centre_z - self.arm.body_length_mm / 2 - pivot_z
        over = body_centre_z + self.arm.body_length_mm / 2 - pivot_z
        reach = self.arm.body_outer_diameter_mm / 2
        edges = (((-reach, under), (reach, under)), ((reach, under), (reach, over)))
        travel = self.arm.maximum_articulation_deg

        lowest: float | None = None
        samples = 2 * int(travel) * self.sample_density
        for index in range(samples + 1):
            angle = math.radians(-travel + 2 * travel * index / samples)
            cosine, sine = math.cos(angle), math.sin(angle)
            for (radial_a, axial_a), (radial_b, axial_b) in edges:
                first_r = self.station_radius_mm + radial_a * cosine - axial_a * sine
                first_z = pivot_z + radial_a * sine + axial_a * cosine
                second_r = self.station_radius_mm + radial_b * cosine - axial_b * sine
                second_z = pivot_z + radial_b * sine + axial_b * cosine
                if (first_r - radius_mm) * (second_r - radius_mm) > 0:
                    continue
                if abs(second_r - first_r) < 1e-9:
                    continue
                fraction = (radius_mm - first_r) / (second_r - first_r)
                height = first_z + fraction * (second_z - first_z)
                lowest = height if lowest is None else min(lowest, height)
        return lowest

    @property
    def headroom_mm(self) -> float:
        """Worst margin between the stem's ramp and the swept floor above it."""
        return min(
            floor - self.top_z_mm(radius)
            for radius in self.sample_radii_mm
            if (floor := self.swept_floor_mm(radius)) is not None
        )
