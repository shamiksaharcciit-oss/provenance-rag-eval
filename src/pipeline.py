"""End-to-end evaluation for one (track, condition) (plan §4 pipeline, §6, §7).

load docs+queries+gold -> chunk into Units (provenance) -> embed -> index (dense+sparse)
-> retrieve top-k per query -> score vs gold via provenance overlap -> aggregate.

Retrieval is computed once per query; scoring is applied under BOTH overlap variants
("any" lenient primary, "strict" >=50% containment) and for BOTH dense-only and hybrid
rankings (the H2 guardrail, §7.4).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from src.chunkers.base import Chunker, Unit
from src.datasets.base import Dataset, Query
from src.index.embed import Embedder
from src.retrieve.retriever import Retriever
from src.score.metrics import aggregate
from src.score.provenance import hit_flags
from src.textutil import count_tokens


@dataclass
class EvalResult:
    condition_id: str
    n_queries: int
    k_values: list[int]
    # metrics[retriever][variant] -> aggregate dict (incl. _per_query vectors)
    metrics: dict = field(default_factory=dict)
    chunk_stats: dict = field(default_factory=dict)
    index_seconds: float = 0.0
    format_seconds: float = 0.0
    llm_cost: dict = field(default_factory=dict)  # per-condition fresh/cached (v1.1 §5.3)
    common_size_recall5: float | None = None       # recall@5 at fixed 256 (v1.1 §5.2)
    per_query: list[dict] = field(default_factory=list)
    # query_id -> top-k unit texts (hybrid), for the faithfulness judge
    contexts: dict = field(default_factory=dict)
    rerank: dict = field(default_factory=dict)  # model/pins/timing when the axis is on (v1.3)


def build_units(chunker: Chunker, dataset: Dataset) -> list[Unit]:
    return chunker.chunk_all(dataset.documents)


def compute_chunk_stats(units: list[Unit], n_docs: int) -> dict:
    n = len(units)
    toks = [count_tokens(u.text) for u in units]
    token_mean = sum(toks) / n if n else 0.0
    return {
        "units_per_doc_mean": (n / n_docs) if n_docs else 0.0,
        "token_mean": round(token_mean, 2),
        "index_units": n,
    }


def evaluate(
    condition_id: str,
    units: list[Unit],
    embedder: Embedder,
    cfg: dict,
    queries: list[Query],
    n_docs: int,
    reranker=None,
) -> EvalResult:
    """Evaluate one condition. With a `reranker`, the 'hybrid_rerank' ranking is scored
    alongside 'dense' and 'hybrid' from the SAME retrieval call — so reranked and
    un-reranked metrics are paired per query, which is what the H6 stats require
    (amendment v1.3 §4). The reranker is an added ranking, never a replacement: with
    reranking off, every existing number is unchanged.
    """
    k_values = cfg.get("retrieval", {}).get("k_values", [1, 3, 5, 10])
    max_k = max(k_values)
    scoring = cfg.get("scoring", {})
    min_overlap = scoring.get("min_overlap_chars", 1)
    containment = scoring.get("strict_containment", 0.5)

    t0 = time.time()
    retriever = Retriever(units, embedder, cfg)
    index_seconds = time.time() - t0

    rankings = ("dense", "hybrid") + (("hybrid_rerank",) if reranker is not None else ())

    # flags[ranking][variant] -> list of per-query flag lists (top-max_k)
    flags: dict[str, dict[str, list[list[int]]]] = {
        r: {"any": [], "strict": []} for r in rankings
    }
    per_query: list[dict] = []
    contexts: dict[str, list[str]] = {}
    t_rerank = 0.0

    for q in queries:
        t1 = time.time()
        ranked = retriever.retrieve(q.text, max_k, reranker=reranker)
        if reranker is not None:
            t_rerank += time.time() - t1
        contexts[q.query_id] = [u.text for u in ranked["hybrid"][:5]]
        rec = {"query_id": q.query_id, "qtype": q.qtype,
               "doc_id": q.gold_spans[0].doc_id,
               "gold_spans": [g.as_dict() for g in q.gold_spans]}
        for r in rankings:
            units_ranked = ranked[r]
            for variant in ("any", "strict"):
                f = hit_flags(units_ranked, q, variant=variant,
                              min_overlap=min_overlap, containment=containment)
                flags[r][variant].append(f)
                if variant == "any" and r in ("hybrid", "hybrid_rerank"):
                    first = next((i + 1 for i, x in enumerate(f) if x), None)
                    top_hit = next((u for u, x in zip(units_ranked, f) if x), None)
                    if r == "hybrid":
                        rec["retrieved_unit_ids"] = [u.unit_id for u in units_ranked[:max_k]]
                        rec["hit@k"] = {k: (1 if any(f[:k]) else 0) for k in k_values}
                        rec["first_hit_rank"] = first
                        rec["top_hit_provenance"] = top_hit.source_ranges if top_hit else None
                    else:
                        # Recorded per query so a reviewer can see WHICH queries the reranker
                        # rescued or broke, not merely that the aggregate moved.
                        rec["rerank_retrieved_unit_ids"] = [
                            u.unit_id for u in units_ranked[:max_k]]
                        rec["rerank_hit@k"] = {k: (1 if any(f[:k]) else 0) for k in k_values}
                        rec["rerank_first_hit_rank"] = first
                        rec["rerank_top_hit_provenance"] = (
                            top_hit.source_ranges if top_hit else None)
        per_query.append(rec)

    metrics: dict = {r: {} for r in rankings}
    for r in rankings:
        for variant in ("any", "strict"):
            metrics[r][variant] = aggregate(flags[r][variant], k_values)

    return EvalResult(
        condition_id=condition_id,
        n_queries=len(queries),
        k_values=k_values,
        metrics=metrics,
        chunk_stats=compute_chunk_stats(units, n_docs),
        index_seconds=round(index_seconds, 3),
        per_query=per_query,
        contexts=contexts,
        rerank=(
            {**reranker.describe(), "seconds": round(t_rerank, 2)}
            if reranker is not None else {}
        ),
    )
