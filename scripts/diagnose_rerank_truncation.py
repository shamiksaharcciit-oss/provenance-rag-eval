"""Measure how much of each indexed unit the cross-encoder could actually see.

Why this matters for the v1.3 verdict: the reranker was configured with `max_length: 512`,
while several conditions index units targeted at 768 tokens (C0/C3 swept to 768; C2/C4/C5 at
768, two of them with a contextual blurb PREPENDED). If a unit exceeds the cross-encoder's
window, its tail is silently dropped before scoring — and a gold span living in that tail is
invisible to the reranker no matter how good the model is.

That would make a KILL verdict ambiguous: "this reranker does not help on this corpus" and
"we truncated the passages we were scoring" predict the same aggregate numbers. This script
separates them by measuring, per condition, the fraction of units exceeding 512 WordPiece
tokens and how much text is lost.

It measures the confound; it does not fix it. Any re-test at a longer window needs a fresh
pre-registered amendment (v1.3 §6, one-shot rule).

    python scripts/diagnose_rerank_truncation.py [--conditions C0,C2,C3,C5] [--track A]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src import config as C  # noqa: E402
from src.chunkers import build_chunker  # noqa: E402
from src.chunkers.base import ChunkContext  # noqa: E402
from src.datasets import load_track_dataset  # noqa: E402
from src.index.embed import Embedder  # noqa: E402
from src.llm.client import build_llm  # noqa: E402
from src.pipeline import build_units  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default="A")
    ap.add_argument("--conditions", default="C0,C1,C2,C3,C4,C5")
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--model", default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    args = ap.parse_args()

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.model)

    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    track_cfg = C.load_track(args.track)
    track_model = track_cfg.get("params", {}).get("llm_model")
    if track_model:
        cfg = C.deep_merge(cfg, {"llm": {"model": track_model}})
    dataset = load_track_dataset(track_cfg, cfg["seed"])
    embedder = Embedder(cfg, cache_root=cfg["_cache_root"])
    ctx = ChunkContext(embedder=embedder, llm=build_llm(cfg), config=cfg)

    # The sizes the run actually used (recorded dev-swept values, matching --no-sweep).
    swept = {"C0": {"chunk_tokens": 768}, "C1": {"max_tokens": 512},
             "C3": {"soft_target_tokens": 768}}

    print(f"Track {args.track} · cross-encoder window = {args.max_length} WordPiece tokens\n")
    print(f"{'cond':6} {'units':>6} {'mean':>7} {'median':>7} {'p90':>7} {'max':>7} "
          f"{'>win':>6} {'%trunc':>7} {'%text lost':>11}")

    for cid in [c.strip() for c in args.conditions.split(",") if c.strip()]:
        cond_cfg = C.load_condition(cid)
        if cid in swept:
            cond_cfg["params"] = {**cond_cfg.get("params", {}), **swept[cid]}
        units = build_units(build_chunker(cond_cfg, ctx), dataset)
        lens = [len(tok.encode(u.text, add_special_tokens=True)) for u in units]
        lens.sort()
        n = len(lens)
        over = [x for x in lens if x > args.max_length]
        total = sum(lens)
        kept = sum(min(x, args.max_length) for x in lens)
        lost_pct = 100.0 * (total - kept) / total if total else 0.0
        print(f"{cid:6} {n:6d} {sum(lens)/n:7.1f} {lens[n//2]:7d} {lens[int(n*0.9)]:7d} "
              f"{lens[-1]:7d} {len(over):6d} {100.0*len(over)/n:7.1f} {lost_pct:11.1f}")

    print("\n%trunc = units exceeding the window (their tail is dropped before scoring)")
    print("%text lost = share of all indexed WordPiece tokens the cross-encoder never saw")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
