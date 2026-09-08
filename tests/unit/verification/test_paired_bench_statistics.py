"""The bench numbers have to become a verdict without a human doing statistics.

`v6-scripts.md` says the protocol reports effect size and a confidence interval and
does not invent its own test. Until now nothing computed either: the user was to
record ten paired trials per object and then, somehow, produce a paired comparison
by hand. That is exactly the analysis this project is not allowed to hand over.

Routed per `applied-statistics:experiment-statistics`: two groups, paired,
continuous. The nonparametric branch is taken by design rather than by a normality
test, because at ten pairs a normality test cannot discriminate and choosing the
branch by one is theatre. Effect size is the matched-pairs rank-biserial
correlation, which is the ordinal effect size that branch asks for.
"""

import pytest

from src.verification.paired_bench_statistics import (
    ScenarioVerdict,
    assess_scenario,
    bootstrap_median_ci,
    holm_adjusted,
    rank_biserial,
    tost_equivalent,
    wilcoxon_signed_rank_p,
)


def test_a_scenario_with_no_trials_is_vacuous_and_never_a_pass() -> None:
    """The first gate is the population, before any ratio is computed."""
    verdict = assess_scenario("S9", [], planned_pairs=10, sesoi=0.5)

    assert verdict.vacuous
    assert not verdict.significant
    assert verdict.n == 0
    assert "vacuous" in verdict.summary.lower()


def test_a_scenario_short_of_its_planned_population_is_vacuous_too() -> None:
    """Nine of ten is not a small sample, it is an incomplete one."""
    pairs = [(1.0, 2.0)] * 9
    verdict = assess_scenario("S9", pairs, planned_pairs=10, sesoi=0.5)

    assert verdict.vacuous
    assert verdict.n == 9


def test_every_pair_moving_the_same_way_is_the_smallest_possible_p() -> None:
    """Ten differences all positive is 2 of 1024 sign assignments, two-sided."""
    diffs = [float(value) for value in range(1, 11)]

    assert wilcoxon_signed_rank_p(diffs) == pytest.approx(2 / 1024, rel=1e-9)
    assert rank_biserial(diffs) == pytest.approx(1.0)


def test_differences_that_cancel_are_no_evidence_at_all() -> None:
    diffs = [1.0, -1.0, 2.0, -2.0, 3.0, -3.0]

    assert wilcoxon_signed_rank_p(diffs) == pytest.approx(1.0)
    assert rank_biserial(diffs) == pytest.approx(0.0)


def test_zero_differences_are_dropped_the_way_the_test_requires() -> None:
    """A pair that did not move carries no sign, so it leaves the test and n."""
    assert wilcoxon_signed_rank_p([0.0, 0.0, 1.0, 2.0, 3.0]) == pytest.approx(2 / 8)


def test_the_confidence_interval_brackets_the_median_and_is_reproducible() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

    low, high = bootstrap_median_ci(values, seed=7)
    again = bootstrap_median_ci(values, seed=7)

    assert low < 5.5 < high
    assert (low, high) == again, "a verdict that changes between runs is not a verdict"
    # An interval that spans the whole sample is the sample, not an interval.
    assert min(values) < low and high < max(values)
    # The first draft asserted a different seed gives a different interval. It does
    # not have to: ten integers make the resampled median coarse enough that two
    # seeds land in the same bin, and asserting otherwise tests the data, not the
    # code. Reproducibility is the property that matters.


def test_a_family_of_comparisons_is_corrected_before_anything_is_claimed() -> None:
    """Four scenarios are one family; Holm, because this is confirmatory and few."""
    assert holm_adjusted([0.01, 0.04]) == pytest.approx([0.02, 0.04])
    assert holm_adjusted([0.04, 0.01]) == pytest.approx([0.04, 0.02])
    # Monotone: an adjusted value never falls below one that came before it.
    adjusted = holm_adjusted([0.001, 0.008, 0.039, 0.041])
    assert adjusted == sorted(adjusted)


