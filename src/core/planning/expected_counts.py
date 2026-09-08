"""How many of everything a hand is, read off the spec once.

`model_finger_v3.py` computed `4 * units + thumb_units` and listed the stations
by hand; the contract listed them again. Two hand-typed copies of one count is
how a contract came to describe a four-phalanx hand while the generator built
three. Both now read this.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.domain.palm_v3 import AnthropomorphicPalmSpec
from src.core.planning.naming import NamingPolicy


@dataclass(frozen=True, slots=True)
class ExpectedCounts:
    units_per_finger: int
    units_per_thumb: int
    row_finger_count: int
    #: Station labels in contract order: the row, then the thumb.
    stations: tuple[str, ...]
    #: Distinct phalanx part numbers — one per distinct moment arm.
    phalanx_part_count: int

    @property
    def hand_unit_count(self) -> int:
        return self.row_finger_count * self.units_per_finger + self.units_per_thumb

    @property
    def layout_part_count(self) -> int:
        """Every printed unit of one finger plus the palm.

        Units, not part numbers: three identical phalanges are still three
        prints, and the layout is what the slicer sees.
        """
        return self.units_per_finger + 1

    def stale_scene_expectations(self, naming: NamingPolicy) -> dict[str, int]:
        """What a clean build leaves under each prefix; anything else is a previous run."""
        return {
            naming.phalanx_prefix: self.units_per_finger,
            naming.layout_prefix: self.layout_part_count,
            naming.hand_prefix: self.hand_unit_count,
            naming.palm(): 1,
        }


def expected_counts(palm: AnthropomorphicPalmSpec, naming: NamingPolicy) -> ExpectedCounts:
    row = len(palm.row_finger_x_mm)
    labels = tuple(naming.station_label(index) for index in range(1, row + 1))
    return ExpectedCounts(
        units_per_finger=palm.finger.link.assembly_unit_count,
        units_per_thumb=palm.thumb.link.assembly_unit_count,
        row_finger_count=row,
        stations=(*labels, naming.station_label(None)),
        phalanx_part_count=palm.finger.phalanx_part_count,
    )
