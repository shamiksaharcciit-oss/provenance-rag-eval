"""v1.5 small-to-big runner (M7).

H7: for each X in {C0, C2, C4}, does ranking X's units by BEST-CHILD score improve recall@5
over ranking them by WHOLE-UNIT score, paired over queries?

Both arms deliver the same parent inventory at the same depth, fused at the same level, with
`candidate_pool` denominated in delivered parents. The only difference is the ranking function.

Separate from `run.py` so v1.3's behaviour and published values are untouched.

    python -m src.run_v15 --track A,B --child-tokens 128,256 --out results_v15
"""
from __future__ import annotations

import argparse
import datetime as _dt
import gc
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from src import config as C
from src.chunkers import build_chunker
from src.chunkers.base import ChunkContext
from src.datasets import load_track_dataset
from src.index.embed import Embedder
from src.llm.client import build_llm
from src.pipeline import build_units
from src.retrieve.retriever import Retriever
from src.run import NO_SWEEP_PARAMS, split_dev_test
from src.score.metrics import recall_at_k
from src.score.provenance import hit_flags
from src.smalltobig.chunker import (blurb_dilution, blurb_to_child_ratio, build_children,
                                    child_token_distribution)
from src.smalltobig.retrieve import SmallToBigRetriever, assert_parent_inventory_identity
from src.stats.tests import holm_correction, paired_bootstrap_diff, paired_permutation_p

ROOT = C.ROOT
CONDITIONS = ("C0", "C2", "C4")
K_PRIMARY = 5
K_VALUES = (1, 3, 5, 10)


def _utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT),
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else "no-git"
    except Exception:
        return "no-git"


