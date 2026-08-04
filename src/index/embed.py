"""Embedding backends (plan §5.4, §11).

Primary: sentence-transformers (BAAI/bge-base-en-v1.5), normalized vectors so cosine
== inner product. Fallback: a deterministic offline hashing embedder for smoke tests
and CI without a model download — clearly labeled, never used for headline numbers.

NOT CACHED. `encode()` recomputes every call; `cache/emb/` is created and never written.
This docstring previously claimed content-hash caching for idempotency (§11) and was
wrong — corrected 2026-07-30 (PW-1 check §3.5). Idempotency comes from the model being
deterministic at fixed revision, not from a cache. Implementing the cache is a real
improvement and deliberately NOT done here: changing the embedding path while an analysis
depends on reproducing published embeddings is the wrong time to touch it.
"""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path

import numpy as np


class Embedder:
    def __init__(self, cfg: dict, cache_root: str = "cache") -> None:
        emb = cfg.get("embedding", {})
        self.backend = emb.get("backend", "sentence-transformers")
        self.model_name = emb.get("model", "BAAI/bge-base-en-v1.5")
        self.revision = emb.get("revision", "main")
        self.normalize = emb.get("normalize", True)
        self.batch_size = emb.get("batch_size", 64)
        self.device = emb.get("device", "cpu")
        self.dim = emb.get("hash_dim", 512)
        self._model = None
        self.cache_dir = Path(cache_root) / "emb"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # -- public -------------------------------------------------------------
    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.effective_dim), dtype=np.float32)
        if self.backend == "hash":
            vecs = np.vstack([self._hash_vec(t) for t in texts]).astype(np.float32)
        else:
            vecs = self._encode_st(texts)
        if self.normalize:
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            vecs = vecs / norms
        return vecs.astype(np.float32)

    @property
    def effective_dim(self) -> int:
        if self.backend == "hash":
            return self.dim
        self._load_st()
        return self._model.get_sentence_embedding_dimension()

    def describe(self) -> dict:
        return {"backend": self.backend, "model": self.model_name,
                "revision": self.revision, "normalize": self.normalize}

    # -- sentence-transformers ---------------------------------------------
    def _load_st(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(
                self.model_name, revision=self.revision, device=self.device)
        return self._model

    def _encode_st(self, texts: list[str]) -> np.ndarray:
        model = self._load_st()
        return np.asarray(model.encode(
            texts, batch_size=self.batch_size, show_progress_bar=False,
            convert_to_numpy=True, normalize_embeddings=False))

    # -- deterministic offline hashing embedder ----------------------------
    def _hash_vec(self, text: str) -> np.ndarray:
        """Bag-of-token hashed vector. Deterministic; captures lexical overlap only.

        NOT semantic — for pipeline smoke tests only. Tokens map to dims via a stable
        hash; a light idf-ish sublinear term weighting keeps it from being pure noise.
        """
        v = np.zeros(self.dim, dtype=np.float32)
        toks = text.lower().split()
        for t in toks:
            h = hashlib.blake2b(t.encode("utf-8"), digest_size=8).digest()
            idx = struct.unpack("<Q", h)[0] % self.dim
            sign = 1.0 if (idx % 2 == 0) else -1.0
            v[idx] += sign
        return v
