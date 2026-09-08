"""The print layout's arithmetic, testable without opening Blender.

The wrap-at-the-bed algorithm lived behind `import bpy`, so the only way to know
whether five parts fit a plate was to build them. The real-machine gate measured
242.0 × 103.5 for the four V3 parts; the same number has to come out of here.
"""

import pytest

from src.core.domain.palm_v3 import AnthropomorphicPalmSpec
from src.core.planning.layout_plan import Footprint, pack, part_footprints
from src.core.planning.naming import NamingPolicy

PALM = AnthropomorphicPalmSpec()
NAMING = NamingPolicy("HJ_", "V3")


def test_the_v3_footprints_are_what_the_shipped_meshes_measure() -> None:
    """Laid flat, a part's footprint is its x by its z; the manifest pins both."""
    footprints = part_footprints(PALM, NAMING)

    assert [f.name for f in footprints] == [
        "HJ_V3_PHALANX_1",
        "HJ_V3_PHALANX_2",
        "HJ_V3_PHALANX_3",
        "HJ_V3_PALM",
    ]
    assert footprints[0].width_mm == pytest.approx(24.0)
    assert footprints[0].depth_mm == pytest.approx(67.0)
    assert footprints[3].width_mm == pytest.approx(140.0)
    assert footprints[3].depth_mm == pytest.approx(103.5)


def test_four_v3_parts_fill_one_row_at_the_measured_footprint() -> None:
    layout = pack(part_footprints(PALM, NAMING))

    assert layout.footprint_mm == pytest.approx((242.0, 103.5))
    assert layout.fits_bed
    assert [p.row for p in layout.placements] == [0, 0, 0, 0]
    # Centred on the bed: the row spans -121..121 and each slot is centred in turn.
    assert layout.placements[0].x_mm == pytest.approx(-121.0 + 12.0)
    assert layout.placements[3].x_mm == pytest.approx(121.0 - 70.0)


def test_a_fifth_part_wraps_to_a_second_row_instead_of_overrunning_the_bed() -> None:
    extra = (*part_footprints(PALM, NAMING), Footprint("HJ_V3_PALM_TWIN", 140.0, 103.5))

    layout = pack(extra)

    assert [p.row for p in layout.placements] == [0, 0, 0, 0, 1]
    assert layout.footprint_mm == pytest.approx((242.0, 217.0))
    assert layout.fits_bed


def test_a_part_wider_than_the_bed_is_reported_not_squeezed() -> None:
    layout = pack((Footprint("wide", 300.0, 10.0),))

    assert layout.footprint_mm == pytest.approx((300.0, 10.0))
    assert not layout.fits_bed


def test_an_empty_layout_is_vacuous_not_fitting() -> None:
    layout = pack(())

    assert layout.placements == ()
    assert not layout.fits_bed
