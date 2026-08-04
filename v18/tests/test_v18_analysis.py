"""PF-14 / G13 — per-answer pairing, and the call arithmetic it has to reproduce.

The tests that matter here are the ones that would fail under the *rejected* readings. It is
easy to write tests that pass for any of (a), (b), (c) — count checks mostly do. So each test
below is chosen to discriminate: pairing correctness against reading (a), order-of-operations
against the medians-then-difference mistake, and the judged-once invariant against (d).
"""
from __future__ import annotations

import pytest

from v18.analysis import (ANSWER_LEVEL, CONTEXT_LEVEL, assemble_query_arm, b1_for_query,
                          b1_per_answer, judge_call_count, median)


# --------------------------------------------------------------- pairing, per answer


def test_b1_per_answer_is_the_fluency_signature_on_one_draw():
    """Judge prefers F768, token-F1 prefers U768, on the SAME two answers -> +2."""
    assert b1_per_answer(judge_f=0.9, judge_u=0.4, f1_f=0.3, f1_u=0.7) == 2


def test_b1_per_answer_is_zero_when_both_instruments_agree():
    assert b1_per_answer(0.9, 0.4, 0.9, 0.4) == 0
    assert b1_per_answer(0.4, 0.9, 0.4, 0.9) == 0


def test_b1_for_query_takes_the_median_of_differences_not_the_difference_of_medians():
    """The order is load-bearing (PF-14).

    Constructed so the two orders genuinely disagree — with symmetric values they coincide,
    which makes most naive test data useless here.

        rep 0: judge +1, f1 +1  ->  0
        rep 1: judge -1, f1 +1  -> -2
        rep 2: judge -1, f1 -1  ->  0      median of differences = 0

    Differencing the medians instead gives (-1) - (+1) = -2, because each median is drawn from
    whichever rep happens to sit in the middle *for that instrument* — the cross-draw
    comparison the ruling removed.
    """
    judge_f = [0.9, 0.2, 0.2]
    judge_u = [0.1, 0.8, 0.8]
    f1_f = [0.9, 0.9, 0.1]
    f1_u = [0.1, 0.1, 0.9]
    assert b1_for_query(judge_f, judge_u, f1_f, f1_u) == 0

    # the difference-of-medians route would give a different answer here
    from v18.instruments import preference
    wrong = preference(median(judge_f), median(judge_u)) - preference(median(f1_f), median(f1_u))
    assert wrong != 0, "test is not discriminating between the two orders"


def test_b1_for_query_pairs_by_index():
    """Reading (a) — judge one answer, F1 across three — must not reproduce this."""
    # rep 0: judge prefers F, F1 prefers U   -> +2
    # rep 1: judge prefers U, F1 prefers F   -> -2
    # rep 2: both tie                        ->  0
    out = b1_for_query([0.9, 0.4, 0.5], [0.4, 0.9, 0.5],
                       [0.3, 0.9, 0.5], [0.7, 0.4, 0.5])
    assert out == 0, "median of [+2, -2, 0]"


def test_b1_for_query_rejects_ragged_reps():
    with pytest.raises(AssertionError, match="rep pairing broken"):
        b1_for_query([0.9, 0.5], [0.4], [0.3, 0.5], [0.7, 0.5])


def test_b1_for_query_handles_the_single_rep_case():
    """Every arm-track outside the targeted pair has one answer; the same code path serves it."""
    assert b1_for_query([0.9], [0.4], [0.3], [0.7]) == 2


# ------------------------------------------------------- which metrics repeat, and why


def test_only_answer_level_metrics_repeat():
    assert ANSWER_LEVEL == {"faithfulness", "answer_relevancy", "answer_correctness"}
    assert CONTEXT_LEVEL == {"context_precision", "context_recall"}
    assert not (ANSWER_LEVEL & CONTEXT_LEVEL)


def test_assembly_medians_answer_level_and_leaves_context_single():
    by_rep = {
        0: {"faithfulness": 1.0, "answer_relevancy": 0.6, "answer_correctness": 0.4},
        1: {"faithfulness": 0.5, "answer_relevancy": 0.9, "answer_correctness": 0.8},
        2: {"faithfulness": 0.0, "answer_relevancy": 0.3, "answer_correctness": 0.6},
    }
    ctx = {"context_precision": 0.8, "context_recall": 0.5}
    out = assemble_query_arm(by_rep, ctx)
    assert out["faithfulness"] == 0.5                     # median of 1.0, 0.5, 0.0
    assert out["answer_relevancy"] == 0.6
    assert out["answer_correctness"] == 0.6
    assert out["context_precision"] == 0.8                # untouched, single judgement
    assert out["_n_answers_judged"] == 3
    assert out["context_composite"] == pytest.approx(0.65)
    assert len(out["answer_composite_by_rep"]) == 3


def test_assembly_works_for_a_single_judged_answer():
    out = assemble_query_arm({0: {"faithfulness": 1.0, "answer_relevancy": 0.5,
                                  "answer_correctness": 0.5}},
                             {"context_precision": 1.0, "context_recall": 1.0})
    assert out["_n_answers_judged"] == 1
    assert out["faithfulness"] == 1.0


# --------------------------------------------------- the call arithmetic (G13 §1, §5)


def _reps_for(track, arm):
    return 3 if (track == "A" and arm in ("F768", "U768")) else 1


def test_judge_call_total_matches_the_frozen_projection():
    """Every answer judged exactly once must still cost exactly 15,960 calls."""
    assert judge_call_count({"A": 176, "B": 150}, _reps_for) == 15_960


def test_generation_plus_judging_equals_the_frozen_ceiling_projection():
    from v18.ledger import FROZEN_PROJECTION
    assert 1_682 + judge_call_count({"A": 176, "B": 150}, _reps_for) == FROZEN_PROJECTION


def test_reading_d_would_breach_the_ceiling():
    """The rejected reading, priced — 3 answers x 3 judgements."""
    def reps_d(track, arm):
        return 9 if (track == "A" and arm in ("F768", "U768")) else 1
    from v18.ledger import CALL_CEILING
    assert 1_682 + judge_call_count({"A": 176, "B": 150}, reps_d) > CALL_CEILING


def test_context_calls_do_not_scale_with_reps():
    """If they did, the totals would not reconcile — and tripling them buys nothing."""
    single = judge_call_count({"A": 176}, lambda t, a: 1)
    tripled = judge_call_count({"A": 176}, lambda t, a: 3)
    # 3 arms x 176 queries x 6 context calls stays constant; only the 6 answer-level scale
    assert tripled - single == 3 * 176 * 6 * 2
