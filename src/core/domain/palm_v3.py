"""An anthropomorphic palm, judged by the one thing that makes it a hand.

Four fingers in a row and a thumb across from them. Every dimension here can be
right — sockets the right size, fingers the right length, plate the right width —
and the thing still not be a hand, because the thumb sweeps past the index
instead of meeting it. Opposition is the only reason a thumb exists, so it is
the acceptance condition, and it is computed rather than drawn.

A finger is a planar chain with known segment lengths and known joint limits, so
where its tip can go is arithmetic. Whether two such reachable sets come within
touching distance is arithmetic too. `thumb_index_tip_gap_mm` is that number.

This composes `SingleTendonFingerSpec`; V3's palm is not a subtype of the
octopus hand's pentagon and does not inherit from it. See `octopus_hand_v2` for
what a radially symmetric plate assumes.

No force claim. Reach and clearance are geometry; what the hand can hold is
measured on a bench.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.core.domain.finger_v3 import SingleTendonFingerSpec
from src.core.domain.hinge_chain import HingePhalanxSpec

#: Joint angles sampled when asking where a fingertip can reach. Coarse on
#: purpose: this answers "can these two ever meet", not "by what path".
_SAMPLES_DEG = (0.0, 10.0, 20.0, 30.0, 40.0, 50.0)

Vector3 = tuple[float, float, float]


def _rotate_y(vector: Vector3, degrees: float) -> Vector3:
    angle = math.radians(degrees)
    x, y, z = vector
    return (
        x * math.cos(angle) + z * math.sin(angle),
        y,
        -x * math.sin(angle) + z * math.cos(angle),
    )


def _rotate_z(vector: Vector3, degrees: float) -> Vector3:
    angle = math.radians(degrees)
    x, y, z = vector
    return (x * math.cos(angle) - y * math.sin(angle), x * math.sin(angle) + y * math.cos(angle), z)


@dataclass(frozen=True, slots=True)
class AnthropomorphicPalmSpec:
    """No grip-force claim: reach, spacing and clearance, not a rated hand."""

    finger: SingleTendonFingerSpec = SingleTendonFingerSpec()
    #: The thumb is a shorter chain, not a fifth copy of the finger. Measured
    #: rather than assumed: a three-joint thumb is 168.5 mm long, and swinging
    #: that across a 114 mm palm carries the tip 78 mm out the far side — it
    #: overshoots the fingers instead of meeting them, at every posture. Two
    #: joints give 114.5 mm, which is also what a hand has: two phalanges.
    thumb: SingleTendonFingerSpec = SingleTendonFingerSpec(
        link=HingePhalanxSpec(joint_count=2, joint_center_offset_mm=27.0),
        moment_arms_mm=(6.6, 6.6),
    )
    #: Air between neighbouring fingers along the row.
    finger_gap_mm: float = 6.0
    #: How far the thumb's root sits outboard of the row, and how far down.
    thumb_offset_mm: float = 26.0
    thumb_base_drop_mm: float = 30.0
    #: How far the thumb's root stands proud of the palm plane, towards the
    #: palmar side. Without it the thumb swings in the plane of the fingers and
    #: can only ever meet them edge-on; a real thumb comes up from in front, and
    #: that is what turns a sideways finger into an opposable one.
    thumb_base_palmar_mm: float = 22.0
    #: Swings the thumb's axis across the palm. Zero leaves it a fifth finger.
    #:
    #: These four numbers were chosen by scanning the placement space against
    #: `thumb_index_tip_gap_mm` inside physically sensible bounds, not by eye.
    #: Both `thumb_base_palmar_mm` and `thumb_base_drop_mm` sit at the edge of
    #: those bounds, and that is the honest answer rather than an accident: the
    #: root wants to be as far forward and as high as it is allowed to be. Its
    #: forward limit is the palm's own thickness — further than that and the
    #: thumb is mounted on a stalk in front of the hand, which reaches the index
    #: tip while being no kind of thumb.
    thumb_opposition_deg: float = 40.0
    #: Rolls the thumb's bending plane so its pad turns towards the fingers.
    thumb_palmar_tilt_deg: float = -15.0
    #: How close two tips must come to count as touching. Generous, because this
    #: is a reachability question answered on a coarse grid, not a contact model.
    pinch_contact_mm: float = 22.0
    #: Where the two sleeves are clamped, and where the syringe pushes in. The
    #: outer glove itself is bought, not designed — see docs/hand-v3/07-interfaces.
    cuff_clamp_wall_mm: float = 3.0
    air_port_diameter_mm: float = 6.0
    #: Refuse an unopposable thumb outright instead of only reporting the gap.
    #: Off by default so a caller can measure a deliberately flat hand and
    #: compare — the guard needs a case it fires on to be worth anything.
    strict: bool = False

    def __post_init__(self) -> None:
        if self.finger_gap_mm <= 0:
            raise ValueError("neighbouring fingers need air between them")
        if self.pinch_contact_mm <= 0:
            raise ValueError("a contact distance of zero can never be met")
        if self.cuff_clamp_wall_mm < self.finger.link.minimum_wall_mm:
            raise ValueError("the cuff clamp is thinner than the minimum printable wall")
        if self.air_port_diameter_mm < 4.0:
            raise ValueError("the air port must take a syringe fitting")
        if self.thumb_offset_mm <= 0 or self.thumb_base_drop_mm <= 0:
            raise ValueError("the thumb root must sit outboard of and below the row")
        if self.thumb_base_palmar_mm < 0:
            raise ValueError("the thumb root cannot sit behind the back of the hand")
        if self.strict and self.thumb_index_tip_gap_mm >= self.pinch_contact_mm:
            raise ValueError(
                "the thumb cannot reach the index fingertip: closest approach is "
                f"{self.thumb_index_tip_gap_mm:.1f} mm against a "
                f"{self.pinch_contact_mm:.1f} mm contact distance"
            )

    # ------------------------------------------------------------ the finger

    @staticmethod
    def segment_lengths_mm(finger: SingleTendonFingerSpec) -> tuple[float, ...]:
        """Base to first joint, then joint to joint, then last joint to the tip."""
        link = finger.link
        overhang = link.joint_center_offset_mm + link.lug_outer_diameter_mm / 2
        middles = (link.unit_pitch_mm,) * (link.joint_count - 1)
        return (link.joint_center_offset_mm, *middles, overhang)

    @property
    def finger_segment_lengths_mm(self) -> tuple[float, ...]:
        return self.segment_lengths_mm(self.finger)

    @property
    def thumb_segment_lengths_mm(self) -> tuple[float, ...]:
        return self.segment_lengths_mm(self.thumb)

    def tip_in_frame_mm(
        self, lengths: tuple[float, ...], angles_deg: tuple[float, ...]
    ) -> tuple[float, float]:
        """Tip position in a chain's own bending plane, as (palmar, along).

        Palmar is negative because that is the way a finger closes: the tip
        travels towards the side the tendon runs on.
        """
        palmar = 0.0
        along = 0.0
        turned = 0.0
        for index, length in enumerate(lengths):
            if index:
                turned += angles_deg[index - 1]
            radians = math.radians(turned)
            palmar -= length * math.sin(radians)
            along += length * math.cos(radians)
        return (palmar, along)

    def fingertip_in_finger_frame_mm(self, angles_deg: tuple[float, ...]) -> tuple[float, float]:
        return self.tip_in_frame_mm(self.finger_segment_lengths_mm, angles_deg)

    # -------------------------------------------------------------- the palm

    @property
    def row_pitch_mm(self) -> float:
        return self.finger.link.body_width_mm + self.finger_gap_mm

    @property
    def row_finger_x_mm(self) -> tuple[float, ...]:
        """Four roots evenly spaced across the plate, index first."""
        pitch = self.row_pitch_mm
        return tuple((index - 1.5) * pitch for index in range(4))

    @property
    def palm_width_mm(self) -> float:
        return 3 * self.row_pitch_mm + self.finger.link.body_width_mm

    @property
    def air_port_center_mm(self) -> tuple[float, float]:
        """On the back of the hand, clear of anything the palm grips with."""
        return (0.0, self.finger.link.body_depth_mm / 2)

    # -------------------------------------------------------- can it oppose?

    def _row_tip_world(self, x_mm: float, angles_deg: tuple[float, ...]) -> Vector3:
        palmar, along = self.fingertip_in_finger_frame_mm(angles_deg)
        return (x_mm, palmar, along)

    def _thumb_tip_world(self, angles_deg: tuple[float, ...]) -> Vector3:
        palmar, along = self.tip_in_frame_mm(self.thumb_segment_lengths_mm, angles_deg)
        # The thumb's frame is the row frame swung across the palm, then rolled so
        # its pad turns to face the fingers. Both turns are needed: the swing alone
        # produces a finger pointing sideways, which still cannot oppose anything.
        axis = _rotate_z(_rotate_y((0.0, 0.0, 1.0), self.thumb_opposition_deg), 0.0)
        pad = _rotate_z(
            _rotate_y((0.0, -1.0, 0.0), self.thumb_opposition_deg), self.thumb_palmar_tilt_deg
        )
        origin = (
            self.row_finger_x_mm[0] - self.thumb_offset_mm,
            -self.thumb_base_palmar_mm,
            -self.thumb_base_drop_mm,
        )
        return tuple(  # type: ignore[return-value]
            origin[axis_index] + along * axis[axis_index] + (-palmar) * pad[axis_index]
            for axis_index in range(3)
        )

    @property
    def thumb_index_tip_gap_mm(self) -> float:
        """Closest the thumb tip can come to the index tip, over both reachable sets.

        A reachability question, not a posture: it asks whether *some* pair of
        postures brings the tips together, which is what "opposable" means. The
        grid is coarse, and `pinch_contact_mm` is correspondingly generous.
        """
        index_x = self.row_finger_x_mm[0]
        row_tips = [
            self._row_tip_world(index_x, angles)
            for angles in self._posture_grid(self.finger.link.joint_count)
        ]
        best = math.inf
        for thumb_angles in self._posture_grid(self.thumb.link.joint_count):
            thumb = self._thumb_tip_world(thumb_angles)
            for tip in row_tips:
                gap = math.dist(thumb, tip)
                if gap < best:
                    best = gap
        return best

    def _posture_grid(self, joints: int) -> tuple[tuple[float, ...], ...]:
        limit = self.finger.link.maximum_articulation_deg
        allowed = tuple(value for value in _SAMPLES_DEG if value <= limit)
        grid: list[tuple[float, ...]] = [()]
        for _ in range(joints):
            grid = [(*posture, angle) for posture in grid for angle in allowed]
        return tuple(grid)
