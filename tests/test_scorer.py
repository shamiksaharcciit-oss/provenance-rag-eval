"""Hand-checked scorer correctness (plan §6.4). Must be green before any real run."""
from __future__ import annotations

import math

from src.chunkers.base import Unit
from src.datasets.base import GoldSpan, Query
from src.score.provenance import ANY, STRICT, covered_chars, is_hit, hit_flags
from src.score.metrics import ndcg_at_k, recall_at_k, reciprocal_rank, first_hit_rank


def _q(spans, qid="q1"):
    return Query(query_id=qid, text="?", gold_spans=spans, qtype="factual")


def _u(ranges, uid="u", doc="d1"):
    return Unit(unit_id=uid, text="x", doc_id=doc, source_ranges=ranges)


# ---------------- covered_chars / overlap geometry ----------------

def test_covered_basic_overlap():
    # gold [10,20); unit range [15,30) -> shares [15,20) = 5 chars
    g = GoldSpan("d1", 10, 20)
    u = _u([(15, 30)])
    assert covered_chars(u, g) == 5


def test_covered_no_overlap():
    g = GoldSpan("d1", 10, 20)
    assert covered_chars(_u([(20, 40)]), g) == 0  # half-open: [20,40) touches but no overlap
    assert covered_chars(_u([(0, 10)]), g) == 0


def test_covered_full_containment():
    g = GoldSpan("d1", 10, 20)
    assert covered_chars(_u([(0, 100)]), g) == 10  # whole gold span (len 10) covered


def test_covered_union_no_double_count():
    # two overlapping unit ranges both cover part of gold; union must not double count
    g = GoldSpan("d1", 0, 10)
    u = _u([(0, 6), (4, 10)])  # union covers [0,10) = 10, naive sum would be 6+6=12
    assert covered_chars(u, g) == 10


def test_covered_multiple_disjoint_ranges():
    g = GoldSpan("d1", 0, 100)
    u = _u([(0, 10), (90, 100)])  # 10 + 10
    assert covered_chars(u, g) == 20


def test_doc_id_mismatch_is_zero():
    g = GoldSpan("d1", 10, 20)
    u = _u([(15, 30)], doc="OTHER")
    assert covered_chars(u, g) == 0
    assert is_hit(u, _q([g])) is False


# ---------------- is_hit variants ----------------

def test_any_overlap_hit_and_miss():
    g = GoldSpan("d1", 10, 20)
    assert is_hit(_u([(19, 25)]), _q([g]), variant=ANY) is True   # 1 char overlap
    assert is_hit(_u([(21, 25)]), _q([g]), variant=ANY) is False  # no overlap


def test_strict_containment_threshold():
    g = GoldSpan("d1", 0, 10)  # len 10 -> need >=5 covered for 50%
    assert is_hit(_u([(0, 5)]), _q([g]), variant=STRICT) is True    # exactly 50%
    assert is_hit(_u([(0, 4)]), _q([g]), variant=STRICT) is False   # 40%
    # any-overlap still counts the 40% case as a hit
    assert is_hit(_u([(0, 4)]), _q([g]), variant=ANY) is True


def test_hit_against_any_of_multiple_gold_spans():
    q = _q([GoldSpan("d1", 0, 5), GoldSpan("d1", 100, 110)])
    assert is_hit(_u([(102, 108)]), q, variant=ANY) is True


# ---------------- metrics: recall@k, nDCG@k, MRR ----------------

def test_recall_at_k():
    flags = [0, 0, 1, 0, 1]
    assert recall_at_k(flags, 1) == 0
    assert recall_at_k(flags, 2) == 0
    assert recall_at_k(flags, 3) == 1
    assert recall_at_k(flags, 5) == 1


def test_first_hit_rank_and_rr():
    assert first_hit_rank([0, 0, 1]) == 3
    assert first_hit_rank([0, 0, 0]) is None
    assert reciprocal_rank([0, 1, 0]) == 0.5
    assert reciprocal_rank([1]) == 1.0
    assert reciprocal_rank([0, 0]) == 0.0


def test_ndcg_hand_computed():
    # hit at ranks 1 and 3 (positions), k=3
    # DCG = 1/log2(2) + 0 + 1/log2(4) = 1.0 + 0.5 = 1.5
    # 2 hits -> IDCG = 1/log2(2) + 1/log2(3) = 1.0 + 0.6309 = 1.6309
    flags = [1, 0, 1]
    dcg = 1.0 + 1.0 / math.log2(4)
    idcg = 1.0 + 1.0 / math.log2(3)
    assert math.isclose(ndcg_at_k(flags, 3), dcg / idcg, rel_tol=1e-9)


def test_ndcg_perfect_and_empty():
    assert ndcg_at_k([1, 1, 1], 3) == 1.0     # already ideal
    assert ndcg_at_k([0, 0, 0], 3) == 0.0


def test_hit_flags_orders_with_units():
    g = GoldSpan("d1", 10, 20)
    ranked = [_u([(0, 5)], "a"), _u([(15, 18)], "b"), _u([(50, 60)], "c")]
    assert hit_flags(ranked, _q([g]), variant=ANY) == [0, 1, 0]
