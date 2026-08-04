"""Retrieval metrics on binary hit flags (plan §6.3, §7).

recall@k(q) = 1 if any unit in top-k retrieved for q is a hit else 0
Recall@k    = mean over queries of recall@k(q)
nDCG@k, MRR use the same binary hit relevance.
"""
from __future__ import annotations

import math


def recall_at_k(flags: list[int], k: int) -> int:
    """0/1 for a single query: did any of the top-k retrieved units hit?"""
    return 1 if any(flags[:k]) else 0


def ndcg_at_k(flags: list[int], k: int) -> float:
    """Binary-relevance nDCG@k. IDCG places all found hits at the top ranks."""
    topk = flags[:k]
    dcg = 0.0
    for i, rel in enumerate(topk):  # position i is 1-indexed as i+1
        if rel:
            dcg += 1.0 / math.log2(i + 2)
    num_hits = sum(topk)
    if num_hits == 0:
        return 0.0
    idcg = sum(1.0 / math.log2(i + 2) for i in range(num_hits))
    return dcg / idcg if idcg > 0 else 0.0


def first_hit_rank(flags: list[int]) -> int | None:
    """1-indexed rank of the first hit in the full ranked list, or None."""
    for i, rel in enumerate(flags):
        if rel:
            return i + 1
    return None


def reciprocal_rank(flags: list[int]) -> float:
    """1/rank of first hit (0 if none) — the per-query term of MRR."""
    r = first_hit_rank(flags)
    return 1.0 / r if r else 0.0


def aggregate(per_query_flags: list[list[int]], k_values: list[int]) -> dict:
    """Aggregate Recall@k, nDCG@k, MRR over many queries.

    Returns point estimates plus the per-query vectors (needed for bootstrap CIs).
    """
    n = len(per_query_flags)
    out: dict = {"n_queries": n, "recall_at_k": {}, "ndcg_at_k": {}, "mrr": 0.0,
                 "_per_query": {"recall_at_k": {}, "ndcg_at_k": {}, "rr": []}}
    if n == 0:
        return out
    for k in k_values:
        rvec = [recall_at_k(f, k) for f in per_query_flags]
        nvec = [ndcg_at_k(f, k) for f in per_query_flags]
        out["recall_at_k"][k] = sum(rvec) / n
        out["ndcg_at_k"][k] = sum(nvec) / n
        out["_per_query"]["recall_at_k"][k] = rvec
        out["_per_query"]["ndcg_at_k"][k] = nvec
    rr = [reciprocal_rank(f) for f in per_query_flags]
    out["mrr"] = sum(rr) / n
    out["_per_query"]["rr"] = rr
    return out