def evaluate_condition(cid, dataset, test_q, embedder, ctx, cfg, child_tokens, log):
    """Baseline (whole-unit ranking) vs treatment (best-child ranking), same parents."""
    cond_cfg = C.load_condition(cid)
    if cid in NO_SWEEP_PARAMS:
        cond_cfg["params"] = {**cond_cfg.get("params", {}), **NO_SWEEP_PARAMS[cid]}
    parents = build_units(build_chunker(cond_cfg, ctx), dataset)

    blurbs = {u.unit_id: u.meta.get("blurb", "") for u in parents if u.meta.get("blurb")}
    children, parent_index = build_children(parents, child_tokens, cid, blurbs=blurbs or None)
    assert_parent_inventory_identity(parent_index, parents)   # §4 guard, at build time

    sc = cfg.get("scoring", {})
    mo, cont = sc.get("min_overlap_chars", 1), sc.get("strict_containment", 0.5)
    max_k = max(K_VALUES)

    base_r = Retriever(parents, embedder, cfg)
    s2b_r = SmallToBigRetriever(children, parents, embedder, cfg)

    base_vec, s2b_vec = {k: [] for k in K_VALUES}, {k: [] for k in K_VALUES}
    per_query = []
    for q in test_q:
        b_units = base_r.retrieve(q.text, max_k)["hybrid"]
        t_units = s2b_r.retrieve_parents(q.text, max_k)["hybrid"]
        bf = hit_flags(b_units, q, variant="any", min_overlap=mo, containment=cont)
        tf = hit_flags(t_units, q, variant="any", min_overlap=mo, containment=cont)
        for k in K_VALUES:
            base_vec[k].append(recall_at_k(bf, k))
            s2b_vec[k].append(recall_at_k(tf, k))
        per_query.append({
            "query_id": q.query_id, "condition": cid, "child_tokens": child_tokens,
            "baseline_hit@k": {str(k): recall_at_k(bf, k) for k in K_VALUES},
            "s2b_hit@k": {str(k): recall_at_k(tf, k) for k in K_VALUES},
            "baseline_top": [u.unit_id for u in b_units[:K_PRIMARY]],
            "s2b_top": [u.unit_id for u in t_units[:K_PRIMARY]],
        })

    cpp = s2b_r.children_per_parent()
    counts = sorted(cpp.values())
    diag = {
        "n_parents": len(parents), "n_children": len(children),
        "child_token_distribution": child_token_distribution(children),
        "blurb_to_child_ratio": blurb_to_child_ratio(children),   # mean-of-ratios; see below
        "blurb_dilution": blurb_dilution(children),               # corrected diagnostic
        "children_per_parent": {
            "mean": round(sum(counts) / len(counts), 2) if counts else 0,
            "median": counts[len(counts) // 2] if counts else 0,
            "min": counts[0] if counts else 0, "max": counts[-1] if counts else 0,
        },
        "children_without_provenance": sum(
            1 for c in children if not c.meta.get("provenance_derivable")),
    }
    n = len(test_q)
    log(f"    {cid} @{child_tokens}: base r@5={sum(base_vec[5])/n:.4f}  "
        f"s2b r@5={sum(s2b_vec[5])/n:.4f}  "
        f"({sum(s2b_vec[5])/n - sum(base_vec[5])/n:+.4f})  "
        f"children={len(children)} per-parent~{diag['children_per_parent']['mean']}")
    del base_r, s2b_r, children
    gc.collect()
    return {"condition": cid, "child_tokens": child_tokens, "n_queries": n,
            "baseline": {str(k): round(sum(base_vec[k]) / n, 4) for k in K_VALUES},
            "s2b": {str(k): round(sum(s2b_vec[k]) / n, 4) for k in K_VALUES},
            "diagnostics": diag, "_vectors": {"base": base_vec[K_PRIMARY],
                                              "s2b": s2b_vec[K_PRIMARY]}}, per_query


def _persist(out_dir: Path, run_id: str, cfg: dict, rows: list, per_query: list) -> None:
    """Write results.json + per_query.jsonl after every condition, not just at the end."""
    payload = {"run_id": run_id, "created_utc": _utc(), "git_commit": _git(),
               "experiment": "v1.5-small-to-big",
               "preregistration": "preregistration_v15.json",
               "environment": {"embedding_model": cfg["embedding"]["model"],
                               "embedding_revision": cfg["embedding"].get("revision"),
                               "seed": cfg["seed"],
                               "candidate_pool": cfg["index"]["candidate_pool"],
                               "k_rrf": cfg["index"]["k_rrf"]},
               "holm_family": "all six tests (3 conditions x 2 child sizes) as ONE family",
               "partial": True,
               "results": [{k: v for k, v in r.items() if k != "_vectors"} for r in rows]}
    (out_dir / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with open(out_dir / "per_query.jsonl", "w", encoding="utf-8") as f:
        for r in per_query:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # Vectors kept separately so statistics can be recomputed from a partial run.
    (out_dir / "vectors.json").write_text(
        json.dumps([{"track": r.get("track"), "condition": r["condition"],
                     "child_tokens": r["child_tokens"], **r.get("_vectors", {})}
                    for r in rows if r.get("_vectors")], indent=2), encoding="utf-8")


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            try:
                s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default="A,B")
    ap.add_argument("--child-tokens", default="128,256")
    ap.add_argument("--conditions", default="C0,C2,C4")
    ap.add_argument("--out", default="results_v15")
    args = ap.parse_args(argv)

    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = "run-" + _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    log = lambda m: print(m, flush=True)

    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    cfg["llm"]["provider"] = "anthropic"
    st = cfg.get("stats", {})
    iters, seed, ci = st.get("bootstrap_iters", 10000), cfg["seed"], st.get("ci", 0.95)
    sizes = [int(x) for x in args.child_tokens.split(",") if x.strip()]
    conds = [c.strip() for c in args.conditions.split(",") if c.strip()]

    log(f"v1.5 small-to-big · run_id={run_id} · sizes={sizes} · embedder={cfg['embedding']['model']}")
    rows, all_pq = [], []
    for track in [t.strip() for t in args.track.split(",") if t.strip()]:
        tcfg_raw = C.load_track(track)
        tm = tcfg_raw.get("params", {}).get("llm_model")
        tcfg = C.deep_merge(cfg, {"llm": {"model": tm}}) if tm else cfg
        dataset = load_track_dataset(tcfg_raw, tcfg["seed"])
        dev_frac = tcfg_raw.get("params", {}).get("dev_fraction")
        dev_frac = dev_frac if dev_frac is not None else tcfg.get("sweep", {}).get("dev_fraction", 0.2)
        _dev, test_q = split_dev_test(dataset, dev_frac, tcfg["seed"])
        embedder = Embedder(tcfg, cache_root=tcfg["_cache_root"])
        ctx = ChunkContext(embedder=embedder, llm=build_llm(tcfg), config=tcfg)
        log(f"\n== Track {track} == {len(dataset.documents)} docs, {len(test_q)} test queries")
        for ctok in sizes:
            for cid in conds:
                try:
                    row, pq = evaluate_condition(cid, dataset, test_q, embedder, ctx, tcfg,
                                                 ctok, log)
                except Exception as e:
                    log(f"    {cid} @{ctok} FAILED -> {type(e).__name__}: {str(e)[:200]}")
                    continue
                row["track"] = track
                rows.append(row)
                all_pq.extend({"track": track, **r} for r in pq)
                # Persist IMMEDIATELY. Writing only at the end lost six completed Track A
                # conditions to a Track B segfault — template §A2: a cheap downstream step
                # must never destroy an expensive completed result. Each condition is
                # ~10 minutes of embedding; losing one is acceptable, losing six is not.
                _persist(out_dir, run_id, cfg, rows, all_pq)
            gc.collect()

    # ---- H7 statistics: Holm over ALL SIX tests (3 conditions x 2 sizes) as ONE family ----
    log("\n== H7 (Holm over all six: 3 conditions x 2 child sizes, one family) ==")
    for track in sorted({r["track"] for r in rows}):
        fam = [r for r in rows if r["track"] == track]
        pvals, stats = [], []
        for r in fam:
            a, b = r["_vectors"]["s2b"], r["_vectors"]["base"]
            d = paired_bootstrap_diff(a, b, iters, seed, ci)
            p = paired_permutation_p(a, b, iters, seed)
            pvals.append(p)
            stats.append({"track": track, "condition": r["condition"],
                          "child_tokens": r["child_tokens"], "metric": "recall@5",
                          "baseline": r["baseline"]["5"], "s2b": r["s2b"]["5"],
                          "mean_diff": round(d["mean_diff"], 4),
                          "ci95": [round(x, 4) for x in d["ci95"]],
                          "p_value": round(p, 5), "significant": d["significant_ci"]})
        if pvals:
            for s_, pa in zip(stats, holm_correction(pvals)):
                s_["p_holm"] = round(pa, 5)
        for s_ in stats:
            log(f"  {s_['track']} {s_['condition']}@{s_['child_tokens']}: "
                f"{s_['baseline']:.4f} -> {s_['s2b']:.4f}  {s_['mean_diff']:+.4f}  "
                f"CI[{s_['ci95'][0]:+.4f},{s_['ci95'][1]:+.4f}]  "
                f"p={s_['p_value']:.4f} holm={s_.get('p_holm', float('nan')):.4f}  "
                f"{'SIG' if s_['significant'] else 'n.s.'}")
        for r in fam:
            r.pop("_vectors", None)
        rows_out = [r for r in rows]
        (out_dir / f"h7_stats_{track}.json").write_text(json.dumps(stats, indent=2),
                                                        encoding="utf-8")

    for r in rows:
        r.pop("_vectors", None)
    payload = {"run_id": run_id, "created_utc": _utc(), "git_commit": _git(),
               "experiment": "v1.5-small-to-big",
               "preregistration": "preregistration_v15.json",
               "environment": {"embedding_model": cfg["embedding"]["model"],
                               "embedding_revision": cfg["embedding"].get("revision"),
                               "seed": cfg["seed"],
                               "candidate_pool": cfg["index"]["candidate_pool"],
                               "k_rrf": cfg["index"]["k_rrf"]},
               "holm_family": "all six tests (3 conditions x 2 child sizes) as ONE family",
               "results": rows}
    (out_dir / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with open(out_dir / "per_query.jsonl", "w", encoding="utf-8") as f:
        for r in all_pq:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log(f"\nartifacts -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
