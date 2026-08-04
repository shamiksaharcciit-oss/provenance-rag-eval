"""Reranker invariants (amendment v1.3, M6).

These enforce the three constraints the amendment commits to, rather than assuming them:

  1. Provenance survives — a reranker may only PERMUTE; any change to the unit set, its
     text, or its source_ranges is a hard failure. Hits are scored against original document
     character ranges, so a reranker that rewrote a unit would silently invalidate every
     metric downstream.
  2. Reranking reorders, it does not resize — unit texts and token statistics are untouched,
     so the v1.1 common-size control is unaffected.
  3. Reranking off is a true no-op — every pre-v1.3 number must reproduce exactly.
"""
from __future__ import annotations

import pytest

from src.chunkers.base import Unit
from src.pipeline import compute_chunk_stats
from src.rerank import NoopReranker, ProvenanceViolation, Reranker, assert_permutation
from src.rerank.base import build_reranker


def _units(n: int = 5) -> list[Unit]:
    return [
        Unit(unit_id=f"u{i}", text=f"unit {i} about HNSW and port 5005{i}",
             doc_id="d0", source_ranges=[(i * 100, i * 100 + 80)])
        for i in range(n)
    ]


class _Reverse(Reranker):
    name = "reverse"

    def _order(self, query, units):
        return list(reversed(units))


class _Duplicates(Reranker):
    name = "bad-duplicate"

    def _order(self, query, units):
        return list(units) + [units[0]]


class _Rewrites(Reranker):
    name = "bad-rewrite"

    def _order(self, query, units):
        out = list(units)
        out[0] = Unit(unit_id=out[0].unit_id, text="REWRITTEN", doc_id=out[0].doc_id,
                      source_ranges=out[0].source_ranges)
        return out


class _DropsProvenance(Reranker):
    name = "bad-provenance"

    def _order(self, query, units):
        out = list(units)
        out[0] = Unit(unit_id=out[0].unit_id, text=out[0].text, doc_id=out[0].doc_id,
                      source_ranges=[])
        return out


# -- 1. provenance / permutation ------------------------------------------------------

def test_valid_reorder_is_accepted_and_preserves_provenance():
    us = _units()
    out = _Reverse().rerank("q", us)
    assert [u.unit_id for u in out] == ["u4", "u3", "u2", "u1", "u0"]
    assert {u.unit_id: u.source_ranges for u in out} == {u.unit_id: u.source_ranges for u in us}


def test_dropping_a_unit_is_rejected():
    with pytest.raises(ProvenanceViolation, match="pool size"):
        assert_permutation(_units(5), _units(5)[:4])


def test_duplicating_a_unit_is_rejected():
    with pytest.raises(ProvenanceViolation):
        _Duplicates().rerank("q", _units())


def test_rewriting_unit_text_is_rejected():
    with pytest.raises(ProvenanceViolation, match="text or source_ranges"):
        _Rewrites().rerank("q", _units())


def test_discarding_source_ranges_is_rejected():
    """The failure mode that would corrupt scoring most quietly: same ids, same text,
    provenance silently emptied. Every hit against that unit would then be a miss."""
    with pytest.raises(ProvenanceViolation, match="text or source_ranges"):
        _DropsProvenance().rerank("q", _units())


def test_empty_pool_is_handled():
    assert NoopReranker().rerank("q", []) == []


# -- 2. reorders, does not resize -----------------------------------------------------

def test_chunk_stats_are_invariant_under_reranking():
    """Confirms rather than assumes: the v1.1 common-size control measures unit token size,
    which reranking cannot touch because it never constructs a Unit."""
    us = _units(8)
    before = compute_chunk_stats(us, n_docs=1)
    after = compute_chunk_stats(_Reverse().rerank("q", us), n_docs=1)
    assert before == after


def test_reranking_does_not_change_the_text_of_any_unit():
    us = _units(6)
    out = _Reverse().rerank("q", us)
    assert sorted(u.text for u in out) == sorted(u.text for u in us)


# -- 3. off is a true no-op -----------------------------------------------------------

def test_disabled_by_default():
    assert build_reranker({}) is None
    assert build_reranker({"rerank": {"enabled": False}}) is None


def test_noop_backend_preserves_order_exactly():
    us = _units(6)
    rr = build_reranker({"rerank": {"enabled": True, "backend": "noop"}})
    assert isinstance(rr, NoopReranker)
    assert [u.unit_id for u in rr.rerank("q", us)] == [u.unit_id for u in us]


def test_unknown_backend_fails_loudly():
    with pytest.raises(ValueError, match="unknown rerank.backend"):
        build_reranker({"rerank": {"enabled": True, "backend": "magic"}})
