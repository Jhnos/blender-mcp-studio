"""The shape of the plate: where its corners point, how far it reaches, where it ends.

Split out of `octopus_hand_v2` because it answers a different question. That module
lays a hand out — which arm stands where, what is drilled through the plate, what is
built on top of it. This one owns the outline itself, and one rule that governs every
question asked of it: a regular polygon is not a circle, so "does this fit on the
plate" only has an answer at a stated heading.

The outline is a pentagon turned so a corner stands on each arm, with those corners
then cut back to short flats. Both halves matter to sizing. Turning the corner onto
the arm is what lets the edges clear a socket at `pi / n` off the heading rather than
along it, which shrinks the plate; cutting the corner back spends part of that saving
again, out of exactly the material standing behind the socket.

The envelope is read off the outline's own vertices. A truncation flat is a chord, so
its ends stand further from the axis than its middle — the same trap that let V1's
grip pads meet at their corners while every check against their face radius passed.

No strength claim: this is a shape and its clearances, not a qualified load path.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields

from src.core.domain.biaxial_hinge import BiaxialHingeSpec


@dataclass(frozen=True, slots=True)
class PalmOutlineSpec:
    """No strength claim: an outline, its reach, and what it leaves round a socket."""

    arm: BiaxialHingeSpec = BiaxialHingeSpec(joint_count=4)
    corner_count: int = 5
    station_radius_mm: float = 41.5
    wall_mm: float = 2.0
    thickness_mm: float = 6.0
    #: Cut at 45 degrees, the steepest an underside can be and still print off the bed.
    rim_chamfer_mm: float = 1.5
    corner_truncation_mm: float = 3.0

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
        if type(self.corner_count) is not int or self.corner_count < 3:
            raise ValueError("an outline needs at least three corners")

        # Softening the plate spends the very surplus that turning it won. The corner
        # is cut back along each arm's own heading, so every millimetre of truncation
        # comes straight out of the material standing behind that arm's socket.
        if self.socket_heading_clearance_mm < self.wall_mm:
            raise ValueError("corner truncation cuts into the socket's own wall")
        if 2 * self.rim_chamfer_mm >= self.thickness_mm:
            raise ValueError("rim chamfers meet in the middle of the plate")
        if self.rim_chamfer_mm <= self.weld_distance_mm:
            raise ValueError("rim chamfer is finer than the mesh weld distance")

    # ------------------------------------------------------------------ the polygon

    @property
    def half_sector_rad(self) -> float:
        return math.pi / self.corner_count

    @property
    def corner_angles_deg(self) -> tuple[float, ...]:
        """One corner per arm, on the arm's own heading. This is the V2 change."""
        return tuple(index * 360.0 / self.corner_count for index in range(self.corner_count))

    @property
    def inradius_mm(self) -> float:
        """Set by the edges' reach to a socket that stands half a sector away.

        With a corner on the arm, the two edges either side of it face the socket at
        `pi / corner_count` off the heading, so the station's contribution is its
        projection onto the edge normal rather than its full radius.
        """
        return (
            self.station_radius_mm * math.cos(self.half_sector_rad)
            + self.arm.connector_envelope_radius_mm
            + self.wall_mm
        )

    @property
    def circumradius_mm(self) -> float:
        return self.inradius_mm / math.cos(self.half_sector_rad)

    @property
    def corner_flat_radius_mm(self) -> float:
        """Where each cut-back corner's flat stands — the plate's reach at an arm."""
        return self.circumradius_mm - self.corner_truncation_mm

    @property
    def corner_flat_half_width_mm(self) -> float:
        """Half the width of one truncation flat, where it meets the pentagon edges."""
        return (
            self.inradius_mm - self.corner_flat_radius_mm * math.cos(self.half_sector_rad)
        ) / math.sin(self.half_sector_rad)

    def boundary_radius_at_mm(self, angle_deg: float) -> float:
        """Distance from the axis to the plate edge along `angle_deg`.

        At an edge's midpoint this returns the inradius, and it rises towards the
        corners — where the truncation flat, not the pentagon, is what the plate
        actually ends at.
        """
        sector = 2 * self.half_sector_rad
        offset = math.radians(angle_deg) % sector
        pentagon = self.inradius_mm / math.cos(self.half_sector_rad - offset)
        # Signed angle to the nearest corner, which every truncation flat faces.
        to_corner = (math.radians(angle_deg) + self.half_sector_rad) % sector - self.half_sector_rad
        return min(pentagon, self.corner_flat_radius_mm / math.cos(to_corner))

    # ----------------------------------------------------------------- the envelope

    @property
    def outline_vertices_mm(self) -> tuple[tuple[float, float], ...]:
        """The truncated polygon, corner by corner — two vertices per cut corner."""
        vertices: list[tuple[float, float]] = []
        half_width = self.corner_flat_half_width_mm
        for corner in self.corner_angles_deg:
            heading = math.radians(corner)
            cosine, sine = math.cos(heading), math.sin(heading)
            for side in (-1.0, 1.0):
                across = side * half_width
                vertices.append(
                    (
                        self.corner_flat_radius_mm * cosine - across * sine,
                        self.corner_flat_radius_mm * sine + across * cosine,
                    )
                )
        return tuple(vertices)

    def inset_vertices_mm(self, inset_mm: float) -> tuple[tuple[float, float], ...]:
        """The outline stepped inward by `inset_mm`, as that smaller polygon's vertices.

        Offsetting a polygon is not scaling it. Each edge moves in along its own
        normal and the vertices land where the moved edges cross; scaling would move
        every vertex the same *fraction* of its radius, and on a shape with two
        different edge distances — long edges at the inradius, corner flats further
        out — that produces a chamfer which is 45 degrees nowhere.

        Ordered around the outline, alternating a corner flat and a long edge, so the
        result stacks ring-on-ring against `inset_vertices_mm(0)` for a loft.
        """
        planes = [
            plane
            for corner in self.corner_angles_deg
            for plane in (
                (math.radians(corner), self.corner_flat_radius_mm - inset_mm),
                (math.radians(corner) + self.half_sector_rad, self.inradius_mm - inset_mm),
            )
        ]
        vertices: list[tuple[float, float]] = []
        for index, (first_angle, first_distance) in enumerate(planes):
            second_angle, second_distance = planes[(index + 1) % len(planes)]
            determinant = math.cos(first_angle) * math.sin(second_angle) - math.sin(
                first_angle
            ) * math.cos(second_angle)
            vertices.append(
                (
                    (
                        first_distance * math.sin(second_angle)
                        - second_distance * math.sin(first_angle)
                    )
                    / determinant,
                    (
                        second_distance * math.cos(first_angle)
                        - first_distance * math.cos(second_angle)
                    )
                    / determinant,
                )
            )
        return tuple(vertices)

    @property
    def enclosing_radius_mm(self) -> float:
        """Farthest any point of the outline sits from the axis.

        Read off the outline's own vertices, never off a nominal radius. A truncation
        flat is a chord: its ends stand further out than its middle does.
        """
        return max(math.hypot(x, y) for x, y in self.outline_vertices_mm)

    @property
    def across_corners_mm(self) -> float:
        """Diameter of the smallest circle containing the plate, whatever its rotation."""
        return 2 * self.enclosing_radius_mm

    # -------------------------------------------------------- what it leaves a socket

    @property
    def socket_heading_clearance_mm(self) -> float:
        """Plate left past the socket along an arm heading — the stem's material.

        V1's boundary along a heading was its inradius, and this was exactly one wall.
        V2's is its corner, less the truncation cut off that corner.
        """
        return self.corner_flat_radius_mm - (
            self.station_radius_mm + self.arm.connector_envelope_radius_mm
        )

    @property
    def socket_edge_clearance_mm(self) -> float:
        """Worst clearance from a station to any edge line, over every station.

        Taken as the minimum over all edges rather than the one expected to bind, so a
        change of `corner_count` cannot quietly move which edge governs.
        """
        return min(
            self.inradius_mm
            - self.station_radius_mm
            * math.cos(math.radians(corner) + self.half_sector_rad - math.radians(station))
            - self.arm.connector_envelope_radius_mm
            for station in self.corner_angles_deg
            for corner in self.corner_angles_deg
        )

    # ------------------------------------------------------------------- the edges

    @property
    def weld_distance_mm(self) -> float:
        """What the mesh cleanup merges away — the floor on any chamfer that must survive."""
        return 0.005

    @property
    def top_face_reach_mm(self) -> float:
        """How far the flat top face runs on an arm's heading, before the chamfer starts."""
        return self.boundary_radius_at_mm(self.corner_angles_deg[0]) - self.rim_chamfer_mm

    @property
    def chamfer_slope_deg(self) -> float:
        """Lean of the rim chamfer from vertical. Cut square, so 45 degrees.

        The underside one is what matters: printed palm-down it is the first thing off
        the bed, and past 45 degrees it would need support.
        """
        return math.degrees(math.atan2(self.rim_chamfer_mm, self.rim_chamfer_mm))
