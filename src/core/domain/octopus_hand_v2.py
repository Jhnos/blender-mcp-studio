"""V2 palm: the pentagon turned so a corner stands on each arm.

V1 sized the plate by its flats, and the comment there said why — "material must
reach past every socket, so the flats govern, not the corners". That was true while
an edge faced each arm, which was never a decision: it is the phase Blender's
five-sided cylinder happens to start at, eighteen degrees off the arm headings. The
consequence is upside down. The corners, which carry nothing, hold the most material;
the edges, which carry the sockets, hold the least.

Turning the pentagon a corner-onto-each-arm inverts that. The socket then stands
where the plate is deepest, and the edges only have to clear it at 36 degrees off the
heading — so `cos 36` comes off the requirement and the whole plate gets smaller while
the arm gets more material behind it. That surplus at the corner is what the
reinforcing stem is later built from.

Everything the palm does not own is V1's, inherited unchanged: the V6 arm, the grip
surfaces, the tip, the coupon and the printed part counts. V1 stays a controlled
delivery — this class only overrides what the new outline actually changes.

No strength claim is made. A deeper plate behind a socket is more material, which is
not the same as a qualified load path.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.core.domain.octopus_grip_v2 import AimedGripSurfaceSpec
from src.core.domain.octopus_hand import OctopusHandSpec
from src.core.domain.octopus_palm_outline import PalmOutlineSpec
from src.core.domain.octopus_stem import ReinforcingStemSpec


@dataclass(frozen=True, slots=True)
class OctopusHandV2Spec(OctopusHandSpec):
    """No material-strength claim: dimensions describe a printable fit prototype."""

    #: Bambu Lab P2S, 256 x 256 x 256 mm. V1 declared 220, which is not this machine.
    max_bed_mm: float = 256.0

    #: Buttress standing on the plate behind each socket, tallest against the socket.
    stem_height_mm: float = 8.0
    stem_length_mm: float = 12.0
    #: The ramp stops here rather than at zero: a feather edge is below the weld
    #: distance `cleanup_mesh` uses, so it would be dissolved rather than printed.
    stem_edge_height_mm: float = 1.2
    stem_half_width_mm: float = 6.0
    #: How far the stem must stay under the arm's swept underside.
    stem_clearance_mm: float = 2.0
    #: Radii the swept-envelope invariant is sampled at, per millimetre of stem.
    stem_sample_density: int = 8

    #: One electrical pass-through per arm, so wiring reaches each finger without
    #: sharing the twenty tendon holes or the single channel at the palm axis.
    arm_wire_bore_diameter_mm: float = 6.0

    #: Square edges taken off the plate. The rim chamfer is cut at 45 degrees, which
    #: is the steepest the underside can be and still print off the bed unsupported —
    #: the same limit the V1 grip pad's chamfer sits on.
    palm_rim_chamfer_mm: float = 1.5
    #: The five points cut back to short flats. Softens the shape and removes the
    #: only remaining vertical square edges, at the cost of corner reach.
    palm_corner_truncation_mm: float = 3.0

    #: Taken off the grip pad's upward face, so it eases into the disc instead of
    #: ending on a square edge — the pad's half of "no right angles left". Small,
    #: because it is subtracted from the gripping face and the face is the point.
    pad_top_chamfer_mm: float = 0.6
    #: See AimedGripSurfaceSpec: not the tip fuse, so the pad and cap never share a radius.
    pad_fuse_mm: float = 0.8
    #: 3.0 puts the cap's flare at exactly 45 degrees, which makes its radius at the
    #: trim plane exactly the disc's radius — a graze the Boolean cannot resolve.
    tip_cap_flare_mm: float = 4.0
    #: Eight, not V1's six: a cap's face centres reach all four grip directions only
    #: when the facet count is a multiple of four. Twelve would too, at the cost of
    #: narrowing each contact face from 16.07 mm to 10.87 mm.
    tip_facet_count: int = 8

    def __post_init__(self) -> None:
        OctopusHandSpec.__post_init__(self)

        # Aiming is the whole point of the pad change, so it is a rule rather than a
        # comment: every twist the chain uses must have a pad pointing at the palm
        # centre, and the pad set must map onto itself under that twist — otherwise
        # the bodies stop sharing one mesh and the export grows a second master.
        placed = set(self.grip_pad_angles_deg)
        for twist in self.body_twists_deg:
            if (180.0 - twist) % 360.0 not in placed:
                raise ValueError("a body twist has no pad facing the palm centre")
            if {(angle + twist) % 360.0 for angle in placed} != placed:
                raise ValueError("pad pattern is not invariant under the body twist")

        # Softening the plate spends the very surplus turning the pentagon won. The
        # corner is cut back along each arm's own heading, so the truncation comes
        # straight out of the material standing behind that arm's socket.
        if self.socket_heading_clearance_mm < self.palm_wall_mm:
            raise ValueError("corner truncation cuts into the socket's own wall")
        if 2 * self.palm_rim_chamfer_mm >= self.palm_thickness_mm:
            raise ValueError("rim chamfers meet in the middle of the plate")
        if self.palm_rim_chamfer_mm <= self.weld_distance_mm:
            raise ValueError("rim chamfer is finer than the mesh weld distance")

        # Building the stem enforces its own rules: that it tapers, that it clears the
        # ears the arm hangs by, and that it stays under everything the base joint
        # sweeps over it. What this layer adds is that it stands on plate that is
        # still flat — the rim chamfer eats into the top face the stem is built on.
        stem = self.stem
        if stem.outer_radius_mm > self.palm_top_face_reach_mm:
            raise ValueError("stem runs off the chamfered edge of the plate")

        # The plate is smaller than V1's, so the holes drilled through it are no
        # longer obviously inside it. Measured against the polygon's real boundary at
        # each hole's own heading, not against the inradius: near a corner the plate
        # reaches much further than the inradius, and near an edge it does not.
        if any(
            math.hypot(x, y) + self.cable_relief_radius_mm + self.palm_wall_mm
            > self.palm_boundary_radius_at_mm(math.degrees(math.atan2(y, x)))
            for x, y in self.tendon_hole_positions_mm
        ):
            raise ValueError("a tendon hole reaches past the palm edge")

        # Each arm's wire bore is a hole in a plate that is already crowded: four
        # tendon holes with counterbores around it, a socket root standing on it, the
        # palm's own channel inboard, and the neighbouring arms' bores either side.
        keep_out = self.arm_wire_bore_radius_mm + self.palm_wall_mm
        for index, (bore_x, bore_y) in enumerate(self.arm_wire_bore_positions_mm):
            if keep_out + self.wire_channel_diameter_mm / 2 > math.hypot(bore_x, bore_y):
                raise ValueError("an arm wire bore breaks into the central channel")
            # No "past the palm edge" check here, deliberately. The bore is placed
            # inboard of its station by a derived offset that only ever grows with the
            # bore, so it cannot reach the rim — a guard for that would be a branch
            # nothing can execute, which reads like cover and provides none.
            for other_x, other_y in self.arm_wire_bore_positions_mm[index + 1 :]:
                if math.dist((bore_x, bore_y), (other_x, other_y)) < 2 * keep_out:
                    raise ValueError("neighbouring arms' wire bores run into each other")
            for hole_x, hole_y in self.tendon_hole_positions_mm:
                gap = math.dist((bore_x, bore_y), (hole_x, hole_y))
                # Against the relief's radius, not the drill's: the counterbore is
                # the wider of the two and it is what would break through first.
                if gap < keep_out + self.cable_relief_radius_mm:
                    raise ValueError("an arm wire bore breaks into a tendon hole")

    # ------------------------------------------------------ pads aimed at the grasp

    @property
    def grip(self) -> AimedGripSurfaceSpec:
        """The contact surfaces, aimed rather than merely placed on the free rim."""
        return AimedGripSurfaceSpec(
            arm=self.arm_spec,
            grip_outer_diameter_mm=self.grip_outer_diameter_mm,
            grip_pad_height_mm=self.grip_pad_height_mm,
            grip_pad_arc_deg=self.grip_pad_arc_deg,
            grip_pad_slope_deg=self.grip_pad_slope_deg,
            tip_facet_count=self.tip_facet_count,
            tip_cap_flare_mm=self.tip_cap_flare_mm,
            tip_cap_height_mm=self.tip_cap_height_mm,
            tip_cap_top_diameter_mm=self.tip_cap_top_diameter_mm,
            tip_cable_bore_diameter_mm=self.tip_cable_bore_diameter_mm,
            tip_feature_fuse_mm=self.tip_feature_fuse_mm,
            pad_top_chamfer_mm=self.pad_top_chamfer_mm,
            pad_fuse_mm=self.pad_fuse_mm,
        )

    @property
    def body_twists_deg(self) -> tuple[float, ...]:
        """Every twist that occurs in an arm, which is what the pads must serve."""
        return tuple(
            self.body_twist_deg(index) % 360.0 for index in range(1, self.arm_body_count + 1)
        )

    @property
    def inward_pad_angles_deg(self) -> tuple[float, ...]:
        """The local heading that faces the palm centre, one per twist in the chain.

        A body at station A turned by twist T presents a pad at local heading h to
        global heading A + T + h; the palm's centre lies at A + 180. So the pad that
        aims at what the hand is closing on is at h = 180 - T, whatever the station.
        """
        return tuple(sorted({(180.0 - twist) % 360.0 for twist in self.body_twists_deg}))

    # ------------------------------------------------------------ the plate itself

    @property
    def palm_outline(self) -> PalmOutlineSpec:
        """The plate's shape, which owns its own truncation and chamfer rules."""
        return PalmOutlineSpec(
            arm=self.arm_spec,
            corner_count=self.arm_count,
            station_radius_mm=self.arm_station_radius_mm,
            wall_mm=self.palm_wall_mm,
            thickness_mm=self.palm_thickness_mm,
            rim_chamfer_mm=self.palm_rim_chamfer_mm,
            corner_truncation_mm=self.palm_corner_truncation_mm,
        )

    @property
    def palm_corner_angles_deg(self) -> tuple[float, ...]:
        return self.palm_outline.corner_angles_deg

    @property
    def palm_inradius_mm(self) -> float:
        return self.palm_outline.inradius_mm

    @property
    def palm_circumradius_mm(self) -> float:
        return self.palm_outline.circumradius_mm

    @property
    def palm_across_corners_mm(self) -> float:
        return self.palm_outline.across_corners_mm

    def palm_boundary_radius_at_mm(self, angle_deg: float) -> float:
        return self.palm_outline.boundary_radius_at_mm(angle_deg)

    @property
    def palm_corner_flat_radius_mm(self) -> float:
        return self.palm_outline.corner_flat_radius_mm

    @property
    def palm_corner_flat_half_width_mm(self) -> float:
        return self.palm_outline.corner_flat_half_width_mm

    @property
    def palm_outline_vertices_mm(self) -> tuple[tuple[float, float], ...]:
        return self.palm_outline.outline_vertices_mm

    @property
    def palm_enclosing_radius_mm(self) -> float:
        return self.palm_outline.enclosing_radius_mm

    @property
    def weld_distance_mm(self) -> float:
        return self.palm_outline.weld_distance_mm

    @property
    def palm_top_face_reach_mm(self) -> float:
        return self.palm_outline.top_face_reach_mm

    @property
    def palm_chamfer_slope_deg(self) -> float:
        return self.palm_outline.chamfer_slope_deg

    @property
    def socket_heading_clearance_mm(self) -> float:
        return self.palm_outline.socket_heading_clearance_mm

    @property
    def socket_edge_clearance_mm(self) -> float:
        return self.palm_outline.socket_edge_clearance_mm

    # ---------------------------------------------------------- wiring to an arm

    @property
    def arm_wire_bore_radius_mm(self) -> float:
        return self.arm_wire_bore_diameter_mm / 2

    @property
    def arm_wire_bore_station_offset_mm(self) -> float:
        """How far inboard of its own arm each bore sits.

        Beside the socket, not under it. A bore on the arm axis would be the obvious
        placement — it would line up with the channel running up the arm — but the
        socket's two root feet are buried in the plate either side of that axis, and
        a bore there undercuts the feet the ears stand on. Inboard by the root's
        radial reach plus a wall plus the bore's own radius clears them entirely.
        """
        return (
            self.arm_spec.root_profile_mm[0][2] + self.palm_wall_mm + self.arm_wire_bore_radius_mm
        )

    @property
    def arm_wire_bore_positions_mm(self) -> tuple[tuple[float, float], ...]:
        """One bore per arm, on the arm's own heading, in palm coordinates."""
        radius = self.arm_station_radius_mm - self.arm_wire_bore_station_offset_mm
        return tuple(
            (radius * math.cos(math.radians(angle)), radius * math.sin(math.radians(angle)))
            for angle in self.arm_station_angles_deg
        )

    @property
    def arm_wire_bore_closest_tendon_gap_mm(self) -> float:
        """Nearest a bore's wall comes to any tendon hole's counterbore, anywhere."""
        return min(
            math.dist(bore, hole) - self.arm_wire_bore_radius_mm - self.cable_relief_radius_mm
            for bore in self.arm_wire_bore_positions_mm
            for hole in self.tendon_hole_positions_mm
        )

    # ------------------------------------------------------- the reinforcing stem

    @property
    def stem(self) -> ReinforcingStemSpec:
        """The buttress, which owns its own printability and swept-clearance rules."""
        return ReinforcingStemSpec(
            arm=self.arm_spec,
            station_radius_mm=self.arm_station_radius_mm,
            palm_wall_mm=self.palm_wall_mm,
            height_mm=self.stem_height_mm,
            length_mm=self.stem_length_mm,
            edge_height_mm=self.stem_edge_height_mm,
            half_width_mm=self.stem_half_width_mm,
            clearance_mm=self.stem_clearance_mm,
            sample_density=self.stem_sample_density,
        )

    @property
    def palm_top_face_z_mm(self) -> float:
        return self.stem.palm_top_face_z_mm

    @property
    def stem_inner_radius_mm(self) -> float:
        return self.stem.inner_radius_mm

    @property
    def stem_outer_radius_mm(self) -> float:
        return self.stem.outer_radius_mm

    def stem_top_z_mm(self, radius_mm: float) -> float:
        return self.stem.top_z_mm(radius_mm)

    def base_joint_swept_floor_mm(self, radius_mm: float) -> float | None:
        return self.stem.swept_floor_mm(radius_mm)

    @property
    def stem_headroom_mm(self) -> float:
        return self.stem.headroom_mm

    @property
    def stem_slope_deg(self) -> float:
        return self.stem.slope_deg
