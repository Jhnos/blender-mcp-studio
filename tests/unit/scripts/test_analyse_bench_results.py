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


DECAY_EMPTY = """
| 日期 | 試次 | 氣壓方向 | 0 秒 kPa | 10 秒 kPa | 30 秒 kPa | 60 秒 kPa | 備註 |
|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | 尚未執行 |
"""

DECAY_FILLED = """
| 日期 | 試次 | 氣壓方向 | 0 秒 kPa | 10 秒 kPa | 30 秒 kPa | 60 秒 kPa | 備註 |
|---|---|---|---|---|---|---|---|
| 2026-09-20 | 1 | 加壓 | 40.0 | 36.0 | 30.0 | 22.0 | |
| 2026-09-20 | 2 | 加壓 | 42.0 | 38.0 | 31.0 | 24.0 | |
| 2026-09-20 | 3 | 加壓 | 41.0 | 35.0 | 29.0 | 21.0 | |
"""

LEAKY = """
| 日期 | 試次 | 氣壓方向 | 0 秒 kPa | 10 秒 kPa | 30 秒 kPa | 60 秒 kPa | 備註 |
|---|---|---|---|---|---|---|---|
| 2026-09-20 | 1 | 加壓 | 40.0 | 8.0 | 1.0 | 0.0 | |
| 2026-09-20 | 2 | 加壓 | 41.0 | 7.0 | 0.5 | 0.0 | |
| 2026-09-20 | 3 | 加壓 | 39.0 | 9.0 | 1.0 | 0.0 | |
"""


def test_a_decay_table_nobody_filled_in_reports_vacuous() -> None:
    from scripts.analyse_bench_results import decay_summary

    verdict = decay_summary(DECAY_EMPTY, hold_fraction=0.5)

    assert verdict.vacuous
    assert verdict.n == 0
    assert "vacuous" in verdict.summary.lower()


def test_a_seal_that_still_holds_at_ten_seconds_says_so_with_a_fraction() -> None:
    from scripts.analyse_bench_results import decay_summary

    verdict = decay_summary(DECAY_FILLED, hold_fraction=0.5, planned_trials=3)

    assert not verdict.vacuous
    assert verdict.n == 3
    # 36/40, 38/42, 35/41 -> 0.900, 0.905, 0.854. The median, not the mean:
    # one leaky run should not drag the summary down proportionally.
    assert verdict.retained_at_ten_seconds == pytest.approx(0.900, abs=0.01)
    assert verdict.holds
    assert "10 s" in verdict.summary


def test_a_layer_that_has_emptied_by_ten_seconds_refutes_the_hypothesis() -> None:
    """H8 says one inflation lasts ten seconds; this is what refuting it looks like."""
    from scripts.analyse_bench_results import decay_summary

    verdict = decay_summary(LEAKY, hold_fraction=0.5, planned_trials=3)

    assert not verdict.vacuous
    assert verdict.retained_at_ten_seconds < 0.25
    assert not verdict.holds


def test_the_holding_fraction_has_no_default_either() -> None:
    """Same discipline as the SESOI: how much pressure counts as still inflated
    is a decision about this hand, not a library constant."""
    from scripts.analyse_bench_results import decay_summary

    with pytest.raises(ValueError):
        decay_summary(DECAY_FILLED, hold_fraction=0.0)
    with pytest.raises(ValueError):
        decay_summary(DECAY_FILLED, hold_fraction=1.5)


def test_the_shipped_results_file_carries_a_table_for_the_decay_run() -> None:
    """A protocol that asks for numbers with nowhere to write them is not a protocol."""
    from scripts.analyse_bench_results import decay_summary

    root = Path(__file__).resolve().parents[3]
    text = (root / "docs" / "hand-v3" / "v8-results.md").read_text(encoding="utf-8")

    assert "10 秒 kPa" in text, "the results file has no column for the ten-second reading"
    assert decay_summary(text, hold_fraction=0.5).vacuous
