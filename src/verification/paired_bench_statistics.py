"""Turning paired bench trials into a verdict, so nobody does statistics by hand.

Routed per `applied-statistics:experiment-statistics`: two groups, paired,
continuous. The nonparametric branch is taken **by design**, not by a normality
test — at ten pairs such a test has almost no power, so branching on it would be
theatre dressed as rigour. Wilcoxon signed-rank with an exact null (enumerated,
not approximated, at these sizes), the matched-pairs rank-biserial correlation as
the ordinal effect size that branch asks for, and a bootstrap interval for the
magnitude.

Four deliverables are enforced rather than offered, because a bare p is not an
output: magnitude with its uncertainty, multiplicity correction across the family
of scenarios, an equivalence test when nothing is found, and an explicit vacuous
marker when the population is short. The smallest effect worth caring about has
no default here and never will — it is a decision about slip force, not a library
constant.

Pure standard library: this project carries no scipy, and adding one for four
functions would cost more than it saves.
"""

from __future__ import annotations

import itertools
import math
import random
import statistics
from dataclasses import dataclass

#: Two-sided, and not treated as a cliff. Reported alongside the effect size and
#: its interval so the reader sees magnitude before they see a verdict.
ALPHA = 0.05

#: Enough for a stable interval at these sample sizes without being slow.
BOOTSTRAP_ITERATIONS = 4000

#: Above this many pairs the exact enumeration stops being cheap and the normal
#: approximation is accurate anyway.
EXACT_LIMIT = 20


@dataclass(frozen=True, slots=True)
class ScenarioVerdict:
    """One scenario's answer, with everything needed to disbelieve it."""

    scenario: str
    n: int
    vacuous: bool
    median_difference: float
    confidence_interval: tuple[float, float]
    effect_size: float
    p_value: float
    significant: bool
    equivalent: bool
    summary: str


def paired_differences(pairs: list[tuple[float, float]]) -> list[float]:
    """Second minus first, so a positive difference means the treatment helped."""
    return [after - before for before, after in pairs]


def wilcoxon_signed_rank_p(differences: list[float]) -> float:
    """Two-sided exact p for the signed-rank statistic.

    Zero differences are dropped, which is what the test requires and also what
    honesty requires: a pair that did not move carries no sign and must not be
    counted as evidence in either direction.
    """
    nonzero = [value for value in differences if value != 0.0]
    count = len(nonzero)
    if count == 0:
        return 1.0

    ranks = _average_ranks([abs(value) for value in nonzero])
    positive: float = math.fsum(
        rank for rank, value in zip(ranks, nonzero, strict=True) if value > 0
    )
    total: float = math.fsum(ranks)
    observed: float = min(positive, total - positive)

    if count > EXACT_LIMIT:
        return _normal_approximation_p(observed, count)

    # Every assignment of signs to the observed ranks is equally likely under the
    # null, so the exact p is just how often the statistic gets this extreme.
    extreme = 0
    for signs in itertools.product((0.0, 1.0), repeat=count):
        candidate = math.fsum(rank * sign for rank, sign in zip(ranks, signs, strict=True))
        if min(candidate, total - candidate) <= observed + 1e-12:
            extreme += 1
    return float(extreme) / float(2**count)


def rank_biserial(differences: list[float]) -> float:
    """Matched-pairs rank-biserial correlation: -1 to +1, zero when signs cancel."""
    nonzero = [value for value in differences if value != 0.0]
    if not nonzero:
        return 0.0
    ranks = _average_ranks([abs(value) for value in nonzero])
    total = math.fsum(ranks)
    positive = math.fsum(rank for rank, value in zip(ranks, nonzero, strict=True) if value > 0)
    return (2.0 * positive - total) / total


def bootstrap_median_ci(
    values: list[float],
    *,
    seed: int,
    confidence: float = 0.95,
    iterations: int = BOOTSTRAP_ITERATIONS,
) -> tuple[float, float]:
    """Percentile interval for the median. Seeded, because a verdict that changes
    between runs is not a verdict."""
    if not values:
        raise ValueError("an interval needs observations")
    rng = random.Random(seed)
    size = len(values)
    medians = sorted(statistics.median(rng.choices(values, k=size)) for _ in range(iterations))
    tail = (1.0 - confidence) / 2.0
    low = medians[int(tail * iterations)]
    high = medians[min(iterations - 1, int((1.0 - tail) * iterations))]
    return (low, high)


