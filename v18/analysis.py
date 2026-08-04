"""v1.8 PF-14 — per-answer pairing for B1, and metric assembly from judge rows.

G13 asked which of the three generated answers the judge scores for the targeted pair, and what
the repeats measure. Ruled: **each answer is judged exactly once**, and B1 is computed *per
answer* before aggregation.

The reason that matters, from the ruling: B1 is a **between-instrument** comparison. Its whole
meaning is "two instruments looked at the same evidence and preferred differently." Score the
judge on one answer while token-F1 spans three, and the contrast stops measuring instrument bias
and starts measuring generation-draw variance instead. Pairing both instruments on the same draw
removes generation variance from the difference entirely, leaving judge noise, which the median
then dampens.

Reps are paired by index — `F768` rep r against `U768` rep r. The draws are independent, so any
fixed pairing is exchangeable; index pairing is simply the one with no discretion in it.

**Declared narrowing (ruling §3).** PF-3 said the judge repeats measure judge variance. Under
per-answer pairing each judged answer is a fresh generation sample *and* a fresh judgement
sample, so the repeats cover the joint draw and the two sources are **not separately
identified**. Separating them costs reading (d)'s budget and serves no frozen prediction. This
narrowing is stated in the results document, not papered over.
"""
from __future__ import annotations

import statistics

from v18.instruments import (ANSWER_METRICS, CONTEXT_METRICS, answer_composite,
                             context_composite, preference)

#: The metrics whose value depends on the generated answer. Only these are repeated: context
#: precision and recall read the retrieved contexts, which are byte-identical across reps, so
#: tripling them would buy nothing (G13 §1).
ANSWER_LEVEL = set(ANSWER_METRICS)
CONTEXT_LEVEL = set(CONTEXT_METRICS)


def median(values: list[float]) -> float:
    """Plain median. Odd counts everywhere here, so no interpolation question arises."""
    assert values, "median of an empty sample"
    return statistics.median(values)


def b1_per_answer(judge_f: float, judge_u: float, f1_f: float, f1_u: float) -> int:
    """B1 on ONE paired answer draw: judge preference minus token-F1 preference.

    Both instruments see the same two answers — that is the property the whole measurement
    rests on, and the reason the arguments are named per-rep rather than per-query.
    """
    return preference(judge_f, judge_u) - preference(f1_f, f1_u)


def b1_for_query(judge_f: list[float], judge_u: list[float],
                 f1_f: list[float], f1_u: list[float]) -> float:
    """Per-query B1: the **median of the per-answer differences** (PF-14).

    Note the order: difference first, median second. Taking medians of each instrument and then
    differencing would reintroduce the cross-draw comparison the ruling removed — the two
    medians could come from different answers.
    """
    n = len(judge_f)
    assert len(judge_u) == len(f1_f) == len(f1_u) == n, (
        f"rep pairing broken: {len(judge_f)}, {len(judge_u)}, {len(f1_f)}, {len(f1_u)}")
    return median([b1_per_answer(judge_f[r], judge_u[r], f1_f[r], f1_u[r]) for r in range(n)])


def per_arm_answer_metric(values_by_rep: list[float]) -> float:
    """Descriptive I1 answer-level value for one (query, arm): median over judged answers."""
    return median(values_by_rep)


def assemble_query_arm(metric_values_by_rep: dict[int, dict[str, float]],
                       context_values: dict[str, float]) -> dict:
    """Collapse one (query, arm)'s judged answers into the reported I1 record.

    `metric_values_by_rep` holds the answer-level metrics per rep; `context_values` holds the
    context-level metrics, which are single-judgement by construction.
    """
    reps = sorted(metric_values_by_rep)
    out = dict(context_values)
    for m in ANSWER_METRICS:
        out[m] = per_arm_answer_metric([metric_values_by_rep[r][m] for r in reps])
    out["_n_answers_judged"] = len(reps)
    out["context_composite"] = context_composite(context_values)
    out["answer_composite_by_rep"] = {
        r: answer_composite(metric_values_by_rep[r]) for r in reps}
    out["answer_composite"] = median(list(out["answer_composite_by_rep"].values()))
    return out


def judge_call_count(n_by_track: dict[str, int], reps_for) -> int:
    """The judge-call total implied by the design, derived rather than asserted.

    Context-level calls are single-judgement; answer-level calls run once per judged answer.
    Must equal the frozen 15,960 (17,642 projection minus 1,682 generation).
    """
    from v18.judge_prompts import CALLS_PER_QUERY_ARM
    ctx = sum(CALLS_PER_QUERY_ARM[m] for m in CONTEXT_METRICS)
    ans = sum(CALLS_PER_QUERY_ARM[m] for m in ANSWER_METRICS)
    total = 0
    for track, n in n_by_track.items():
        for arm in ("U256", "U768", "F768"):
            total += n * (ctx + ans * reps_for(track, arm))
    return total