def test_a_non_significant_result_is_tested_for_equivalence_not_called_no_difference() -> None:
    """The headline error this guards: absence of evidence read as evidence of absence."""
    tight = [0.05, -0.04, 0.03, -0.02, 0.01, 0.0, -0.01, 0.02, -0.03, 0.04]
    assert tost_equivalent(tight, sesoi=0.5) is True

    wide = [3.0, -2.5, 4.0, -3.5, 2.0, -4.0, 1.0, -1.5, 3.5, -2.0]
    assert tost_equivalent(wide, sesoi=0.5) is False, "inconclusive is not equivalent"


def test_equivalence_cannot_be_run_without_a_smallest_effect_worth_caring_about() -> None:
    """No silent default: the SESOI is a domain decision, not a library constant."""
    with pytest.raises(ValueError):
        tost_equivalent([0.1, -0.1], sesoi=0.0)
    with pytest.raises(ValueError):
        assess_scenario("S9", [(1.0, 2.0)] * 10, planned_pairs=10, sesoi=-1.0)


def test_a_complete_scenario_reports_magnitude_uncertainty_and_a_verdict() -> None:
    inflated = [(10.0, 13.0), (11.0, 14.5), (9.5, 12.0), (12.0, 15.0), (10.5, 13.5)]
    pairs = inflated * 2

    verdict = assess_scenario("S9", pairs, planned_pairs=10, sesoi=0.5, seed=3)

    assert isinstance(verdict, ScenarioVerdict)
    assert not verdict.vacuous
    assert verdict.n == 10
    assert verdict.median_difference > 0
    assert verdict.confidence_interval[0] < verdict.median_difference
    assert verdict.effect_size == pytest.approx(1.0)
    assert verdict.significant
    # A bare p is a failure, so the summary has to carry the magnitude too.
    assert "CI" in verdict.summary and "p=" in verdict.summary


@pytest.mark.parametrize("count", [4, 5, 6, 7, 8, 9, 10, 11, 12])
def test_the_exact_null_matches_the_arithmetic_it_is_supposed_to_be(count: int) -> None:
    """Hand-rolled inference is only as good as what pins it down.

    `applied-statistics:experiment-statistics` says the primitives already exist
    and this layer should route over them rather than write new statistics. This
    project carries no scipy and no pure-Python exact Wilcoxon exists, so the
    test is written here — which means it needs pinning to something better than
    "it looked right".

    Two cases are analytically certain and need no reference table. When every
    difference shares a sign, exactly two of the 2^n sign assignments reach a
    statistic that extreme, so p is 2/2^n. And a p-value is a probability, so it
    can never leave [0, 1] whatever the ranks look like.
    """
    same_sign = [float(value) for value in range(1, count + 1)]

    assert wilcoxon_signed_rank_p(same_sign) == pytest.approx(2 / 2**count, rel=1e-9)
    assert wilcoxon_signed_rank_p([-value for value in same_sign]) == pytest.approx(
        2 / 2**count, rel=1e-9
    )
    assert 0.0 <= wilcoxon_signed_rank_p(same_sign) <= 1.0


def test_the_p_value_moves_the_way_evidence_moves() -> None:
    """One sign flipped is strictly weaker evidence than none flipped.

    Monotonicity is the cheapest property that a transcription error breaks, and
    it does not need a reference implementation to state.
    """
    clean = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    one_flipped = [-1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    two_flipped = [-1.0, -2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]

    assert (
        wilcoxon_signed_rank_p(clean)
        < wilcoxon_signed_rank_p(one_flipped)
        < wilcoxon_signed_rank_p(two_flipped)
    )


def test_tied_magnitudes_are_handled_as_a_permutation_over_the_observed_ranks() -> None:
    """Ties are where a textbook table and this implementation part company.

    With tied magnitudes the classical exact table no longer applies, because it
    assumes distinct ranks. What is computed here is the permutation null
    conditional on the ranks actually observed — a defensible answer to a
    slightly different question, and one worth stating rather than glossing.
    """
    tied = [2.0, 2.0, 2.0, 2.0]

    p_value = wilcoxon_signed_rank_p(tied)

    assert p_value == pytest.approx(2 / 16, rel=1e-9)
    assert rank_biserial(tied) == pytest.approx(1.0)