def holm_adjusted(p_values: list[float]) -> list[float]:
    """Holm step-down, in the caller's order. Family-wise, because the scenarios
    are a small confirmatory family rather than a wide exploratory sweep."""
    count = len(p_values)
    ordered = sorted(range(count), key=lambda index: p_values[index])
    adjusted = [0.0] * count
    running = 0.0
    for position, index in enumerate(ordered):
        running = max(running, min(1.0, (count - position) * p_values[index]))
        adjusted[index] = running
    return adjusted


def tost_equivalent(differences: list[float], *, sesoi: float) -> bool:
    """Two one-sided tests against a smallest effect worth caring about.

    The point is to stop "not significant" being read as "no difference". A true
    verdict means the interval sits inside the bounds; false means inconclusive,
    which is not the same as different and must not be reported as either.
    """
    if sesoi <= 0.0:
        raise ValueError("TOST needs a positive smallest effect worth caring about")
    if len(differences) < 2:
        return False
    low, high = bootstrap_median_ci(differences, seed=0, confidence=0.90)
    return -sesoi < low and high < sesoi


def assess_scenario(
    scenario: str,
    pairs: list[tuple[float, float]],
    *,
    planned_pairs: int,
    sesoi: float,
    seed: int = 0,
) -> ScenarioVerdict:
    """The whole verdict for one comparison, population checked first."""
    if sesoi <= 0.0:
        raise ValueError("every scenario needs a positive smallest effect worth caring about")

    count = len(pairs)
    if count < planned_pairs:
        return ScenarioVerdict(
            scenario=scenario,
            n=count,
            vacuous=True,
            median_difference=0.0,
            confidence_interval=(0.0, 0.0),
            effect_size=0.0,
            p_value=1.0,
            significant=False,
            equivalent=False,
            summary=(
                f"{scenario}: vacuous — n={count} of {planned_pairs} planned pairs. "
                "Never mixed into a pass."
            ),
        )

    differences = paired_differences(pairs)
    median = statistics.median(differences)
    interval = bootstrap_median_ci(differences, seed=seed)
    effect = rank_biserial(differences)
    p_value = wilcoxon_signed_rank_p(differences)
    significant = p_value < ALPHA
    equivalent = False if significant else tost_equivalent(differences, sesoi=sesoi)

    if significant:
        verdict = "difference"
    elif equivalent:
        verdict = "practically equivalent"
    else:
        verdict = "inconclusive, not 'no difference'"

    return ScenarioVerdict(
        scenario=scenario,
        n=count,
        vacuous=False,
        median_difference=median,
        confidence_interval=interval,
        effect_size=effect,
        p_value=p_value,
        significant=significant,
        equivalent=equivalent,
        summary=(
            f"{scenario}: median {median:+.2f} N, 95% CI [{interval[0]:+.2f}, "
            f"{interval[1]:+.2f}], rank-biserial {effect:+.2f}, p={p_value:.4f}, "
            f"n={count} — {verdict}"
        ),
    )


def _average_ranks(magnitudes: list[float]) -> list[float]:
    """Ranks with ties averaged, because tied magnitudes are common on a bench."""
    order = sorted(range(len(magnitudes)), key=lambda index: magnitudes[index])
    ranks = [0.0] * len(magnitudes)
    position = 0
    while position < len(order):
        stop = position
        while stop + 1 < len(order) and magnitudes[order[stop + 1]] == magnitudes[order[position]]:
            stop += 1
        shared = (position + stop) / 2.0 + 1.0
        for index in order[position : stop + 1]:
            ranks[index] = shared
        position = stop + 1
    return ranks


def _normal_approximation_p(observed: float, count: int) -> float:
    mean = count * (count + 1) / 4.0
    deviation = math.sqrt(count * (count + 1) * (2 * count + 1) / 24.0)
    if deviation == 0.0:
        return 1.0
    z = (observed - mean) / deviation
    return max(0.0, min(1.0, 2.0 * _standard_normal_cdf(z)))


def _standard_normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
