"""Query -> ranked Units, via dense, sparse, and RRF-fused hybrid (plan §5.4, §7.4).

Dense-only and hybrid rankings are both exposed because the H2 guardrail (§2.3, §7.4)
compares them: vocabulary drift shows up as hybrid failing to track dense.
"""
from __future__ import annotations

import numpy as np

from src.chunkers.base import Unit
from src.index.embed import Embedder
from src.index.store import DenseIndex, SparseIndex


def rrf_fuse(rankings: list[list[int]], k_rrf: int = 60) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion over several ranked id-lists. Higher score = better."""
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):  # rank is 0-indexed
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k_rrf + rank + 1)
    return sorted(scores.items(), key=lambda kv: -kv[1])


class Retriever:
    """Holds a unit set, its dense+sparse indexes, and answers queries."""

    def __init__(self, units: list[Unit], embedder: Embedder, cfg: dict) -> None:
        self.units = units
        self.embedder = embedder
        idx = cfg.get("index", {})
        self.k_rrf = idx.get("k_rrf", 60)
        self.candidate_pool = idx.get("candidate_pool", 50)
        texts = [u.text for u in units]
        self.vectors = embedder.encode(texts)
        self.dense = DenseIndex(self.vectors)
        self.sparse = SparseIndex(texts)

    # -- single query -------------------------------------------------------
    def _dense_ranking(self, qvec: np.ndarray, pool: int) -> list[int]:
        res = self.dense.search(qvec[None, :], pool)[0]
        return [i for i, _ in res]

    def _sparse_ranking(self, query_text: str, pool: int) -> list[int]:
        return [i for i, _ in self.sparse.search(query_text, pool)]

    def retrieve(self, query_text: str, top_k: int, reranker=None) -> dict[str, list[Unit]]:
        """Return {'dense': [...], 'sparse': [...], 'hybrid': [...]} ranked Units.

        With a `reranker`, additionally returns 'hybrid_rerank': the fused CANDIDATE POOL
        reordered by the cross-encoder, then cut to top_k. Reranking the pool rather than the
        top-k is what allows recall@k to move — reordering within the cut could never admit a
        unit that the first-stage ranking placed below it (amendment v1.3 §3).
        """
        pool = max(self.candidate_pool, top_k)
        qvec = self.embedder.encode([query_text])[0]
        dense_ids = self._dense_ranking(qvec, pool)
        sparse_ids = self._sparse_ranking(query_text, pool)
        hybrid = [i for i, _ in rrf_fuse([dense_ids, sparse_ids], self.k_rrf)]
        out = {
            "dense": [self.units[i] for i in dense_ids[:top_k]],
            "sparse": [self.units[i] for i in sparse_ids[:top_k]],
            "hybrid": [self.units[i] for i in hybrid[:top_k]],
        }
        if reranker is not None:
            pool_units = [self.units[i] for i in hybrid[:pool]]
            out["hybrid_rerank"] = reranker.rerank(query_text, pool_units)[:top_k]
        return out
