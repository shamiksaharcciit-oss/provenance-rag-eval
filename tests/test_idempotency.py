"""Idempotency (plan §11, §12.7): rerunning a (track, condition) reproduces identical
metrics. Uses the deterministic hash embedder so the test needs no model download."""
from __future__ import annotations

from src import config as C
from src.chunkers import build_chunker
from src.chunkers.base import ChunkContext
from src.datasets import track_a_synthetic as ta
from src.index.embed import Embedder
from src.llm.client import build_llm
from src.pipeline import build_units, evaluate


def _cfg():
    cfg = C.load_default()
    cfg["embedding"]["backend"] = "hash"
    return cfg


def _eval_once(cid: str):
    cfg = _cfg()
    ds = ta.load({"params": {"n_docs": 12, "n_queries": 100}}, seed=cfg["seed"])
    embedder = Embedder(cfg, cache_root=cfg["_cache_root"])
    ctx = ChunkContext(embedder=embedder, llm=build_llm(cfg), config=cfg)
    cond = C.load_condition(cid)
    units = build_units(build_chunker(cond, ctx), ds)
    res = evaluate(cid, units, embedder, cfg, ds.queries, len(ds.documents))
    return res.metrics["hybrid"]["any"]["recall_at_k"], res.chunk_stats


def test_recall_reproducible_c0():
    a, sa = _eval_once("C0")
    b, sb = _eval_once("C0")
    assert a == b and sa == sb


def test_recall_reproducible_c3():
    a, sa = _eval_once("C3")
    b, sb = _eval_once("C3")
    assert a == b and sa == sb
