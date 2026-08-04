"""v1.7 E1 — budget selection and the decomposition (plan §2.2, §2.3).

`units_at_budget` and `contrast` are v1.6's procedures moved out of `scripts/segment_size_sweep.py`
into a module so that v17 executes the same rule under test rather than re-deriving it in a second
place. The semantics are unchanged and `tests/test_v17_e1.py` pins them:

  * take units in rank order, accumulate tokens, INCLUDE the unit that crosses B, stop;
  * a difference must lie on the k/n lattice (R2, a wiring check — per-query scores are binary,
    so an off-lattice difference is a pairing or denominator bug, not a small effect);
  * discordant n01/n10 recorded beside every difference, descriptively, never tested on (R3/A5b).

The decomposition telescopes by construction:

    D_int_size + D_int_ws + D_int_seam + D_int_edit
      = (U768-U256) + (U768ws-U768) + (S768-U768ws) + (F768-S768)
      = F768 - U256 = D_int_total

`assert_decomposition` checks that on INTEGER numerators, where it must hold exactly.
"""
from __future__ import annotations

from src.stats.tests import paired_bootstrap_diff, paired_permutation_p


def units_at_budget(ranked_ids: list[str], tokens: dict[str, int], budget: int) -> list[str]:
    """Units taken in rank order up to `budget`, INCLUDING the one that crosses it.

    Returns the prefix; the caller checks it against the retrieval depth. Raises if the ranked
    list is too short to reach the budget, because a truncated list understates the small-unit
    arms and flatters the large-unit ones (v1.6's R4).
    """
    acc, k = 0, 0
    while k < len(ranked_ids) and acc < budget:
        acc += tokens[ranked_ids[k]]
        k += 1
    if acc < budget:
        raise RuntimeError(
            f"R4: budget {budget} not reached — {acc} tokens in {len(ranked_ids)} units. The "
            f"ranked list truncated the metric; do NOT raise the pool, that changes retrieval "
            f"for every arm.")
    return ranked_ids[:k]


def contrast(a: list[int], b: list[int], n: int, iters: int, seed: int) -> dict:
    """R1 + R2 + R3 for one paired binary contrast. v1.6's procedure, unchanged."""
    assert len(a) == len(b) == n, f"pairing broken: {len(a)}, {len(b)}, n={n}"
    num = sum(a) - sum(b)
    d = paired_bootstrap_diff(a, b, iters, seed, 0.95)
    delta = d["mean_diff"]
    assert abs(delta - num / n) < 1e-9, (
        f"R2: delta {delta} is off the k/{n} lattice (numerator {num})")
    n01 = sum(1 for x, y in zip(a, b) if x and not y)
    n10 = sum(1 for x, y in zip(a, b) if y and not x)
    return {"numerator": num, "denominator": n, "delta": round(delta, 6),
            "delta_exact": f"{num}/{n}",
            "ci95": [round(x, 6) for x in d["ci95"]],
            "p_permutation": round(paired_permutation_p(a, b, iters, seed), 6),
            "discordant": {"n01": n01, "n10": n10, "informative": n01 + n10,
                           "_note": "descriptive only; no test is computed from these (A5b)"}}


def assert_decomposition(dec: dict, prefix: str = "D_int") -> int:
    """The four inner differences must sum to the total, exactly, on integer numerators."""
    inner = sum(dec[f"{prefix}_{k}"]["numerator"] for k in ("size", "ws", "seam", "edit"))
    total = dec[f"{prefix}_total"]["numerator"]
    assert inner == total, f"decomposition identity: inner {inner} != total {total}"
    return total
