"""Dense (FAISS) + sparse (BM25) indexes (plan §5.4).

Dense: inner-product over normalized vectors (== cosine). Uses FAISS IndexFlatIP if
available, else a numpy brute-force fallback (identical results, fine at this scale).
Sparse: BM25 via rank_bm25 with a numpy fallback.
"""
from __future__ import annotations

import re

import numpy as np

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


class DenseIndex:
    def __init__(self, vectors: np.ndarray) -> None:
        self.vectors = np.ascontiguousarray(vectors.astype(np.float32))
        self.n, self.dim = self.vectors.shape if vectors.size else (0, 0)
        self._faiss = None
        try:
            import faiss  # type: ignore
            self._faiss = faiss
            self.index = faiss.IndexFlatIP(self.dim)
            if self.n:
                self.index.add(self.vectors)
        except Exception:
            self.index = None  # numpy fallback

    def search(self, query_vecs: np.ndarray, top_k: int) -> list[list[tuple[int, float]]]:
        if self.n == 0:
            return [[] for _ in range(len(query_vecs))]
        q = np.ascontiguousarray(query_vecs.astype(np.float32))
        top_k = min(top_k, self.n)
        if self.index is not None:
            scores, idx = self.index.search(q, top_k)
            return [list(zip(idx[r].tolist(), scores[r].tolist())) for r in range(len(q))]
        # numpy fallback
        sims = q @ self.vectors.T  # (nq, n)
        out = []
        for r in range(sims.shape[0]):
            part = np.argpartition(-sims[r], top_k - 1)[:top_k]
            part = part[np.argsort(-sims[r][part])]
            out.append([(int(i), float(sims[r][i])) for i in part])
        return out


class SparseIndex:
    def __init__(self, texts: list[str]) -> None:
        self.corpus_tokens = [tokenize(t) for t in texts]
        self.n = len(texts)
        self._bm25 = None
        try:
            from rank_bm25 import BM25Okapi
            if self.n:
                self._bm25 = BM25Okapi(self.corpus_tokens)
        except Exception:
            self._bm25 = None  # numpy fallback below

    def search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        if self.n == 0:
            return []
        qtok = tokenize(query)
        if self._bm25 is not None:
            scores = np.asarray(self._bm25.get_scores(qtok))
        else:
            scores = self._bm25_fallback(qtok)
        top_k = min(top_k, self.n)
        part = np.argpartition(-scores, top_k - 1)[:top_k]
        part = part[np.argsort(-scores[part])]
        return [(int(i), float(scores[i])) for i in part]

    def _bm25_fallback(self, qtok: list[str], k1: float = 1.5, b: float = 0.75) -> np.ndarray:
        from collections import Counter
        import math
        doc_len = np.array([len(d) for d in self.corpus_tokens], dtype=np.float32)
        avgdl = float(doc_len.mean()) if self.n else 0.0
        df: dict[str, int] = {}
        counters = [Counter(d) for d in self.corpus_tokens]
        for c in counters:
            for term in c:
                df[term] = df.get(term, 0) + 1
        scores = np.zeros(self.n, dtype=np.float32)
        for term in set(qtok):
            n_q = df.get(term, 0)
            if n_q == 0:
                continue
            idf = math.log(1 + (self.n - n_q + 0.5) / (n_q + 0.5))
            for i, c in enumerate(counters):
                f = c.get(term, 0)
                if f:
                    denom = f + k1 * (1 - b + b * doc_len[i] / (avgdl or 1))
                    scores[i] += idf * (f * (k1 + 1)) / denom
        return scores
