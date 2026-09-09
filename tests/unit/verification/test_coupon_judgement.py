"""The coupon's seven checks are judged by the machine; the user only measures.

`docs/hand-v3/v6b-coupon.md` gives the user seven things to measure on the
first printed phalanx and a tolerance band for each. Until now the comparison
was theirs to do by eye against a table — which is the one job this project
is not allowed to hand over. The bands derive from the link spec, the verdict
is computed, a single reading is vacuous, and the document's table is held to
the same numbers.
"""

from pathlib import Path

import pytest

from src.core.domain.palm_v3 import AnthropomorphicPalmSpec
from src.verification.coupon_judgement import (
    coupon_bands,
    coupon_passed,
    judge_coupon,
    result_rows,
)

LINK = AnthropomorphicPalmSpec().finger.link
ROOT = Path(__file__).resolve().parents[3]


def test_the_bands_derive_from_the_link_and_match_the_protocol() -> None:
    bands = {band.item: band for band in coupon_bands(LINK)}

    assert bands["C1"].nominal_mm == LINK.printed_pin_bore_mm == 4.5
    assert (bands["C1"].low_mm, bands["C1"].high_mm) == pytest.approx((4.35, 4.70))
    assert bands["C3"].nominal_mm == LINK.bearing_seat_diameter_mm == 8.1
    assert (bands["C3"].low_mm, bands["C3"].high_mm) == pytest.approx((7.95, 8.20))


def test_the_protocol_document_quotes_the_bands_the_judge_uses() -> None:
    doc = (ROOT / "docs" / "hand-v3" / "v6b-coupon.md").read_text(encoding="utf-8")
    for band in coupon_bands(LINK):
        quoted = f"{band.low_mm:.2f}–{band.high_mm:.2f}"
        assert quoted in doc, f"{band.item}: the protocol no longer says {quoted}"


def test_two_readings_inside_the_band_pass_and_one_outside_fails_with_the_direction() -> None:
    verdicts = {v.item: v for v in judge_coupon(LINK, {"C1": (4.52, 4.48), "C3": (7.80, 8.05)})}

    assert verdicts["C1"].status == "PASS"
    assert verdicts["C3"].status == "FAIL"
    assert "7.80" in verdicts["C3"].detail and "偏小" in verdicts["C3"].detail


def test_a_single_reading_is_vacuous_not_a_pass() -> None:
    """The protocol asks for two readings per hole, turned 90°, because ovality hides in one."""
    verdicts = {v.item: v for v in judge_coupon(LINK, {"C1": (4.5,)})}

    assert verdicts["C1"].status == "VACUOUS"
    assert not coupon_passed(judge_coupon(LINK, {"C1": (4.5,)}))


def test_boolean_checks_pass_fail_or_stay_vacuous() -> None:
    verdicts = {v.item: v for v in judge_coupon(LINK, {"C2": True, "C4": False})}

    assert verdicts["C2"].status == "PASS"
    assert verdicts["C4"].status == "FAIL"
    assert verdicts["C5"].status == "VACUOUS"


def test_the_coupon_passes_only_when_all_seven_pass() -> None:
    full = {
        "C1": (4.52, 4.48),
        "C2": True,
        "C3": (8.05, 8.12),
        "C4": True,
        "C5": True,
        "C6": True,
        "C7": True,
    }
    assert coupon_passed(judge_coupon(LINK, full))
    assert not coupon_passed(judge_coupon(LINK, {**full, "C6": False}))
    assert not coupon_passed(judge_coupon(LINK, {**full, "C7": None}))


def test_result_rows_are_one_reading_per_row_never_averaged() -> None:
    rows = result_rows(judge_coupon(LINK, {"C1": (4.52, 4.48)}), date="2026-09-10")

    assert len([r for r in rows if r.startswith("| 2026-09-10 | C1 |")]) == 2
    assert not any("4.50" in r for r in rows), "the two readings were averaged away"


def test_a_bearingless_link_has_one_band_not_two() -> None:
    """The compact link holds its seat diameter equal to the bore so that a
    consumer subtracting a seat removes nothing. Quoting that equality as an
    acceptance band would present a feature that is not there as measured."""
    from src.core.domain.compact_link import CompactHingeLinkSpec

    bands = coupon_bands(CompactHingeLinkSpec())

    assert [band.item for band in bands] == ["C1"]


def test_the_bearing_items_are_not_applicable_on_a_bearingless_link() -> None:
    from src.core.domain.compact_link import CompactHingeLinkSpec

    verdicts = {
        verdict.item: verdict
        for verdict in judge_coupon(
            CompactHingeLinkSpec(),
            {"C1": (2.40, 2.42), "C2": True, "C5": True, "C6": True, "C7": True},
        )
    }

    assert verdicts["C3"].status == "N/A"
    assert verdicts["C4"].status == "N/A"
    assert coupon_passed(tuple(verdicts.values()))


def test_the_same_readings_on_a_bearing_link_do_not_pass() -> None:
    """Should-fire. If N/A leaked into the link that does have a seat, the
    coupon would go green on a part whose bearing nobody checked."""
    from src.core.domain.hinge_chain import HingePhalanxSpec

    verdicts = judge_coupon(
        HingePhalanxSpec(),
        {"C1": (4.50, 4.52), "C2": True, "C5": True, "C6": True, "C7": True},
    )
    by_item = {verdict.item: verdict for verdict in verdicts}

    assert by_item["C3"].status == "VACUOUS"
    assert by_item["C4"].status == "VACUOUS"
    assert not coupon_passed(verdicts)


def test_a_coupon_where_nothing_applies_is_not_a_pass() -> None:
    """Every item N/A would otherwise be vacuously true — the exact shape this
    module already refuses for a hole measured once."""
    from src.verification.coupon_judgement import ItemVerdict

    assert not coupon_passed([ItemVerdict("C3", "N/A", "no seat")])
