"""The print layout's arithmetic, out from behind `import bpy`.

`finger_v3_presentation.build_print_layout` learned three things the hard way —
parts spaced by their own width, placement baked into the mesh, rows wrapping
at the bed — and every one of them could only be checked by building the parts.
The same algorithm here takes footprints and returns slots, so "does it fit the
plate" is a unit test, and the execution layer only bakes what it is told.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from src.core.domain.palm_v3 import AnthropomorphicPalmSpec
from src.core.planning.naming import NamingPolicy

#: The one printer this project has. Becoming an instance field is DEFERRALS D-006.
BED_MM = 256.0
GAP_MM = 10.0


@dataclass(frozen=True, slots=True)
class Footprint:
    """A part laid flat: its printed width by its printed depth, both in mm."""

    name: str
    width_mm: float
    depth_mm: float


@dataclass(frozen=True, slots=True)
class Placement:
    name: str
    x_mm: float
    y_mm: float
    row: int


@dataclass(frozen=True, slots=True)
class LayoutPlan:
    placements: tuple[Placement, ...]
    footprint_mm: tuple[float, float]
    bed_mm: float
    gap_mm: float

    @property
    def fits_bed(self) -> bool:
        """False for an empty layout: nothing placed is not the same as fitting."""
        width, depth = self.footprint_mm
        return bool(self.placements) and width <= self.bed_mm and depth <= self.bed_mm


def pack(
    footprints: Sequence[Footprint], bed_mm: float = BED_MM, gap_mm: float = GAP_MM
) -> LayoutPlan:
    """Rows left to right, wrapping at the bed, the whole thing centred on the origin.

    Rows are built before anything is placed, because a row's depth is not
    known until the row is finished.
    """
    rows: list[list[Footprint]] = [[]]
    used = 0.0
    for part in footprints:
        if rows[-1] and used + gap_mm + part.width_mm > bed_mm:
            rows.append([])
            used = 0.0
        rows[-1].append(part)
        used += part.width_mm + (gap_mm if len(rows[-1]) > 1 else 0.0)

    slots: list[tuple[str, float, float, int]] = []
    row_top = 0.0
    widest = 0.0
    for row_index, row in enumerate(rows):
        if not row:
            continue
        row_depth = max(part.depth_mm for part in row)
        row_width = sum(part.width_mm for part in row) + gap_mm * (len(row) - 1)
        widest = max(widest, row_width)
        left = -row_width / 2
        for part in row:
            slots.append((part.name, left + part.width_mm / 2, row_top + row_depth / 2, row_index))
            left += part.width_mm + gap_mm
        row_top += row_depth + gap_mm
    total_depth = row_top - gap_mm if slots else 0.0

    placements = tuple(
        Placement(name, x_mm, y_mm - total_depth / 2, row) for name, x_mm, y_mm, row in slots
    )
    return LayoutPlan(placements, (widest, total_depth), bed_mm, gap_mm)


def part_footprints(palm: AnthropomorphicPalmSpec, naming: NamingPolicy) -> tuple[Footprint, ...]:
    """Each printed part's footprint laid on its side, from the spec alone.

    Laid flat swaps a part's z for its printed depth. A phalanx spans lug to
    lug along z and its body width across; the palm spans the thenar boss to the
    far plate edge across, and the plate plus a root's reach along z. The
    shipped manifest measures 24 × 67 and 140 × 103.5, and the tests hold these
    to those numbers.
    """
    link = palm.finger.link
    unit_width = max(link.body_width_mm, link.fork_total_width_mm)
    unit_depth = 2 * link.joint_center_offset_mm + link.lug_outer_diameter_mm
    units = tuple(
        Footprint(naming.phalanx(index), unit_width, unit_depth)
        for index in range(1, link.assembly_unit_count + 1)
    )
    palm_width = palm.palm_width_mm / 2 - (palm.thumb_root_mm[0] - link.body_width_mm / 2)
    palm_depth = palm.plate_height_mm + link.joint_center_offset_mm + link.lug_outer_diameter_mm / 2
    return (*units, Footprint(naming.palm(), palm_width, palm_depth))
