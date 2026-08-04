"""Headroom bound for v1.5: recall@{5,10,50,inf} per condition per track.

Under the parent-scoring redesign the s2b parent inventory is SET-IDENTICAL to the baseline
unit inventory, so small-to-big can only REORDER existing units, never surface a new one. The
addressable pool is therefore `recall@inf - recall@5`, not the old ceiling gap and not
`r@10 - r@5`.

`r@10 - r@5` is the WRONG bound because it assumes reordering is local to an existing
shortlist. Under max-over-children a parent whose whole-unit embedding is diluted — one
relevant passage averaged with ~700 unrelated tokens — can sit at rank 200 under whole-unit
scoring and rank 3 under best-child scoring, because the child carrying that passage is
embedded alone. Nothing confines the movement to the top-10. That dilution-rescue IS the
mechanism.

`recall@inf` is COVERAGE: the fraction of queries whose gold lies in *some* indexed unit. It
needs no retrieval — every unit is checked against every query's gold spans directly — so it
is exact rather than estimated, and cheap.

It also earns its keep independently: **recall@inf < 1 means that condition's pipeline loses
gold outright at any k.** C4 is the one to watch. The formatter edits and deduplicates, and if
a gold span sits in a duplicate whose ranges were NOT absorbed into the canonical unit, it is
unreachable at any k — a genuine treatment defect, invisible in every number reported to date.

Data source: v1.3 test artifacts extended in k, per the admissibility principle that
quantities *bounding* what an experiment could show are admissible pre-data, while quantities
*indicating* what it would show are not. A headroom bound can only shrink or cancel an
experiment, never manufacture a positive.

    python scripts/headroom_bound.py --track A,B --conditions C0,C2,C4
"""
from __future__ import annotations

import argparse
import gc
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
from src.chunkers.base import ChunkContext  # noqa: E402
from src.datasets import load_track_dataset  # noqa: E402
from src.index.embed import Embedder  # noqa: E402
from src.llm.client import build_llm  # noqa: E402
from src.pipeline import build_units  # noqa: E402
from src.retrieve.retriever import Retriever  # noqa: E402
from src.run import NO_SWEEP_PARAMS, split_dev_test  # noqa: E402
from src.score.metrics import recall_at_k  # noqa: E402
from src.score.provenance import hit_flags  # noqa: E402

# Imported from run.py rather than hand-copied (review §4e). A duplicated constant drifted
# once already: overriding only chunk_tokens and leaving overlap_frac at C0.yaml's 0.1 instead
# of --no-sweep's 0.0 measured a C0 the experiment would never run (91 units / r@5 0.722 vs the
# real 90 / 0.790). Importing makes the next drift impossible rather than merely documented.
SWEPT = NO_SWEEP_PARAMS


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default="A,B")
    ap.add_argument("--conditions", default="C0,C2,C4")
    ap.add_argument("--out", default="results_v13/headroom_bound.json")
    args = ap.parse_args()

    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    cfg["llm"]["provider"] = "anthropic"
    sc = cfg.get("scoring", {})
    mo, cont = sc.get("min_overlap_chars", 1), sc.get("strict_containment", 0.5)

    rows = []
    for track in [t.strip() for t in args.track.split(",") if t.strip()]:
        track_cfg = C.load_track(track)
        tm = track_cfg.get("params", {}).get("llm_model")
        tcfg = C.deep_merge(cfg, {"llm": {"model": tm}}) if tm else cfg
        dataset = load_track_dataset(track_cfg, tcfg["seed"])
        dev_frac = track_cfg.get("params", {}).get("dev_fraction")
        dev_frac = dev_frac if dev_frac is not None else tcfg.get("sweep", {}).get("dev_fraction", 0.2)
        _dev, test_q = split_dev_test(dataset, dev_frac, tcfg["seed"])
        embedder = Embedder(tcfg, cache_root=tcfg["_cache_root"])
        ctx = ChunkContext(embedder=embedder, llm=build_llm(tcfg), config=tcfg)

        print(f"\n=== Track {track} · {len(dataset.documents)} docs · {len(test_q)} test queries "
              f"· embedder={tcfg['embedding']['model']} ===")
        print(f"{'cond':6}{'units':>7}{'r@5':>8}{'r@10':>8}{'r@50':>8}{'r@inf':>8}"
              f"{'r10-r5':>9}{'r50-r5':>9}{'rinf-r5':>9}  coverage")
        for cid in [c.strip() for c in args.conditions.split(",") if c.strip()]:
            cond_cfg = C.load_condition(cid)
            if cid in SWEPT:
                cond_cfg["params"] = {**cond_cfg.get("params", {}), **SWEPT[cid]}
            units = build_units(build_chunker(cond_cfg, ctx), dataset)

            # recall@inf = COVERAGE. No retrieval: check every unit against every gold span.
            covered = 0
            for q in test_q:
                flags = hit_flags(units, q, variant="any", min_overlap=mo, containment=cont)
                covered += 1 if any(flags) else 0
            r_inf = covered / len(test_q)

            retr = Retriever(units, embedder, tcfg)
            acc = {5: 0, 10: 0, 50: 0}
            for q in test_q:
                ranked = retr.retrieve(q.text, 50)["hybrid"]
                f = hit_flags(ranked, q, variant="any", min_overlap=mo, containment=cont)
                for k in acc:
                    acc[k] += recall_at_k(f, k)
            n = len(test_q)
            n_units = len(units)
            # Free the FAISS index + embedding matrix before the next condition builds its own.
            # run.py does this between conditions for the same reason; omitting it segfaulted
            # (exit 139) on Track B, whose larger unit sets make the accumulation fatal.
            # NOTE: n_units is captured ABOVE — reading len(units) after the del is a NameError.
            del retr, units
            gc.collect()
            r5, r10, r50 = acc[5] / n, acc[10] / n, acc[50] / n
            flag = "" if r_inf >= 0.999 else "  <-- GOLD LOST AT ANY k"
            print(f"{cid:6}{n_units:7d}{r5:8.3f}{r10:8.3f}{r50:8.3f}{r_inf:8.3f}"
                  f"{r10 - r5:+9.3f}{r50 - r5:+9.3f}{r_inf - r5:+9.3f}{flag}")
            rows.append({"track": track, "condition": cid, "n_units": n_units,
                         "n_queries": n, "recall@5": round(r5, 4), "recall@10": round(r10, 4),
                         "recall@50": round(r50, 4), "recall@inf": round(r_inf, 4),
                         "headroom_r10_minus_r5": round(r10 - r5, 4),
                         "headroom_r50_minus_r5": round(r50 - r5, 4),
                         "headroom_rinf_minus_r5": round(r_inf - r5, 4),
                         "coverage_complete": bool(r_inf >= 0.999)})
    Path(args.out).write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nwrote {args.out}")
    print("\nr@inf = coverage: gold lies in SOME indexed unit. r@inf < 1 means the condition's")
    print("pipeline loses gold outright at any k — a treatment defect, not a ranking problem.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
