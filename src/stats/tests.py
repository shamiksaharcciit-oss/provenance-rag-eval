"""Statistics (plan §8).

Paired design (identical queries across conditions):
  * 95% CI on each Recall@k via paired bootstrap (resample queries, >=10k iters, seed).
  * pairwise significance via a paired permutation test (sign-flip of per-query diffs).
  * Holm correction across the reported pairwise comparisons.
A result is "real" only if its CI excludes 0 (§8, §13).
"""
from __future__ import annotations

import numpy as np


def bootstrap_ci_mean(values: list[float], iters: int, seed: int, ci: float = 0.95
                      ) -> tuple[float, float, float]:
    """Mean and (lo, hi) percentile CI of the mean via bootstrap resampling."""
    arr = np.asarray(values, dtype=np.float64)
    n = len(arr)
    if n == 0:
        return 0.0, 0.0, 0.0
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(iters, n))
    means = arr[idx].mean(axis=1)
    alpha = (1.0 - ci) / 2.0
    lo, hi = np.percentile(means, [100 * alpha, 100 * (1 - alpha)])
    return float(arr.mean()), float(lo), float(hi)


def paired_bootstrap_diff(a: list[float], b: list[float], iters: int, seed: int,
                          ci: float = 0.95) -> dict:
    """Paired bootstrap of the mean difference (a - b) over the SAME queries."""
    x = np.asarray(a, dtype=np.float64)
    y = np.asarray(b, dtype=np.float64)
    assert len(x) == len(y), "paired stats require equal-length, aligned vectors"
    n = len(x)
    d = x - y
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(iters, n))
    diffs = d[idx].mean(axis=1)
    alpha = (1.0 - ci) / 2.0
    lo, hi = np.percentile(diffs, [100 * alpha, 100 * (1 - alpha)])
    return {"mean_diff": float(d.mean()), "ci95": [float(lo), float(hi)],
            "significant_ci": bool(lo > 0 or hi < 0)}


def paired_permutation_p(a: list[float], b: list[float], iters: int, seed: int) -> float:
    """Two-sided paired permutation test via random sign flips of per-query diffs."""
    x = np.asarray(a, dtype=np.float64)
    y = np.asarray(b, dtype=np.float64)
    d = x - y
    n = len(d)
    obs = abs(d.mean())
    if n == 0 or np.allclose(d, 0):
        return 1.0
    rng = np.random.default_rng(seed)
    signs = rng.integers(0, 2, size=(iters, n)) * 2 - 1  # +/-1
    perm_means = np.abs((signs * d).mean(axis=1))
    # +1 smoothing to avoid p=0
    return float((np.sum(perm_means >= obs - 1e-12) + 1) / (iters + 1))


class NotEqualMagnitudeDiffs(AssertionError):
    """Raised when exact sign-flip enumeration is applied to non-binary paired data.

    Enumeration collapses 2**K sign assignments to K+1 counts. That collapse is valid only
    when every non-zero difference has the SAME magnitude — which is exactly the paired
    binary (hit/miss) case. With unequal magnitudes the flip distribution depends on which
    pairs flipped, not merely how many, and the count-based enumeration is wrong rather than
    approximate. Refuse rather than return a number that looks exact.
    """


def exact_signflip_p(a: list[float], b: list[float]) -> dict:
    """Exact two-sided sign-flip permutation p for PAIRED BINARY outcomes.

    This is the same null as `paired_permutation_p` — flip the sign of each per-query
    difference independently — evaluated by complete enumeration instead of Monte Carlo, so
    it carries no sampling error. On paired binary data it coincides with McNemar's exact
    test: only the K discordant pairs contribute, and enumeration is over 2**K.

    Returns p, K (the discordant count — the sample size the test actually runs on, without
    which a paired binary p cannot be judged), and the gain/loss split.
    """
    from math import comb

    d = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    nz = d[d != 0]
    mags = np.abs(nz)
    if nz.size and not np.allclose(mags, mags[0]):
        raise NotEqualMagnitudeDiffs(
            f"non-zero |diffs| are not identical (min={mags.min()}, max={mags.max()}); "
            "exact enumeration is only valid for paired binary outcomes"
        )
    unit = nz / mags[0] if nz.size else nz  # +/-1
    K = int(unit.size)
    if K == 0:
        return {"p_exact": 1.0, "k_discordant": 0, "n_gains": 0, "n_losses": 0,
                "n_assignments": 1, "n_at_least_as_extreme": 1}
    S = int(unit.sum())
    extreme = sum(comb(K, j) for j in range(K + 1) if abs(2 * j - K) >= abs(S) - 1e-9)
    return {"p_exact": extreme / 2 ** K, "k_discordant": K,
            "n_gains": int((d > 0).sum()), "n_losses": int((d < 0).sum()),
            "n_assignments": 2 ** K, "n_at_least_as_extreme": extreme}


def holm_correction(pvals: list[float]) -> list[float]:
    """Holm-Bonferroni adjusted p-values, preserving input order."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        val = (m - rank) * pvals[i]
        running = max(running, val)
        adj[i] = min(1.0, running)
    return adj
