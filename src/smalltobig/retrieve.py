"""Parent-level retrieval for small-to-big (amendment v1.5 §4).

THE PROBLEM THIS SOLVES
=======================
`Retriever` builds both indexes over whatever unit list it is handed, then truncates each
modality to `index.candidate_pool` and RRF-fuses. Hand it parents and the pool is 50 parents;
hand it children — which the treatment arm must — and the pool is 50 *children*. Two
one-directional biases against the treatment, both in the primary metric:

1. **Fusion at the wrong level.** The baseline fuses two PARENT-level rankings, so a parent that
   is a moderate dense match AND a moderate sparse match collects both RRF terms — that
   agreement bonus is the entire point of RRF. Fusing at CHILD level and then taking max over
   children picks the single best child, which usually carries one modality's evidence, so the
   treatment behaves like max(dense, sparse) while the baseline behaves like dense + sparse.
   H7 would then change the ranking function (the hypothesis) AND the fusion locus (an
   artifact) at once.

2. **Pool denominated in the indexed unit.** 50 children is bounded above by 50 parents and in
   practice far fewer, because siblings of a strong child cluster near it and consume slots. The
   treatment's reach is strictly shallower than the baseline's — exactly where §2 locates the
   hypothesis, since ~26-30 points of Track B's addressable pool lie beyond rank 50 and are
   reachable only by moving a unit a long way.

THE SPECIFICATION
=================
Both arms produce parent rankings of identical depth, per modality, and fuse at parent level.

For each modality independently (dense, sparse):
  1. Rank children by that modality's score.
  2. Walk the ranked child list in order, emitting each parent on FIRST APPEARANCE, until
     `candidate_pool` DISTINCT parents have been emitted or the child list is exhausted.
     First appearance is max-over-children by construction for a rank-based ranking, so this
     IS best-child scoring, per modality.
  3. The result is a parent ranking `candidate_pool` deep — same depth, same units as the
     baseline arm's.

Then RRF-fuse the two parent-level rankings with the same `k_rrf`, and take top-k parents.

`candidate_pool` is denominated in DELIVERED PARENTS in both arms, never in indexed children.
The child pool becomes whatever depth is needed to reach that many distinct parents — variable
per query, which is correct: the child side is now the harness parameter and the delivered side
is pinned.
"""
from __future__ import annotations

import numpy as np

from src.chunkers.base import Unit
from src.index.embed import Embedder
from src.index.store import DenseIndex, SparseIndex
from src.retrieve.retriever import rrf_fuse
from src.smalltobig.units import ParentContext


class ParentRankingDepthMismatch(RuntimeError):
    """The two arms' per-modality parent rankings differ in depth for a query.

    This is the assertion that would have caught the pool-denomination bug. Raised unless both
    rankings reached `candidate_pool` distinct parents or both exhausted their source.
    """


