"""V6 profile: four-way roots and two experimentally printable retention styles."""

from dataclasses import dataclass

from src.core.domain.inset_hinge import InsetHingeSpec


@dataclass(frozen=True, slots=True)
class BiaxialHingeSpec(InsetHingeSpec):
    body_outer_diameter_mm: float = 36.0
    joint_center_offset_mm: float = 9.5
    lug_outer_diameter_mm: float = 10.6

    def __post_init__(self) -> None:
        InsetHingeSpec.__post_init__(self)
        if (self.lug_outer_diameter_mm - self.retainer_seat_diameter_mm) / 2 < 2:
            raise ValueError("retainer recess leaves insufficient ear wall")
        base, shoulder, _ = self.root_profile_mm
        mate_inner = self.side_female_center_mm - self.lug_thickness_mm / 2
        at_mate = base[0] + (base[1] - (mate_inner - self.side_male_center_mm)) * (
            shoulder[0] - base[0]
        ) / (base[1] - shoulder[1])
        if self.joint_center_offset_mm - at_mate - self.lug_outer_diameter_mm / 2 < 0.2:
            raise ValueError("side ramp enters the mating circular ear envelope")
        if not self.groove_diameter_mm < self.clip_inner_diameter_mm < self.pin_diameter_mm:
            raise ValueError("clip must fit the groove but be stopped by its shoulders")

    @property
    def root_profile_mm(self) -> tuple[tuple[float, float, float], ...]:
        return ((1.8, 5.1, 6.5), (4.4, 1.5, 3.0), (5.7, 1.5, 1.5))

    @property
    def retention_styles(self) -> tuple[str, str]:
        return ("print_in_place_double_head", "separate_pin_and_clip")

    @property
    def retainer_diameter_mm(self) -> float:
        return 6.0

    @property
    def retainer_seat_diameter_mm(self) -> float:
        return 6.6

    @property
    def retainer_seat_depth_mm(self) -> float:
        return 1.8

    @property
    def retainer_inner_radius_mm(self) -> float:
        return self.side_male_center_mm - self.lug_thickness_mm / 2 + 0.3

    @property
    def retainer_thickness_mm(self) -> float:
        return 1.2

    @property
    def groove_length_mm(self) -> float:
        return 1.2

    @property
    def groove_diameter_mm(self) -> float:
        return 3.0

    @property
    def clip_thickness_mm(self) -> float:
        return 0.9

    @property
    def clip_inner_diameter_mm(self) -> float:
        return 3.2

    @property
    def clip_opening_mm(self) -> float:
        return 2.6
