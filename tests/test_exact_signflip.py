"""Exact sign-flip enumeration for paired binary outcomes (handoff 2026-07-29 §1).

The v1.5 p-values were Monte-Carlo estimates of a null that is exactly enumerable on paired
binary data. Same test, no sampling error. These tests fix the arithmetic, pin the equivalence
to McNemar's exact test, and — per template §A1b — demonstrate the guard FAILING against a
deliberate violation rather than merely asserting it.
"""
from __future__ import annotations

from math import comb

import numpy as np
import pytest

from src.stats.tests import (
    NotEqualMagnitudeDiffs,
    exact_signflip_p,
    paired_permutation_p,
)


def _pair(gains: int, losses: int, ties: int):
    """Build paired binary vectors with an exact discordance pattern."""
    a = [1] * gains + [0] * losses + [1] * ties
    b = [0] * gains + [1] * losses + [1] * ties
    return a, b


# --------------------------------------------------------------------------
# Arithmetic, checked against a hand-computable case
# --------------------------------------------------------------------------

def test_all_discordant_one_direction_is_the_two_sided_binomial_point():
    """5 gains, 0 losses: the only assignments at least as extreme as S=5 are all-+ and all-−."""
    r = exact_signflip_p(*_pair(5, 0, 20))
    assert r["k_discordant"] == 5
    assert r["n_assignments"] == 32
    assert r["n_at_least_as_extreme"] == 2
    assert r["p_exact"] == pytest.approx(2 / 32)


def test_balanced_discordance_gives_p_one():
    """Equal gains and losses: S=0, so every assignment is at least as extreme."""
    r = exact_signflip_p(*_pair(6, 6, 30))
    assert r["p_exact"] == 1.0
    assert (r["n_gains"], r["n_losses"]) == (6, 6)


def test_no_discordant_pairs_is_p_one_not_a_division_by_zero():
    r = exact_signflip_p([1, 0, 1], [1, 0, 1])
    assert r == {"p_exact": 1.0, "k_discordant": 0, "n_gains": 0, "n_losses": 0,
                 "n_assignments": 1, "n_at_least_as_extreme": 1}


def test_matches_mcnemar_exact_closed_form():
    """The literature form: 2 * sum_{j<=min(g,l)} C(K,j) / 2**K, clipped at 1."""
    for gains, losses in [(3, 1), (9, 2), (12, 5), (17, 0), (10, 7)]:
        K = gains + losses
        lo = min(gains, losses)
        expected = min(1.0, 2 * sum(comb(K, j) for j in range(lo + 1)) / 2 ** K)
        got = exact_signflip_p(*_pair(gains, losses, 40))["p_exact"]
        assert got == pytest.approx(expected), (gains, losses, got, expected)


def test_ties_do_not_change_the_p_only_the_denominator_of_the_effect():
    """Concordant pairs contribute nothing to the null — that is why K, not n, is reported."""
    few = exact_signflip_p(*_pair(8, 2, 5))
    many = exact_signflip_p(*_pair(8, 2, 500))
    assert few["p_exact"] == many["p_exact"]
    assert few["k_discordant"] == many["k_discordant"] == 10


def test_direction_does_not_change_a_two_sided_p():
    assert exact_signflip_p(*_pair(9, 2, 40))["p_exact"] == \
           pytest.approx(exact_signflip_p(*_pair(2, 9, 40))["p_exact"])


# --------------------------------------------------------------------------
# It is the SAME test as the pre-registered one, not a substitute
# --------------------------------------------------------------------------

def test_monte_carlo_converges_on_the_exact_value():
    """The pre-registered 10k permutation estimates exactly this quantity.

    Tolerance is the Monte-Carlo SE at these p's (~0.005 at 10k), which is the whole reason
    the exact value is worth having: the estimate's noise is the same size as the distance
    from 0.05 that a significance call turns on.
    """
    for gains, losses in [(9, 2), (12, 5), (20, 8)]:
        a, b = _pair(gains, losses, 100)
        assert paired_permutation_p(a, b, 10000, 1337) == \
               pytest.approx(exact_signflip_p(a, b)["p_exact"], abs=0.02)


# --------------------------------------------------------------------------
# Negative controls — template §A1b: the guard must be SEEN to fail
# --------------------------------------------------------------------------

def test_guard_fails_on_non_binary_paired_data():
    """Graded scores: |diffs| differ, so count-based enumeration would be WRONG, not merely
    approximate. It must refuse rather than return an authoritative-looking number."""
    with pytest.raises(NotEqualMagnitudeDiffs):
        exact_signflip_p([0.9, 0.2, 0.5], [0.1, 0.2, 0.4])


def test_guard_fails_on_binary_data_scored_on_different_scales():
    """A subtler violation: hits recorded as 1 in one arm and 2 in the other."""
    with pytest.raises(NotEqualMagnitudeDiffs):
        exact_signflip_p([2, 0, 2, 0], [0, 0, 1, 0])


def test_guard_passes_the_shape_it_is_meant_to_admit():
    """Complement of the two controls above: real 0/1 hit vectors must NOT raise."""
    rng = np.random.default_rng(7)
    a = rng.integers(0, 2, 176).tolist()
    b = rng.integers(0, 2, 176).tolist()
    assert 0.0 <= exact_signflip_p(a, b)["p_exact"] <= 1.0


def test_reported_k_is_the_discordant_count_not_the_query_count():
    """Regression on the reporting rule itself: a paired binary p is unreadable without K,
    and K is emphatically not n."""
    r = exact_signflip_p(*_pair(9, 8, 159))
    assert r["k_discordant"] == 17 and len(_pair(9, 8, 159)[0]) == 176
