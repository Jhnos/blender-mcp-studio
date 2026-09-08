"""Which bearing seats a link asks for — as data, so it can be checked anywhere.

The generator needs `bpy`, so nothing about it runs in this suite. The decision
inside it does not need `bpy` at all: a link either wants seats bored into its
fork lugs or it does not, and that is a list of cuts. Making it a list is what
lets the bearingless case be checked on a machine with no Blender on it.

Not cosmetic. A link with no bearing carries `bearing_width_mm = 0.0`, and the
unconditional code would hand a zero-height cylinder to a boolean — the kind of
degenerate input that produces either nothing or something non-manifold, and
that no per-dimension rule would have objected to.
"""

import pytest

from scripts.finger_v3_geometry import bearing_seat_cuts
from src.core.domain.compact_link import CompactHingeLinkSpec
from src.core.domain.hinge_chain import HingePhalanxSpec


def test_a_link_with_bearings_asks_for_one_seat_per_lug() -> None:
    link = HingePhalanxSpec(joint_count=2, joint_center_offset_mm=27.0)

    cuts = bearing_seat_cuts(link)

    assert len(cuts) == 2
    offsets = sorted(cut.offset_mm for cut in cuts)
    assert offsets[0] == pytest.approx(-offsets[1]), "the two seats mirror each other"
    for cut in cuts:
        assert cut.diameter_mm == pytest.approx(link.bearing_seat_diameter_mm)
        assert cut.width_mm == pytest.approx(link.bearing_width_mm)
        assert cut.width_mm > 0.0
        # Seated at the outer face of each lug, not buried in the middle.
        assert abs(cut.offset_mm) < link.fork_total_width_mm / 2.0


def test_a_bearingless_link_asks_for_nothing() -> None:
    """Zero cuts, not one cut of zero width. Those are different instructions."""
    link = CompactHingeLinkSpec()

    assert link.has_bearing_seat is False
    assert bearing_seat_cuts(link) == []


def test_no_cut_is_ever_degenerate() -> None:
    """The failure this exists to prevent, stated against every link in the repo."""
    for link in (
        HingePhalanxSpec(),
        HingePhalanxSpec(joint_count=2, joint_center_offset_mm=27.0),
        CompactHingeLinkSpec(),
        CompactHingeLinkSpec(joint_count=3),
    ):
        for cut in bearing_seat_cuts(link):
            assert cut.width_mm > 0.0
            assert cut.diameter_mm > 0.0
