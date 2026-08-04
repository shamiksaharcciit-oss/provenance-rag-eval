"""Sanity checks for the statistics module (plan §8)."""
from __future__ import annotations

from src.stats.tests import (
    bootstrap_ci_mean, holm_correction, paired_bootstrap_diff, paired_permutation_p,
)


def test_bootstrap_ci_brackets_mean():
    vals = [1.0] * 50 + [0.0] * 50  # mean 0.5
    mean, lo, hi = bootstrap_ci_mean(vals, iters=2000, seed=1)
    assert abs(mean - 0.5) < 1e-9
    assert lo < 0.5 < hi


def test_paired_diff_detects_clear_improvement():
    a = [1.0] * 80 + [0.0] * 20  # 0.8
    b = [0.0] * 80 + [0.0] * 20  # 0.0, aligned
    res = paired_bootstrap_diff(a, b, iters=3000, seed=2)
    assert res["mean_diff"] > 0.5
    assert res["significant_ci"] is True
    assert res["ci95"][0] > 0


def test_paired_diff_no_difference():
    a = [1, 0, 1, 0, 1, 0, 1, 0]
    res = paired_bootstrap_diff(a, a, iters=1000, seed=3)
    assert res["mean_diff"] == 0.0
    assert res["significant_ci"] is False


def test_permutation_p_small_for_strong_effect():
    a = [1.0] * 90 + [0.0] * 10
    b = [0.0] * 100
    p = paired_permutation_p(a, b, iters=5000, seed=4)
    assert p < 0.01


def test_permutation_p_large_for_null():
    a = [1, 0] * 50
    p = paired_permutation_p(a, a, iters=1000, seed=5)
    assert p == 1.0


def test_holm_monotone_and_bounds():
    adj = holm_correction([0.01, 0.04, 0.03])
    assert all(0.0 <= x <= 1.0 for x in adj)
    # smallest raw p gets multiplied by m=3
    assert abs(adj[0] - 0.03) < 1e-9
