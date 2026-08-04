"""Gate 0 — the E1 metrics (plan §5, freeze checklist).

The four required cases are `test_multi_span_*`, `test_straddling_span_scores_single_zero`,
`test_budget_crossing_unit_is_included` and `test_decomposition_sums_on_the_lattice`.

Every test here states a BEHAVIOUR of the metric. None asserts a fact about the corpus: the
v1.6 empty-segment ruling split those apart, because a corpus fact asserted under a behavioural
name fails for the wrong reason when the corpus changes.
"""
from __future__ import annotations

import pytest

from src.datasets.base import GoldSpan
from src.v17.e1 import assert_decomposition, contrast, units_at_budget
from src.v17.integrity import (count_degenerate_spans, feasible_single, integrity_full,
                               integrity_single, score_query)

D = "doc1"


def g(start, end, doc=D):
    return GoldSpan(doc_id=doc, start_char=start, end_char=end)


def u(doc, *ranges):
    return (doc, [tuple(r) for r in ranges])


# ------------------------------------------------------------------ single vs full

def test_one_unit_covering_the_span_scores_both():
    units = [u(D, (0, 100))]
    assert integrity_single(units, [g(10, 50)]) == 1
    assert integrity_full(units, [g(10, 50)]) == 1


def test_straddling_span_scores_single_zero_and_full_one():
    """THE required case: a span split across two units is whole in the union, not in any unit."""
    units = [u(D, (0, 50)), u(D, (50, 100))]
    gold = [g(40, 60)]
    assert integrity_single(units, gold) == 0
    assert integrity_full(units, gold) == 1


def test_partial_coverage_scores_both_zero():
    units = [u(D, (0, 45))]
    gold = [g(40, 60)]
    assert integrity_single(units, gold) == 0
    assert integrity_full(units, gold) == 0


def test_single_implies_full_is_asserted():
    out = score_query([u(D, (0, 100))], [g(10, 50)])
    assert out == {"integrity_single": 1, "integrity_full": 1}


# ------------------------------------------------------------------ multi-span gold

def test_multi_span_needs_one_unit_covering_all_spans():
    """One unit per span is NOT enough — §2.2 requires a single unit covering every span."""
    split = [u(D, (0, 50)), u(D, (200, 260))]
    gold = [g(10, 40), g(210, 250)]
    assert integrity_single(split, gold) == 0
    assert integrity_full(split, gold) == 1

    whole = [u(D, (0, 300))]
    assert integrity_single(whole, gold) == 1


def test_multi_span_with_one_span_uncovered_fails_full():
    units = [u(D, (0, 50))]
    gold = [g(10, 40), g(210, 250)]
    assert integrity_full(units, gold) == 0
    assert integrity_single(units, gold) == 0


def test_multi_span_across_documents_cannot_satisfy_single():
    """A unit belongs to one document, so cross-document gold is unsatisfiable by construction."""
    units = [u("docA", (0, 500)), u("docB", (0, 500))]
    gold = [g(10, 40, "docA"), g(10, 40, "docB")]
    assert integrity_single(units, gold) == 0
    assert integrity_full(units, gold) == 1


def test_ranges_in_a_foreign_document_never_cover():
    units = [u("docB", (0, 500))]
    assert integrity_full(units, [g(10, 40, "docA")]) == 0
    assert integrity_single(units, [g(10, 40, "docA")]) == 0


# ------------------------------------------------------------------ coverage arithmetic

def test_disjoint_ranges_in_one_unit_union_before_counting():
    """Two ranges of one unit jointly covering a span is coverage, not two partial misses."""
    units = [u(D, (0, 30), (30, 60))]
    assert integrity_single(units, [g(10, 50)]) == 1


def test_overlapping_ranges_do_not_double_count():
    """Overlapping ranges must not inflate coverage past the span they actually cover."""
    units = [u(D, (0, 30), (0, 30), (0, 30))]
    assert integrity_single(units, [g(0, 60)]) == 0


def test_degenerate_span_is_vacuously_covered_and_counted():
    units = [u(D, (500, 600))]
    assert integrity_single(units, [g(10, 10)]) == 1
    assert count_degenerate_spans([g(10, 10), g(0, 5)]) == 1


def test_feasibility_uses_the_inventory_not_the_retrieved_set():
    retrieved = [u(D, (0, 50))]
    inventory = [u(D, (0, 50)), u(D, (0, 300))]
    gold = [g(10, 250)]
    assert integrity_single(retrieved, gold) == 0
    assert feasible_single(inventory, gold) == 1


def test_empty_retrieved_set_scores_zero():
    assert integrity_single([], [g(10, 50)]) == 0
    assert integrity_full([], [g(10, 50)]) == 0


# ------------------------------------------------------------------ budget selection

def test_budget_crossing_unit_is_included():
    """THE required case: the unit that crosses B is taken, then selection stops."""
    ranked = ["a", "b", "c", "d"]
    toks = {"a": 800, "b": 800, "c": 800, "d": 800}
    assert units_at_budget(ranked, toks, 1920) == ["a", "b", "c"]  # 2400 >= 1920, stop at c


def test_budget_met_exactly_takes_no_further_unit():
    ranked = ["a", "b", "c"]
    toks = {"a": 960, "b": 960, "c": 960}
    assert units_at_budget(ranked, toks, 1920) == ["a", "b"]


def test_ranked_list_too_short_raises_rather_than_understating():
    with pytest.raises(RuntimeError, match="R4"):
        units_at_budget(["a"], {"a": 100}, 1920)


# ------------------------------------------------------------------ decomposition

def test_decomposition_sums_on_the_lattice():
    """THE required case: the four inner differences sum to the total on integer numerators."""
    n, iters, seed = 12, 200, 1337
    vecs = {
        "U256":     [1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0],
        "U768":     [1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 0],
        "U768-ws":  [1, 1, 0, 1, 1, 1, 1, 0, 1, 0, 0, 0],
        "S768":     [1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0],
        "F768":     [1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0],
    }
    c = lambda x, y: contrast(vecs[x], vecs[y], n, iters, seed)
    dec = {"D_int_size": c("U768", "U256"), "D_int_ws": c("U768-ws", "U768"),
           "D_int_seam": c("S768", "U768-ws"), "D_int_edit": c("F768", "S768"),
           "D_int_total": c("F768", "U256")}
    assert assert_decomposition(dec) == 6
    assert dec["D_int_total"]["delta_exact"] == "6/12"


def test_contrast_records_discordant_pairs_without_testing_on_them():
    a, b = [1, 1, 0, 0], [1, 0, 1, 0]
    d = contrast(a, b, 4, 200, 1337)
    assert d["numerator"] == 0
    assert d["discordant"] == {"n01": 1, "n10": 1, "informative": 2,
                               "_note": d["discordant"]["_note"]}


def test_contrast_rejects_broken_pairing():
    with pytest.raises(AssertionError, match="pairing broken"):
        contrast([1, 0], [1, 0, 1], 2, 200, 1337)
