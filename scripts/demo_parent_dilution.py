"""Quantify the parent-dilution trap on the REAL corpora (v1.4 review §1a).

Retrieves once, then scores the SAME retrieved children two ways:

  correct  — hits on the child's source_ranges (what the frozen plan mandates)
  broken   — hits on the parent's span (the defect the type split prevents)

The gap between them is the size of the trap: how much recall@5 would silently inflate if a
future refactor started returning parent provenance so the scored unit matched the generator's
context. That number belongs in the evidentiary bundle as the reason the rule exists.

Retrieval is identical in both columns — only the scoring provenance differs — so the
difference isolates the defect rather than confounding it with ranking changes.

    python scripts/demo_parent_dilution.py --track A --child-tokens 128
"""
from __future__ import annotations

import argparse
import json
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
from src.chunkers.base import ChunkContext, Unit  # noqa: E402
from src.datasets import load_track_dataset  # noqa: E402
from src.index.embed import Embedder  # noqa: E402
from src.llm.client import build_llm  # noqa: E402
from src.pipeline import build_units  # noqa: E402
from src.retrieve.retriever import Retriever  # noqa: E402
from src.run import split_dev_test  # noqa: E402
from src.score.metrics import recall_at_k  # noqa: E402
from src.score.provenance import hit_flags  # noqa: E402
from src.smalltobig.chunker import build_children  # noqa: E402

SWEPT = {"C0": {"chunk_tokens": 768}, "C4": {"soft_target_tokens": 768, "chunk_tokens": 768}}


def score(children_ranked: list[Unit], q, min_overlap, containment) -> list[int]:
    return hit_flags(children_ranked, q, variant="any",
                     min_overlap=min_overlap, containment=containment)


def as_parent_scored(children_ranked: list[Unit], parents) -> list[Unit]:
    """The deliberate defect: swap each child's provenance for its parent's span."""
    out = []
    for c in children_ranked:
        p = parents[c.meta["parent_id"]]
        out.append(Unit(unit_id=c.unit_id, text=c.text, doc_id=c.doc_id,
                        source_ranges=[tuple(p.char_span)], meta=c.meta))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default="A")
    ap.add_argument("--conditions", default="C0,C2,C4")
    ap.add_argument("--child-tokens", type=int, default=128)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    cfg["llm"]["provider"] = "anthropic"
    track_cfg = C.load_track(args.track)
    tm = track_cfg.get("params", {}).get("llm_model")
    if tm:
        cfg = C.deep_merge(cfg, {"llm": {"model": tm}})

    dataset = load_track_dataset(track_cfg, cfg["seed"])
    dev_frac = track_cfg.get("params", {}).get("dev_fraction")
    dev_frac = dev_frac if dev_frac is not None else cfg.get("sweep", {}).get("dev_fraction", 0.2)
    _dev, test_q = split_dev_test(dataset, dev_frac, cfg["seed"])
    embedder = Embedder(cfg, cache_root=cfg["_cache_root"])
    ctx = ChunkContext(embedder=embedder, llm=build_llm(cfg), config=cfg)
    sc = cfg.get("scoring", {})
    mo, cont = sc.get("min_overlap_chars", 1), sc.get("strict_containment", 0.5)

    print(f"parent-dilution demo · track {args.track} · child_tokens={args.child_tokens} · "
          f"{len(test_q)} queries · embedder={cfg['embedding']['model']}\n")
    print(f"{'cond':6}{'children':>10}{'parents':>9}{'recall@5 CORRECT':>19}"
          f"{'recall@5 BROKEN':>18}{'inflation':>11}")

    rows = []
    for cid in [c.strip() for c in args.conditions.split(",") if c.strip()]:
        cond_cfg = C.load_condition(cid)
        if cid in SWEPT:
            cond_cfg["params"] = {**cond_cfg.get("params", {}), **SWEPT[cid]}
        parent_units = build_units(build_chunker(cond_cfg, ctx), dataset)
        children, parents = build_children(parent_units, args.child_tokens, cid)

        retr = Retriever(children, embedder, cfg)
        ok = bad = 0
        for q in test_q:
            ranked = retr.retrieve(q.text, args.k)["hybrid"]
            ok += recall_at_k(score(ranked, q, mo, cont), args.k)
            bad += recall_at_k(score(as_parent_scored(ranked, parents), q, mo, cont), args.k)
        n = len(test_q)
        r_ok, r_bad = ok / n, bad / n
        rows.append({"track": args.track, "condition": cid, "child_tokens": args.child_tokens,
                     "n_children": len(children), "n_parents": len(parents),
                     "recall5_child_scored": round(r_ok, 4),
                     "recall5_parent_scored": round(r_bad, 4),
                     "inflation": round(r_bad - r_ok, 4)})
        print(f"{cid:6}{len(children):10d}{len(parents):9d}{r_ok:19.4f}{r_bad:18.4f}"
              f"{r_bad - r_ok:+11.4f}")

    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"\nwrote {args.out}")
    print("\ninflation = how much recall@5 would silently rise if scoring used parent ranges.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
