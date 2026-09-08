"""The print coupon's seven checks, judged by the machine from the user's readings.

`docs/hand-v3/v6b-coupon.md` asks for seven measurements on the first printed
phalanx. Comparing them to a tolerance band is not the user's job — the user
measures, the machine judges — and the bands are not typed here either: the
nominals come from the link spec, the protocol's offsets sit beside them with a
name, and a document guard holds the protocol table to the same numbers.

A single reading of a hole is vacuous. The protocol asks for two, turned 90°,
because ovality is the commonest printing failure and one reading cannot see
it. Vacuous never counts as a pass.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from src.core.domain.finger_link import FingerLinkSpec

#: Protocol tolerance below and above the nominal, in mm. A bore that shrinks
#: is the common case (over-extrusion, cooling), so the low side is tighter.
PIN_BORE_TOLERANCE_MM = (-0.15, 0.20)
#: The bearing seat must hold an MR84 by press fit: little room above nominal.
BEARING_SEAT_TOLERANCE_MM = (-0.15, 0.10)
#: Readings per hole, turned 90° between them.
READINGS_PER_HOLE = 2

BOOLEAN_CHECKS: dict[str, str] = {
    "C2": "Ø4.0 銷能手推穿過兩個耳片",
    "C4": "MR84 壓入後不自己掉出來",
    "C5": "腱孔(掌側)Ø2.0 線可穿過全長",
    "C6": "走線孔(背側)Ø2.0 線可穿過全長",
    "C7": "兩孔之間與孔到銷孔的壁目視無裂、無穿",
}

ITEM_ORDER = ("C1", "C2", "C3", "C4", "C5", "C6", "C7")

Measurement = Sequence[float] | bool | None


@dataclass(frozen=True, slots=True)
class Band:
    item: str
    what: str
    nominal_mm: float
    low_mm: float
    high_mm: float

    @property
    def text(self) -> str:
        return f"{self.low_mm:.2f}–{self.high_mm:.2f}"


@dataclass(frozen=True, slots=True)
class ItemVerdict:
    item: str
    #: PASS, FAIL or VACUOUS. Vacuous is "not enough readings", never a pass.
    status: str
    detail: str
    readings: tuple[float, ...] = ()
    #: One note per reading, so a row in the results table says what *that*
    #: reading did rather than repeating the item's verdict.
    reading_notes: tuple[str, ...] = ()


def coupon_bands(link: FingerLinkSpec) -> tuple[Band, ...]:
    """The two dimensional bands, nominal from the link, offsets from the protocol."""
    pin_low, pin_high = PIN_BORE_TOLERANCE_MM
    seat_low, seat_high = BEARING_SEAT_TOLERANCE_MM
    return (
        Band(
            "C1",
            "銷孔直徑",
            link.printed_pin_bore_mm,
            link.printed_pin_bore_mm + pin_low,
            link.printed_pin_bore_mm + pin_high,
        ),
        Band(
            "C3",
            "軸承座直徑",
            link.bearing_seat_diameter_mm,
            link.bearing_seat_diameter_mm + seat_low,
            link.bearing_seat_diameter_mm + seat_high,
        ),
    )


def _judge_band(band: Band, readings: Sequence[float]) -> ItemVerdict:
    values = tuple(float(value) for value in readings)
    notes: list[str] = []
    for value in values:
        if value < band.low_mm:
            notes.append(f"{value:.2f} 偏小(下限 {band.low_mm:.2f})")
        elif value > band.high_mm:
            notes.append(f"{value:.2f} 偏大(上限 {band.high_mm:.2f})")
        else:
            notes.append(f"在 {band.text} 內")
    if len(values) < READINGS_PER_HOLE:
        return ItemVerdict(
            band.item,
            "VACUOUS",
            f"只有 {len(values)} 次量測;每個孔量 {READINGS_PER_HOLE} 次(轉 90°)才算",
            values,
            tuple(notes),
        )
    failures = [note for note in notes if not note.startswith("在 ")]
    if failures:
        return ItemVerdict(band.item, "FAIL", "; ".join(failures), values, tuple(notes))
    return ItemVerdict(
        band.item, "PASS", f"{len(values)} 次量測都在 {band.text} 內", values, tuple(notes)
    )


def judge_coupon(
    link: FingerLinkSpec, measurements: Mapping[str, Measurement]
) -> tuple[ItemVerdict, ...]:
    """Every item C1–C7 gets a verdict; an item not measured is vacuous, not skipped."""
    bands = {band.item: band for band in coupon_bands(link)}
    verdicts: list[ItemVerdict] = []
    for item in ITEM_ORDER:
        given = measurements.get(item)
        if item in bands:
            readings: Sequence[float] = () if given is None or isinstance(given, bool) else given
            verdicts.append(_judge_band(bands[item], readings))
            continue
        what = BOOLEAN_CHECKS[item]
        if given is None:
            verdicts.append(ItemVerdict(item, "VACUOUS", f"未量:{what}"))
        elif given is True:
            verdicts.append(ItemVerdict(item, "PASS", what))
        else:
            verdicts.append(ItemVerdict(item, "FAIL", f"沒過:{what}"))
    return tuple(verdicts)


def coupon_passed(verdicts: Sequence[ItemVerdict]) -> bool:
    return bool(verdicts) and all(verdict.status == "PASS" for verdict in verdicts)


def result_rows(verdicts: Sequence[ItemVerdict], date: str) -> list[str]:
    """Markdown rows for `v8-results`: one reading per row, never averaged."""
    rows: list[str] = []
    for verdict in verdicts:
        if verdict.readings:
            for value, note in zip(verdict.readings, verdict.reading_notes, strict=True):
                rows.append(
                    f"| {date} | {verdict.item} | {value:.2f} | {verdict.status} | {note} |"
                )
        else:
            rows.append(f"| {date} | {verdict.item} | — | {verdict.status} | {verdict.detail} |")
    return rows
