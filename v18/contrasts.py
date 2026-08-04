"""v1.8 §4 — the arm contrasts, and the single tested family `F_BIAS`.

**B2 was deleted at Gate 0 (PF-7), and the reason is worth keeping here.** As drafted it was
`(F768 - U256) - (F768 - U768)` on the per-query context composite, which telescopes exactly to
`U768 - U256` — the F768 terms cancel. A quantity containing no F768 term cannot support any
claim about what fraction of F768's apparent gain is size, which is what PD-2 was written to
predict. Rather than bolt on a ratio with a small, noisy denominator, the plan now reports the
three context contrasts as absolute values with discordant counts and lets the reader subtract:
`context_contrast_table` below. `F_BIAS` is B1 alone.

**B1 has a sign convention that a synthetic case must be able to fail.** `b1_per_query` is the
judge's preference minus token-F1's preference on the identical pair, so it lives on
{-2, -1, 0, +1, +2}. Positive mean = the judge favours the formatter beyond what objective
scoring supports (§4). `tests/test_v18_contrasts.py` builds a case where the two instruments
disagree by construction and pins the sign; that test exists because a silently flipped
comparison would turn the fluency-bias finding into its own refutation and nothing else in the
pipeline would notice.

Everything outside `F_BIAS` is descriptive (§4): values and counts favouring each side, no test,
no mechanism prose. `descriptive_contrast` deliberately returns no p-value.
"""
from __future__ import annotations

from src.pw1.interpret import holm_within_family
from src.stats.tests import paired_bootstrap_diff, paired_permutation_p
from v18.instruments import preference

#: §4 — the decision-bearing family, exactly one member, Track A [PF-7]. With one member Holm
#: reduces to the plain p-value; `holm_family` reports it labelled as such rather than dressed
#: as a correction.
F_BIAS = ("B1",)

#: §4 — frozen statistical parameters.
ITERS = 10000
SEED = 1337
CI = 0.95


def b1_per_query(judge_f: list[float], judge_u: list[float],
                 f1_f: list[float], f1_u: list[float]) -> list[int]:
    """B1 (fluency excess), paired per query.

    `judge_*` are the I1 *answer-level* composites for `F768` and `U768`; `f1_*` are the I2
    token-F1 scores for the same generated answers. Per query:

        b1 = preference(judge_F, judge_U) - preference(f1_F, f1_U)

    Positive mean => the judge favours the formatter beyond what objective scoring supports.
    """
    n = len(judge_f)
    assert len(judge_u) == len(f1_f) == len(f1_u) == n, (
        f"pairing broken: {len(judge_f)}, {len(judge_u)}, {len(f1_f)}, {len(f1_u)}")
    return [preference(judge_f[i], judge_u[i]) - preference(f1_f[i], f1_u[i]) for i in range(n)]


def context_contrast_table(ctx_f768: list[float], ctx_u768: list[float],
                           ctx_u256: list[float]) -> dict:
    """The absolute-numbers pattern that replaced B2 [PF-7].

    Three contrasts on the context-metric composite, each a value with its discordant counts,
    descriptive and untested. The reader does the subtraction — which is the point: no ratio is
    formed here, so no small denominator can destabilise anything.

    `PD-2` is scored off this table by comparing two point values (`size` vs `residual`), by
    direction only. `pd2_direction_holds` states that comparison once rather than leaving it to
    prose in the results document.
    """
    n = len(ctx_f768)
    assert len(ctx_u768) == len(ctx_u256) == n, (
        f"pairing broken: {len(ctx_f768)}, {len(ctx_u768)}, {len(ctx_u256)}")
    total = descriptive_contrast(ctx_f768, ctx_u256)
    size = descriptive_contrast(ctx_u768, ctx_u256)
    residual = descriptive_contrast(ctx_f768, ctx_u768)
    return {
        "total_F768_minus_U256": total,
        "size_U768_minus_U256": size,
        "residual_F768_minus_U768": residual,
        "pd2_direction_holds": size["mean_diff"] >= residual["mean_diff"],
        "_note": ("descriptive; no test and no ratio (§4, PF-7). PD-2 is the direction "
                  "comparison size >= residual, scored on point values."),
    }


def tested_contrast(values: list[float]) -> dict:
    """A `F_BIAS` member: paired bootstrap CI + permutation p against zero.

    The member is already a per-query difference, so the paired machinery is applied against a
    zero vector — the same procedure v1.6 and v1.7 used, not a second one (A5b).
    """
    zeros = [0.0] * len(values)
    d = paired_bootstrap_diff(values, zeros, ITERS, SEED, CI)
    favour_pos = sum(1 for v in values if v > 0)
    favour_neg = sum(1 for v in values if v < 0)
    return {"n": len(values),
            "mean": round(d["mean_diff"], 6),
            "ci95": [round(x, 6) for x in d["ci95"]],
            "p_permutation": round(paired_permutation_p(values, zeros, ITERS, SEED), 6),
            "discordant": {"favour_positive": favour_pos, "favour_negative": favour_neg,
                           "ties": len(values) - favour_pos - favour_neg,
                           "informative": favour_pos + favour_neg,
                           "_note": "descriptive only; no test is computed from these (A5b)"}}


def descriptive_contrast(a: list[float], b: list[float]) -> dict:
    """A non-family contrast: value and counts favouring each side. No test, by design (§4)."""
    n = len(a)
    assert len(b) == n, f"pairing broken: {len(a)}, {len(b)}"
    diffs = [a[i] - b[i] for i in range(n)]
    favour_a = sum(1 for d in diffs if d > 0)
    favour_b = sum(1 for d in diffs if d < 0)
    return {"n": n,
            "mean_diff": round(sum(diffs) / n, 6) if n else 0.0,
            "n01_favour_first": favour_a, "n10_favour_second": favour_b,
            "ties": n - favour_a - favour_b,
            "informative": favour_a + favour_b,
            "_note": "descriptive only; no test is computed on this contrast (§4)"}


def holm_family(p_by_member: dict[str, float]) -> dict:
    """Holm within `F_BIAS` only, in the declared member order.

    `F_BIAS` now has one member, so Holm is the identity and `p_holm == p_raw`. That is stated
    in the returned record rather than left for a reader to infer from two equal numbers — a
    single-member "correction" reported without comment reads as a correction that was applied,
    which would overstate what the procedure did.
    """
    missing = set(F_BIAS) - set(p_by_member)
    assert not missing, f"F_BIAS is exactly {F_BIAS}; missing {sorted(missing)}"
    extra = set(p_by_member) - set(F_BIAS)
    assert not extra, f"F_BIAS is exactly {F_BIAS}; will not correct over {sorted(extra)}"
    raw = [p_by_member[m] for m in F_BIAS]
    adjusted = holm_within_family(raw)
    out = {"members": list(F_BIAS),
           "p_raw": dict(zip(F_BIAS, raw)),
           "p_holm": dict(zip(F_BIAS, adjusted))}
    if len(F_BIAS) == 1:
        out["_note"] = ("single-member family: Holm is the identity and p_holm is the plain "
                        "p-value, not a corrected one")
        assert adjusted[0] == raw[0], (
            f"single-member Holm must be the identity: {adjusted[0]} != {raw[0]}")
    return out
