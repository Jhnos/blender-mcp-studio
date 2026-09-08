"""The results table has to become a report without anyone calling a function.

`paired_bench_statistics` computes the verdict, but until something reads the
markdown table nobody gets a report by recording numbers — they get one by
writing Python, which is the same handover in a different costume.

Two of the matrix's remaining verifiers are about this report rather than about
the bench: that it carries n and an interval, and that the glove comparison
names two distinct outer layers. Both are checkable today, and the answer for an
empty table is `vacuous` — which is the check working, not the check waiting.
"""

from pathlib import Path

import pytest

from scripts.analyse_bench_results import (
    BenchTrial,
    parse_trials,
    report_lines,
    scenario_pairs,
)

EMPTY = """
| 日期 | 物體編號 | 外層手套編號 | 氣壓方向 | 目標壓力 kPa | 第幾次 | 滑脫質量 g | 滑脫力 N | 10 秒內滑脫? | 備註 |
|---|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | — | — | 尚未執行 |
"""

FILLED = """
| 日期 | 物體編號 | 外層手套編號 | 氣壓方向 | 目標壓力 kPa | 第幾次 | 滑脫質量 g | 滑脫力 N | 10 秒內滑脫? | 備註 |
|---|---|---|---|---|---|---|---|---|---|
| 2026-09-20 | OBJ01 | G1 | 未充氣 | 0 | 1 | 500 | 4.91 | 否 | |
| 2026-09-20 | OBJ01 | G1 | 充氣 | 40 | 1 | 800 | 7.85 | 否 | |
| 2026-09-20 | OBJ02 | G1 | 未充氣 | 0 | 1 | 450 | 4.41 | 否 | |
| 2026-09-20 | OBJ02 | G1 | 充氣 | 40 | 1 | 700 | 6.87 | 否 | |
"""


def test_a_table_nobody_has_filled_in_parses_to_nothing() -> None:
    """The placeholder row is not a trial, and must not become one."""
    assert parse_trials(EMPTY) == []


def test_recorded_trials_come_back_as_numbers_not_text() -> None:
    trials = parse_trials(FILLED)

    assert len(trials) == 4
    assert isinstance(trials[0], BenchTrial)
    assert trials[0].object_id == "OBJ01"
    assert trials[0].condition == "未充氣"
    assert trials[0].slip_force_n == pytest.approx(4.91)


def test_trials_pair_by_object_across_the_two_conditions() -> None:
    pairs = scenario_pairs(parse_trials(FILLED), before="未充氣", after="充氣")

    assert pairs == [(4.91, 7.85), (4.41, 6.87)]


def test_an_object_measured_in_only_one_condition_is_dropped_not_guessed() -> None:
    """Half a pair is not a pair, and filling in the other half is fabrication."""
    lopsided = FILLED + "| 2026-09-20 | OBJ03 | G1 | 充氣 | 40 | 1 | 900 | 8.83 | 否 | |\n"

    assert len(scenario_pairs(parse_trials(lopsided), before="未充氣", after="充氣")) == 2


def test_the_report_of_an_empty_table_says_vacuous_and_never_a_number() -> None:
    lines = report_lines(EMPTY, sesoi=0.5)

    joined = "\n".join(lines)
    assert "vacuous" in joined.lower()
    assert "0 of 10" in joined


def test_every_reported_scenario_carries_its_population_and_an_interval() -> None:
    """The matrix asks for exactly this and it is checkable without a bench."""
    lines = report_lines(FILLED, sesoi=0.5)

    body = [line for line in lines if line.startswith("S")]
    assert body, "the report stopped naming scenarios"
    for line in body:
        assert "n=" in line, line
        assert "CI" in line or "vacuous" in line.lower(), line


def test_the_glove_comparison_names_two_distinct_outer_layers() -> None:
    """S10 is meaningless with one glove: the whole point is two of them."""
    one_glove = report_lines(FILLED, sesoi=0.5)

    assert any("S10" in line and "vacuous" in line.lower() for line in one_glove)


def test_the_shipped_results_file_parses_and_reports_vacuous() -> None:
    """The real document, so a change to its shape breaks this rather than the bench."""
    root = Path(__file__).resolve().parents[3]
    text = (root / "docs" / "hand-v3" / "v8-results.md").read_text(encoding="utf-8")

    assert parse_trials(text) == []
    assert any("vacuous" in line.lower() for line in report_lines(text, sesoi=0.5))