class SmallToBigRetriever:
    """Indexes children, ranks and delivers PARENTS.

    `parent_units` is the baseline unit inventory; `children` are its subdivisions, each
    carrying `meta['parent_id']`. Set-identity between the delivered parents and the baseline
    inventory is asserted at build time (v1.5 §4 guard).
    """

    def __init__(self, children: list[Unit], parent_units: list[Unit],
                 embedder: Embedder, cfg: dict) -> None:
        idx = cfg.get("index", {})
        self.k_rrf = idx.get("k_rrf", 60)
        self.candidate_pool = idx.get("candidate_pool", 50)
        self.children = children
        self.parents_by_id = {u.unit_id: u for u in parent_units}

        # --- guard: parent inventory must be set-identical to the baseline inventory --------
        child_parent_ids = {c.meta.get("parent_id") for c in children}
        missing = child_parent_ids - set(self.parents_by_id)
        if missing:
            raise ValueError(
                f"children reference {len(missing)} parent_id(s) absent from the baseline "
                f"inventory, e.g. {sorted(m for m in missing if m)[:3]} — set-identity violated")

        self.embedder = embedder
        texts = [c.text for c in children]
        self.vectors = embedder.encode(texts)
        self.dense = DenseIndex(self.vectors)
        self.sparse = SparseIndex(texts)

    # -- per-modality parent rankings -----------------------------------------------------
    def _parents_from_child_ranking(self, ranked_child_ix: list[int]) -> list[str]:
        """Walk a ranked child list, emitting each parent on first appearance.

        First appearance in a rank-ordered list IS max-over-children: the first time a parent
        is seen, it is via its highest-scoring child.
        """
        seen: set[str] = set()
        out: list[str] = []
        for i in ranked_child_ix:
            pid = self.children[i].meta.get("parent_id")
            if pid is None or pid in seen:
                continue
            seen.add(pid)
            out.append(pid)
            if len(out) >= self.candidate_pool:
                break
        return out

    def retrieve_parents(self, query_text: str, top_k: int) -> dict:
        """Return delivered parents plus diagnostics.

        Both modalities rank the FULL child list, then walk to `candidate_pool` distinct
        parents, so the treatment's reach is denominated in parents exactly as the baseline's is.
        """
        n_children = len(self.children)
        qvec = self.embedder.encode([query_text])[0]
        dense_ix = [i for i, _ in self.dense.search(qvec[None, :], n_children)[0]]
        sparse_ix = [i for i, _ in self.sparse.search(query_text, n_children)]

        dense_parents = self._parents_from_child_ranking(dense_ix)
        sparse_parents = self._parents_from_child_ranking(sparse_ix)

        # Depth assertion (v1.5 §4): both reached candidate_pool, or both exhausted their source.
        n_distinct = len({c.meta.get("parent_id") for c in self.children})
        expected = min(self.candidate_pool, n_distinct)
        if len(dense_parents) != expected or len(sparse_parents) != expected:
            raise ParentRankingDepthMismatch(
                f"per-modality parent depth {len(dense_parents)}/{len(sparse_parents)} != "
                f"expected {expected} (candidate_pool={self.candidate_pool}, "
                f"distinct parents={n_distinct})")

        # Fuse at PARENT level, same k_rrf as the baseline arm.
        id_to_pos = {pid: n for n, pid in enumerate(sorted(self.parents_by_id))}
        pos_to_id = {n: pid for pid, n in id_to_pos.items()}
        fused = rrf_fuse([[id_to_pos[p] for p in dense_parents],
                          [id_to_pos[p] for p in sparse_parents]], self.k_rrf)
        ranked_ids = [pos_to_id[i] for i, _ in fused]

        return {
            "hybrid": [self.parents_by_id[pid] for pid in ranked_ids[:top_k]],
            "dense": [self.parents_by_id[pid] for pid in dense_parents[:top_k]],
            "sparse": [self.parents_by_id[pid] for pid in sparse_parents[:top_k]],
            "depth": {"dense": len(dense_parents), "sparse": len(sparse_parents),
                      "expected": expected},
        }

    def children_per_parent(self) -> dict[str, int]:
        """v1.5 §4 reporting: max over N gives a parent with more children more chances."""
        counts: dict[str, int] = {}
        for c in self.children:
            pid = c.meta.get("parent_id")
            if pid:
                counts[pid] = counts.get(pid, 0) + 1
        return counts


def assert_parent_inventory_identity(parent_index: dict[str, ParentContext] | dict,
                                     baseline_units: list[Unit]) -> None:
    """v1.5 §4 guard: exact set-identity, not overlap or containment.

    TRUE BY CONSTRUCTION (parents are built from baseline units) and therefore a REGRESSION
    GUARD, not evidence — per criteria template §A1b. A negative control asserts it fails
    against a deliberately widened inventory.
    """
    baseline_ids = {u.unit_id for u in baseline_units}
    parent_ids = set(parent_index)
    if parent_ids != baseline_ids:
        extra, missing = parent_ids - baseline_ids, baseline_ids - parent_ids
        raise ValueError(
            "parent inventory is not set-identical to the baseline unit inventory: "
            f"{len(extra)} extra, {len(missing)} missing")
