"""One object owns every name, so a contract and a scene cannot disagree on one.

The V3 generator carried three spellings of the same station — `F1`, `"1"` and
`ARM_1` — in three functions. Each was correct on its own; the point of the
policy is that there is one, and that a second instance gets its own namespace
so `run_generator` clearing one hand never clears the other.
"""

import pytest

from src.core.planning.naming import NamingPolicy

V3 = NamingPolicy(namespace="HJ_", family="V3")


def test_the_prefix_is_what_the_committed_contracts_and_manifest_pin() -> None:
    assert V3.prefix == "HJ_V3_"
    assert V3.phalanx(1) == "HJ_V3_PHALANX_1"
    assert V3.hand_unit("F1", 1) == "HJ_V3_HAND_F1_1"
    assert V3.hand_chain_prefix("T") == "HJ_V3_HAND_T_"
    assert V3.palm() == "HJ_V3_PALM"
    assert V3.thenar() == "HJ_V3_THENAR"
    assert V3.root("F2") == "HJ_V3_ROOT_F2"
    assert V3.cut("TENDON", "F3") == "HJ_V3_CUT_TENDON_F3"
    assert V3.layout_prefix == "HJ_V3_LAYOUT_PART_"
    assert V3.layout_part(4) == "HJ_V3_LAYOUT_PART_4"
    assert V3.layout_collection == "HJ_V3_LAYOUT"
    assert V3.finger_collection == "HJ_V3_FINGER"
    assert V3.scene_key("HAND_STATIONS") == "HJ_V3_HAND_STATIONS"
    assert V3.material("BODY") == "HJ_V3_BODY"


def test_station_labels_are_one_spelling() -> None:
    assert [V3.station_label(index) for index in range(1, 5)] == ["F1", "F2", "F3", "F4"]
    assert V3.station_label(None) == "T"


def test_scratch_cutters_live_in_the_namespace_not_the_family() -> None:
    """Transient booleans are cleared by prefix too, but never counted as parts."""
    assert V3.scratch("CUT_TENDON") == "HJ_CUT_TENDON"
    assert not V3.scratch("MALE_LUG").startswith(V3.prefix)


def test_two_instances_cannot_share_a_namespace_by_accident() -> None:
    compact = NamingPolicy(namespace="HK_", family="COMPACT")

    assert not compact.prefix.startswith(V3.prefix)
    assert not V3.prefix.startswith(compact.prefix)


@pytest.mark.parametrize(
    ("namespace", "family"),
    [("HJ", "V3"), ("", "V3"), ("HJ_", ""), ("HJ_", "_V3"), ("HJ_", "V3_")],
)
def test_a_malformed_namespace_or_family_is_refused(namespace: str, family: str) -> None:
    with pytest.raises(ValueError):
        NamingPolicy(namespace=namespace, family=family)
