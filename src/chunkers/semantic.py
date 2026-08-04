"""C1 — Semantic chunking (plan §5.2).

Embedding-similarity boundary detection between adjacent sentences: place a break
where the cosine distance between consecutive sentence embeddings exceeds a percentile
threshold, subject to min/max token bounds. Units are contiguous sentence groups, so
provenance is the underlying chunk's char offsets (§6.1).
"""
from __future__ import annotations

import numpy as np

from src.chunkers.base import Chunker, ChunkContext, Unit
from src.datasets.base import Document
from src.textutil import count_tokens, sentence_spans


class SemanticChunker(Chunker):
    condition_id = "C1"

    def __init__(self, params: dict, ctx: ChunkContext | None = None) -> None:
        super().__init__(params, ctx)
        if ctx is None or ctx.embedder is None:
            raise ValueError("SemanticChunker requires an embedder in ChunkContext")
        self.embedder = ctx.embedder

    def chunk(self, doc: Document) -> list[Unit]:
        spans = sentence_spans(doc.text)
        if not spans:
            return []
        if len(spans) == 1:
            s, e = spans[0]
            return [self._unit(doc, 0, [(s, e)])]

        sents = [doc.text[s:e] for s, e in spans]
        vecs = self.embedder.encode(sents)  # normalized
        # cosine distance between consecutive sentences
        dists = 1.0 - np.sum(vecs[:-1] * vecs[1:], axis=1)
        pct = self.params.get("breakpoint_percentile", 90)
        thresh = float(np.percentile(dists, pct)) if len(dists) else 1.0
        max_tokens = self.params.get("max_tokens", 512)
        min_tokens = self.params.get("min_tokens", 64)

        groups: list[list[int]] = [[0]]
        for i in range(1, len(spans)):
            cur = groups[-1]
            cur_tokens = sum(count_tokens(sents[j]) for j in cur)
            over_budget = cur_tokens + count_tokens(sents[i]) > max_tokens
            semantic_break = dists[i - 1] >= thresh and cur_tokens >= min_tokens
            if over_budget or semantic_break:
                groups.append([i])
            else:
                cur.append(i)

        units = []
        for gi, g in enumerate(groups):
            start = spans[g[0]][0]
            end = spans[g[-1]][1]
            units.append(self._unit(doc, gi, [(start, end)]))
        return units

    def _unit(self, doc: Document, gi: int, ranges: list[tuple[int, int]]) -> Unit:
        s, e = ranges[0][0], ranges[-1][1]
        return Unit(
            unit_id=f"{self.condition_id}:{doc.doc_id}:{gi}",
            text=doc.text[s:e],
            doc_id=doc.doc_id,
            source_ranges=ranges,
        )
