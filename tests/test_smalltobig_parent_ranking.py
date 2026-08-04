"""v1.5 primary path: parent-level fusion, parent-denominated pool, set-identity guard.

Every assertion here is paired with a NEGATIVE CONTROL demonstrating it fails against a
deliberate violation, per criteria template §A1b. An assertion never observed failing is a
regression guard, not evidence.

The bug these guard against (v1.5 §1): `Retriever` truncates each modality to
`index.candidate_pool` and fuses at whatever level it was handed. Handing it children made the
treatment arm (a) fuse at child level, losing RRF's agreement bonus, and (b) reach only ~50
children deep instead of 50 parents. Both biases run one way — against the treatment — and both
land in the primary metric.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.chunkers.base import Unit
from src.smalltobig.retrieve import (
    ParentRankingDepthMismatch,
    SmallToBigRetriever,
    assert_parent_inventory_identity,
)


class _StubEmbedder:
    """Deterministic bag-of-words vectors — no model download, no CPU cost."""

    def __init__(self, vocab: list[str]) -> None:
        self.vocab = vocab

    def encode(self, texts: list[str]) -> np.ndarray:
        v = np.zeros((len(texts), len(self.vocab)), dtype=np.float32)
        for i, t in enumerate(texts):
            toks = t.lower().split()
            for j, w in enumerate(self.vocab):
                v[i, j] = toks.count(w)
        n = np.linalg.norm(v, axis=1, keepdims=True)
        return v / np.maximum(n, 1e-9)


def _corpus(n_parents: int = 8, children_per: int = 4):
    """n_parents baseline units, each subdivided into `children_per` children."""
    parents, children = [], []
    for p in range(n_parents):
        words = [f"w{p}{c}" for c in range(children_per)]
        parents.append(Unit(unit_id=f"C0:d:{p}", text=" ".join(words), doc_id="d",
                            source_ranges=[(p * 100, p * 100 + 50)]))
        for c, w in enumerate(words):
            children.append(Unit(unit_id=f"C0s2b:d:{p}:{c}", text=w, doc_id="d",
                                 source_ranges=[(p * 100 + c, p * 100 + c + 5)],
                                 meta={"parent_id": f"C0:d:{p}"}))
    vocab = sorted({w for u in children for w in u.text.split()})
    return parents, children, _StubEmbedder(vocab)


def _cfg(pool: int) -> dict:
    return {"index": {"candidate_pool": pool, "k_rrf": 60}}


# ---------------------------------------------------------------------------
# 1. The pool is denominated in DELIVERED PARENTS, not indexed children
# ---------------------------------------------------------------------------

def test_pool_reaches_candidate_pool_distinct_parents_not_children():
    """8 parents x 4 children = 32 children. A pool of 8 must reach all 8 PARENTS.

    Under the v1.4-style bug the same pool would have consumed 8 CHILDREN, reaching at most
    8 parents and typically far fewer, since siblings cluster.
    """
    parents, children, emb = _corpus(8, 4)
    r = SmallToBigRetriever(children, parents, emb, _cfg(8))
    out = r.retrieve_parents("w00 w31", top_k=5)
    assert out["depth"]["dense"] == 8, "dense ranking must reach 8 distinct parents"
    assert out["depth"]["sparse"] == 8, "sparse ranking must reach 8 distinct parents"


def test_depth_assertion_bites_when_pool_is_denominated_in_children():
    """NEGATIVE CONTROL for the depth guard.

    Simulates the bug by truncating the child walk to `candidate_pool` CHILDREN rather than
    parents. With 4 children per parent, 8 child slots yield ~2 parents, not 8 — and the
    assertion must fire. If this ever passes, the guard has stopped guarding.
    """
    parents, children, emb = _corpus(8, 4)
    r = SmallToBigRetriever(children, parents, emb, _cfg(8))

    def broken_walk(ranked_child_ix):
        seen, out = set(), []
        for i in ranked_child_ix[:r.candidate_pool]:      # <-- truncate CHILDREN (the bug)
            pid = r.children[i].meta["parent_id"]
            if pid not in seen:
                seen.add(pid); out.append(pid)
        return out

    r._parents_from_child_ranking = broken_walk  # type: ignore[method-assign]
    with pytest.raises(ParentRankingDepthMismatch):
        r.retrieve_parents("w00 w31", top_k=5)


def test_both_modalities_have_equal_depth_per_query():
    parents, children, emb = _corpus(6, 3)
    r = SmallToBigRetriever(children, parents, emb, _cfg(4))
    out = r.retrieve_parents("w00 w51", top_k=3)
    assert out["depth"]["dense"] == out["depth"]["sparse"] == out["depth"]["expected"] == 4


def test_pool_larger_than_corpus_exhausts_rather_than_failing():
    parents, children, emb = _corpus(3, 2)
    r = SmallToBigRetriever(children, parents, emb, _cfg(50))
    out = r.retrieve_parents("w00", top_k=3)
    assert out["depth"]["expected"] == 3, "expected depth clamps to the distinct-parent count"


# ---------------------------------------------------------------------------
# 2. Fusion happens at PARENT level
# ---------------------------------------------------------------------------

def test_rrf_receives_PARENT_level_rankings_not_child_level(monkeypatch):
    """The §1a fix, tested at the specification rather than through behaviour.

    The defect was fusing two CHILD-level rankings and then taking max, which loses RRF's
    cross-modality agreement bonus whenever the two modalities land on different siblings of
    the same parent. The fix is that RRF must receive two PARENT-level rankings.

    Asserted by capturing what `rrf_fuse` is actually handed. A behavioural proxy cannot test
    this here: bag-of-words dense and BM25 sparse agree almost perfectly on single-token
    children, so there is no disagreement for fusion to resolve.

    Note also what max-over-children does NOT do: a parent with two matching children gets no
    more credit than one with a single equally-good child. First appearance IS max, and max
    ignores multiplicity — sibling count must not become a ranking signal.
    """
    parents, children, emb = _corpus(6, 3)
    r = SmallToBigRetriever(children, parents, emb, _cfg(6))
    captured: list[list[list[int]]] = []
    import src.smalltobig.retrieve as mod
    real = mod.rrf_fuse
    monkeypatch.setattr(mod, "rrf_fuse", lambda rankings, k: captured.append(rankings) or real(rankings, k))

    r.retrieve_parents("w00 w01 w52", top_k=6)

    assert len(captured) == 1, "fusion must happen exactly once, after parent ranking"
    rankings = captured[0]
    assert len(rankings) == 2, "two modality rankings fused"
    n_parents = len(parents)
    for ranking in rankings:
        # Parent-level: every entry indexes a PARENT, and no parent repeats.
        assert len(ranking) == len(set(ranking)), "a parent appeared twice — child-level leak"
        assert len(ranking) <= n_parents, "ranking longer than the parent inventory"
        assert all(0 <= i < n_parents for i in ranking), "index outside the parent inventory"
    assert len(rankings[0]) == len(rankings[1]) == 6, "both modalities at candidate_pool depth"


def test_sibling_count_is_not_a_ranking_signal():
    """max-over-children ignores multiplicity: a parent with many matching children must not
    outrank one whose single best child matches equally well. Guards against a future change
    to sum-over-children, which would make sibling count a mechanical advantage."""
    parents, children, emb = _corpus(4, 4)
    r = SmallToBigRetriever(children, parents, emb, _cfg(4))
    many = r.retrieve_parents("w00 w01 w02", top_k=4)["hybrid"][0].unit_id
    one = r.retrieve_parents("w00", top_k=4)["hybrid"][0].unit_id
    assert many == one == "C0:d:0", "same parent leads whether one or three of its children match"


def test_delivered_units_are_baseline_parents_not_children():
    parents, children, emb = _corpus(5, 3)
    r = SmallToBigRetriever(children, parents, emb, _cfg(5))
    out = r.retrieve_parents("w00", top_k=3)
    baseline_ids = {p.unit_id for p in parents}
    for u in out["hybrid"]:
        assert u.unit_id in baseline_ids, "delivered unit must be a baseline parent"
        assert u.source_ranges, "delivered parent carries source_ranges legitimately under v1.5"


# ---------------------------------------------------------------------------
# 3. Set-identity guard — and its negative control
# ---------------------------------------------------------------------------

def test_set_identity_holds_by_construction():
    """TRUE BY CONSTRUCTION, therefore a REGRESSION guard, not evidence (template §A1b)."""
    parents, children, _emb = _corpus(4, 2)
    assert_parent_inventory_identity({p.unit_id: p for p in parents}, parents)


def test_set_identity_bites_on_a_widened_inventory():
    """NEGATIVE CONTROL: a parent that is not a baseline unit must fail the assertion."""
    parents, children, _emb = _corpus(4, 2)
    widened = {p.unit_id: p for p in parents}
    widened["C0:d:INVENTED"] = Unit(unit_id="C0:d:INVENTED", text="wider", doc_id="d",
                                    source_ranges=[(0, 99999)])
    with pytest.raises(ValueError, match="set-identical"):
        assert_parent_inventory_identity(widened, parents)


def test_children_referencing_an_unknown_parent_are_rejected_at_build():
    parents, children, emb = _corpus(4, 2)
    children.append(Unit(unit_id="orphan", text="x", doc_id="d", source_ranges=[(0, 1)],
                         meta={"parent_id": "C0:d:NOT_A_BASELINE_UNIT"}))
    with pytest.raises(ValueError, match="set-identity violated"):
        SmallToBigRetriever(children, parents, emb, _cfg(4))


# ---------------------------------------------------------------------------
# 4. Reporting required by §4
# ---------------------------------------------------------------------------

def test_children_per_parent_distribution_is_reported():
    parents, children, emb = _corpus(5, 4)
    r = SmallToBigRetriever(children, parents, emb, _cfg(5))
    counts = r.children_per_parent()
    assert set(counts) == {p.unit_id for p in parents}
    assert all(v == 4 for v in counts.values())
