"""How many of everything a hand is, read off the spec instead of typed twice.

`model_finger_v3.py` wrote `4 *` and `["F1", "F2", "F3", "F4", "T"]` by hand and
the contract wrote them again. The counts here are the one place both read.
"""

from src.core.domain.palm_v3 import AnthropomorphicPalmSpec
from src.core.planning.expected_counts import expected_counts
from src.core.planning.naming import NamingPolicy

PALM = AnthropomorphicPalmSpec()
NAMING = NamingPolicy("HJ_", "V3")


def test_the_v3_counts_are_the_ones_the_generator_and_contracts_hard_code() -> None:
    counts = expected_counts(PALM, NAMING)

    assert counts.units_per_finger == 3
    assert counts.units_per_thumb == 3
    assert counts.row_finger_count == 4
    assert counts.stations == ("F1", "F2", "F3", "F4", "T")
    assert counts.hand_unit_count == 15
    assert counts.layout_part_count == 4
    assert counts.phalanx_part_count == 1


def test_the_stale_scene_expectations_are_what_the_generator_used_to_type() -> None:
    counts = expected_counts(PALM, NAMING)

    assert counts.stale_scene_expectations(NAMING) == {
        "HJ_V3_PHALANX_": 3,
        "HJ_V3_LAYOUT_PART_": 4,
        "HJ_V3_HAND_": 15,
        "HJ_V3_PALM": 1,
    }


def test_the_layout_holds_every_printed_unit_plus_the_palm() -> None:
    """Three identical phalanges are still three prints; the layout is what the slicer sees."""
    counts = expected_counts(PALM, NAMING)

    assert counts.layout_part_count == counts.units_per_finger + 1
