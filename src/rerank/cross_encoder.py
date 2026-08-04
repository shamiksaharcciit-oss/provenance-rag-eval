"""Cross-encoder reranker (amendment v1.3, M6).

A cross-encoder scores (query, passage) jointly rather than comparing two independently
produced embeddings, which is why it can reorder a pool the bi-encoder got wrong. It is
applied to the fused candidate pool (default 50) and the top-k is taken AFTER reordering —
reranking only the top-k could never change recall@k, since no new unit would enter the cut.

Model is pinned and recorded into results.json alongside the embedding model, same as every
other model in the harness (§11).
"""
from __future__ import annotations

import os

from src.chunkers.base import Unit
from src.rerank.base import Reranker


class RerankerUnavailable(RuntimeError):
    """The cross-encoder could not be loaded — fail loud rather than silently not reranking."""


class CrossEncoderReranker(Reranker):
    name = "cross_encoder"

    def __init__(
        self,
        model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        revision: str = "main",
        batch_size: int = 32,
        device: str = "cpu",
        max_length: int = 512,
        threads: int = 0,
    ) -> None:
        self.model_name = model
        self.revision = revision
        self.batch_size = batch_size
        self.device = device
        self.max_length = max_length
        # run.py pins OMP_NUM_THREADS=1 to stop the faiss/torch duplicate-OpenMP abort on
        # Windows. That also throttles the cross-encoder to ~7 pairs/s. Raising torch's own
        # thread count (not the OpenMP env var) roughly doubles throughput without touching
        # faiss. Purely a performance setting: same model, same inputs, same scores.
        self.threads = threads or max(1, (os.cpu_count() or 2) - 0)
        self._model = None
        self.calls = 0
        self.pairs_scored = 0

    def _load(self):
        if self._model is not None:
            return self._model
        try:
            import torch
            from sentence_transformers import CrossEncoder
        except Exception as e:  # pragma: no cover - import guard
            raise RerankerUnavailable(f"sentence-transformers not importable: {e}") from e
        try:
            torch.set_num_threads(self.threads)
        except Exception:
            pass  # performance only — never fail a run over a thread hint
        try:
            self._model = CrossEncoder(
                self.model_name,
                revision=self.revision,
                max_length=self.max_length,
                device=self.device,
            )
        except Exception as e:
            raise RerankerUnavailable(
                f"could not load cross-encoder {self.model_name!r}: {str(e)[:200]}") from e
        return self._model

    def _order(self, query: str, units: list[Unit]) -> list[Unit]:
        model = self._load()
        pairs = [(query, u.text) for u in units]
        scores = model.predict(
            pairs, batch_size=self.batch_size, show_progress_bar=False)
        self.calls += 1
        self.pairs_scored += len(pairs)
        # Stable sort on the negated score: ties keep the fused order they arrived in, so a
        # model that cannot separate two candidates does not shuffle them at random.
        order = sorted(range(len(units)), key=lambda i: (-float(scores[i]), i))
        return [units[i] for i in order]

    def describe(self) -> dict:
        return {
            "name": self.name,
            "model": self.model_name,
            "revision": self.revision,
            "max_length": self.max_length,
            "calls": self.calls,
            "pairs_scored": self.pairs_scored,
        }
