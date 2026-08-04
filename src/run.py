"""CLI entrypoint: run the retrieval-evaluation experiment (plan §0, §10, §12, §14).

Usage:
  python -m src.run --track A                 # full run for a track
  python -m src.run --track A --provider none --smoke   # zero-cost pipeline smoke
  python -m src.run --report-only             # rebuild figures/report from last run
"""
from __future__ import annotations

import argparse
import datetime as _dt
import gc
import hashlib
import json
import random
import os
import subprocess
import sys
from pathlib import Path

# Memory / native-runtime guards, set BEFORE the faiss/torch import chain below.
# faiss-cpu and torch both bundle an OpenMP runtime; on Windows the duplicate load can
# hard-abort (exit 5). Pinning one thread also curbs peak RAM on small hosts.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from src import config as C
from src.chunkers import build_chunker
from src.chunkers.base import ChunkContext
from src.chunkers.formatter import FormatterChunker
from src.datasets import load_track_dataset
from src.datasets.base import Dataset
from src.index.embed import Embedder
from src.judge.rubric import faithfulness_eval, readability_eval
from src.llm.client import build_llm
from src.pipeline import EvalResult, build_units, evaluate
from src.rerank import build_reranker
from src.stats.tests import holm_correction, paired_bootstrap_diff, paired_permutation_p

ROOT = C.ROOT
RESULTS = ROOT / "results"

# Dev-sweep winners, applied by --no-sweep. Single definition: analysis scripts
# import this rather than hand-copying it (a duplicate drifted once).
NO_SWEEP_PARAMS = {"C0": {"chunk_tokens": 768, "overlap_frac": 0.0},
                   "C1": {"max_tokens": 512},
                   "C3": {"soft_target_tokens": 768}}

# Pre-registered success / kill criteria (plan §2.4) — frozen verbatim.
PREREG_CRITERIA = {
    "plan_version": "1.1",
    "supersedes": "run-20260723-223653 (v1.0, Track A, PARTIAL)",
    "validate_if": ("C3 recall@5 >= C2 (within CI or better) on >=2 tracks AND H2 AND H3"),
    "complement_if": ("H4 holds on Track B (C5>C2, paired CI excludes 0 after Holm) and "
                      "directionally on Track A; may be reported alongside any verdict"),
    "partial_if": ("parity with C2 plus a SIGNIFICANT win over C0 or C1 (state which, "
                   "changelog-8), AND H2, AND H3-objective"),
    "kill_if": ("treatment only beats the naive floor (not semantic), OR H2 fails "
                "(vocabulary drift), OR H3 fails (readability lost -> propositionization)"),
    "hypotheses": {
        "H1": "C3 recall@k >= C2, and > C1 > C0 at k in {1,3,5,10}",
        "H2": "C3 (and C4/C5) hybrid recall@k not reduced vs dense (no vocab drift)",
        "H3": "C3 single output rated as readable or better than source; assessed on Track B "
              "real prose (Track A rubric floors; objective preserved-term check is A's signal)",
        "H4": "C5 (formatted+contextual) recall@5 > C2 (contextual alone), CI excludes 0 after "
              "Holm; secondary C4 (formatted+naive) > C0 (naive alone)",
    },
    "preregistered_expectation": "de-duplication is neutral-to-negative for recall "
                                 "(redundancy is robustness); a negative dedup ablation is expected",
    "prose_rule": "any 'beats' claim must be backed by a significant pairwise test "
                  "(CI excluding 0 after Holm) — changelog-8",
}


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT),
                             capture_output=True, text=True, timeout=5)
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return "no-git"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# dev/test split and per-condition fairness sweep (§5.3)
# --------------------------------------------------------------------------
def split_dev_test(dataset: Dataset, dev_fraction: float, seed: int):
    qs = list(dataset.queries)
    random.Random(seed * 7 + 1).shuffle(qs)
    n_dev = max(1, int(round(len(qs) * dev_fraction))) if dev_fraction > 0 else 0
    return qs[:n_dev], qs[n_dev:]


def _dev_recall5(cond_cfg: dict, dataset: Dataset, embedder: Embedder, cfg: dict,
                 dev_queries, ctx: ChunkContext) -> float:
    chunker = build_chunker(cond_cfg, ctx)
    units = build_units(chunker, dataset)
    res = evaluate(cond_cfg["id"], units, embedder, cfg, dev_queries, len(dataset.documents))
    return res.metrics["hybrid"]["any"]["recall_at_k"].get(5, 0.0)


def sweep_condition(cond_id: str, base_cfg: dict, dataset: Dataset, embedder: Embedder,
                    cfg: dict, dev_queries, ctx: ChunkContext, log) -> dict:
    """Return the best params for a baseline/treatment by dev recall@5 (§5.3)."""
    sweep = cfg.get("sweep", {})
    candidates: list[dict] = []
    if cond_id == "C0":
        for ct in sweep.get("baseline_chunk_tokens", [384]):
            for ov in sweep.get("baseline_overlap_frac", [0.1]):
                candidates.append({"chunk_tokens": ct, "overlap_frac": ov})
    elif cond_id == "C1":
        for mt in sweep.get("baseline_chunk_tokens", [512]):
            candidates.append({"max_tokens": mt})
    elif cond_id == "C3":
        for st in sweep.get("formatter_soft_target", [384]):
            candidates.append({"soft_target_tokens": st})
    else:
        return dict(base_cfg.get("params", {}))

    best, best_score = None, -1.0
    for cand in candidates:
        trial = json.loads(json.dumps(base_cfg))
        trial["params"] = {**trial.get("params", {}), **cand}
        score = _dev_recall5(trial, dataset, embedder, cfg, dev_queries, ctx)
        log(f"    sweep {cond_id} {cand} -> dev recall@5={score:.3f}")
        if score > best_score:
            best, best_score = cand, score
        gc.collect()  # release per-candidate vectors/FAISS index before the next build
    merged = {**base_cfg.get("params", {}), **(best or {})}
    return merged


# --------------------------------------------------------------------------
# main experiment
# --------------------------------------------------------------------------
def run_track(track_id: str, cfg: dict, args, log) -> dict | None:
    seed = cfg["seed"]
    track_cfg = C.load_track(track_id)
    try:
        dataset = load_track_dataset(track_cfg, seed)
    except Exception as e:
        _append_blocker(f"Track {track_id}: {type(e).__name__}: {e}")
        log(f"  Track {track_id} unavailable -> recorded in BLOCKERS.md ({e})")
        return None

    log(f"  Track {track_id}: {len(dataset.documents)} docs, {len(dataset.queries)} queries "
        f"({dataset.meta.get('dataset', 'synthetic')})")

    # Per-track LLM model override (v1.1): keeps Track A on its cached model (Opus) while
    # a different, cheaper model (e.g. Sonnet) runs the all-fresh Track B. Cache keys
    # include the model, so this preserves Track A cache reuse.
    track_model = track_cfg.get("params", {}).get("llm_model")
    cfg_track = C.deep_merge(cfg, {"llm": {"model": track_model}}) if track_model else cfg
    if track_model:
        log(f"  Track {track_id} LLM model override -> {track_model}")

    embedder = Embedder(cfg_track, cache_root=cfg["_cache_root"])
    llm = build_llm(cfg_track)
    ctx = ChunkContext(embedder=embedder, llm=llm, config=cfg_track)
    cfg = cfg_track  # use the track-resolved config downstream

    # Per-track dev fraction: Track A keeps 0.2 (reproduces v1.0's 176-query test set);
    # Track B sets 0.0 so all 150 queries are used for the test (no sweep on B).
    track_dev = track_cfg.get("params", {}).get("dev_fraction")
    dev_frac = (0.0 if args.smoke else
                (track_dev if track_dev is not None
                 else cfg.get("sweep", {}).get("dev_fraction", 0.2)))
    dev_q, test_q = split_dev_test(dataset, dev_frac, seed)
    log(f"  split: {len(dev_q)} dev / {len(test_q)} test queries")

    cond_ids = args.conditions or C.all_condition_ids()

    # 1) Fairness sweep on dev for the tunable conditions (skipped in smoke).
    # Sweeps select chunk SIZES only and must not spend on the LLM: the C3 soft-target
    # sweep uses a rule-based (none-provider) formatter context; the final C3 evaluation
    # below uses the real LLM. C0/C1 sweeps involve no LLM anyway.
    from src.llm.client import LLMClient
    sweep_ctx = ChunkContext(
        embedder=embedder,
        llm=LLMClient(provider="none", cache_dir=Path(cfg["_cache_root"]) / "llm"),
        config=cfg,
    )
    chosen_params: dict[str, dict] = {}
    chosen_sizes: dict[str, int] = {}
    if getattr(args, "no_sweep", False):
        # Use sizes selected by a prior dev sweep (recorded, not re-derived live). Avoids
        # the memory-heavy repeated-embedding loop; sizes below are the dev-sweep winners.
        chosen_params = dict(NO_SWEEP_PARAMS)
        chosen_sizes = {"C0": 768, "C1": 512, "C3": 768}
        log(f"  --no-sweep: using recorded dev-swept sizes {chosen_sizes}")
    elif not args.smoke and dev_q:
        for cid in ["C0", "C1", "C3"]:
            if cid in cond_ids:
                base = C.load_condition(cid)
                chosen_params[cid] = sweep_condition(cid, base, dataset, embedder, cfg,
                                                     dev_q, sweep_ctx, log)
        chosen_sizes = {
            "C0": chosen_params.get("C0", {}).get("chunk_tokens", 384),
            "C1": chosen_params.get("C1", {}).get("max_tokens", 512),
            "C3": chosen_params.get("C3", {}).get("soft_target_tokens", 384),
        }
    else:
        chosen_sizes = {"C0": 384, "C1": 512, "C3": 384}

    # Reranking axis (v1.3 M6). None unless rerank.enabled — with it off, every number
    # below reproduces the pre-v1.3 run exactly.
    reranker = build_reranker(cfg)
    if reranker is not None:
        log(f"  rerank ON: {reranker.describe()}")

    # 2) Evaluate every condition on the TEST split.
    results: dict[str, EvalResult] = {}
    formatted_docs: dict[str, list] = {}
    for cid in cond_ids:
        cond_cfg = C.load_condition(cid)
        # apply swept params (ablations inherit C3's chosen soft_target)
        if cid in chosen_params:
            cond_cfg["params"] = {**cond_cfg.get("params", {}), **chosen_params[cid]}
        elif cid.startswith("C3-"):
            st = chosen_sizes.get("C3", 384)
            cond_cfg["params"] = {**cond_cfg.get("params", {}), "soft_target_tokens": st}
        chunker = build_chunker(cond_cfg, ctx)
        import time as _t
        _cost_before = llm.snapshot()
        _c0 = _t.time()
        units = build_units(chunker, dataset)
        format_seconds = _t.time() - _c0
        res = evaluate(cid, units, embedder, cfg, test_q, len(dataset.documents),
                       reranker=reranker)
        res.format_seconds = format_seconds
        res.llm_cost = llm.delta(_cost_before, llm.snapshot())  # per-condition (§5.3)
        results[cid] = res
        r5 = res.metrics["hybrid"]["any"]["recall_at_k"].get(5, 0.0)
        rr_note = ""
        if reranker is not None:
            rr5 = res.metrics["hybrid_rerank"]["any"]["recall_at_k"].get(5, 0.0)
            rr_note = f"  +rerank={rr5:.3f} ({rr5 - r5:+.3f})"
        log(f"    {cid}: recall@5(hybrid,any)={r5:.3f}{rr_note}"
            f"  units={res.chunk_stats['index_units']}"
            f"  llm(fresh/cached)={res.llm_cost['fresh_calls']}/{res.llm_cost['cached_calls']}")
        gc.collect()

    # 2b) Cost self-check (§5.3): C2/C3/C5 MUST show some LLM usage (fresh or cached).
    for cid in ("C2", "C3", "C5"):
        if cid in results:
            c = results[cid].llm_cost
            if (c.get("fresh_calls", 0) + c.get("cached_calls", 0)) == 0 and not llm.is_none:
                raise RuntimeError(
                    f"cost self-check failed: {cid} reported zero LLM usage "
                    f"(fresh+cached=0) with provider={llm.provider}")

    # 2c) Common-size control (§5.2): naive@256 on ORIGINAL vs FORMATTED corpus.
    common_size = _common_size_control(dataset, embedder, cfg, test_q, ctx, log)

    # 3) Stats: pairwise C3 vs baselines on recall@5 (hybrid, any) (§8).
    pairwise = _pairwise_stats(track_id, results, cfg)

    # 3b) H6 rerank main effect + interaction (amendment v1.3). Empty when the axis is off.
    rerank_stats = _rerank_stats(track_id, results, cfg) if reranker is not None else {}

    # 4) Ablation contributions (§9).
    ablations = _ablation_contributions(track_id, results)

    # 5) Judges: faithfulness (subset) + readability H3 (§7.6, §7.8).
    # The judges are SECONDARY diagnostics that need live LLM calls. A judge failure — a
    # missing API key, an uncached prompt, a rate limit — must not destroy the retrieval
    # results, which are the expensive primary artifact and are already computed by this
    # point. Previously an uncached judge prompt aborted the whole run and lost ~50 minutes
    # of reranked retrieval with nothing written to disk.
    def _judge(name, fn, *a):
        try:
            return fn(*a)
        except Exception as e:
            msg = f"{type(e).__name__}: {str(e)[:160]}"
            log(f"    {name} judge unavailable -> {msg} (retrieval results retained)")
            _append_blocker(f"Track {track_id}: {name} judge skipped -> {msg}")
            return {"error": msg, "skipped": True}

    faith = _judge("faithfulness", _faithfulness, results, dataset, test_q, llm, cfg)
    read = _judge("readability", _readability, dataset, ctx, cfg, llm)

    return {
        "track": track_id,
        "dataset": dataset,
        "results": results,
        "chosen_sizes": chosen_sizes,
        "pairwise": pairwise,
        "rerank_stats": rerank_stats,
        "rerank": (reranker.describe() if reranker is not None else {}),
        "ablations": ablations,
        "faithfulness": faith,
        "readability": read,
        "llm_cost": llm.cost_summary(),
        "common_size": common_size,
        "embedder": embedder.describe(),
        "llm_model": cfg.get("llm", {}).get("model", ""),
        "n_test": len(test_q),
    }


def _common_size_control(dataset, embedder, cfg, test_q, ctx, log) -> dict:
    """Recall@5 with naive 256-token chunks on the ORIGINAL vs FORMATTED corpus (§5.2).

    Isolates text-quality effects (formatting) from unit-count effects. The formatter
    pass reuses cache, so this adds no LLM spend beyond re-chunking.
    """
    out = {}
    try:
        orig = build_chunker({"id": "orig256", "chunker": "naive",
                              "params": {"chunk_tokens": 256, "overlap_frac": 0.0}}, ctx)
        r = evaluate("orig256", build_units(orig, dataset), embedder, cfg, test_q,
                     len(dataset.documents))
        out["original_256"] = round(r.metrics["hybrid"]["any"]["recall_at_k"].get(5, 0.0), 4)
        gc.collect()
        fmt = build_chunker({"id": "fmt256", "chunker": "formatted_naive",
                             "params": {"chunk_tokens": 256, "overlap_frac": 0.0,
                                        "reference_resolution": True, "dedup": True,
                                        "right_size": True, "soft_target_tokens": 384}}, ctx)
        r = evaluate("fmt256", build_units(fmt, dataset), embedder, cfg, test_q,
                     len(dataset.documents))
        out["formatted_256"] = round(r.metrics["hybrid"]["any"]["recall_at_k"].get(5, 0.0), 4)
        gc.collect()
    except Exception as e:
        log(f"    common-size control skipped: {e}")
        out["error"] = str(e)[:120]
        return out
    # Reporting sits OUTSIDE the computation guard: a formatting or console failure must not
    # discard a control that already ran.
    try:
        log(f"    common-size@256: original={out['original_256']:.3f} "
            f"formatted={out['formatted_256']:.3f} "
            f"(delta={out['formatted_256'] - out['original_256']:+.3f})")
    except Exception:
        pass
    return out


def _pairwise_stats(track_id: str, results: dict[str, EvalResult], cfg: dict) -> list[dict]:
    st = cfg.get("stats", {})
    iters = st.get("bootstrap_iters", 10000)
    piters = st.get("permutation_iters", 10000)
    seed = cfg["seed"]
    out: list[dict] = []

    def vec(cid):
        return (results[cid].metrics["hybrid"]["any"]["_per_query"]["recall_at_k"].get(5, [])
                if cid in results else None)

    # C3 vs baselines + the v1.1 composition/complementarity pairs (§6).
    pairs = [("C3", "C2"), ("C3", "C1"), ("C3", "C0"),
             ("C5", "C2"), ("C4", "C0"), ("C5", "C3")]  # H4: C5>C2, C4>C0
    pvals: list[float] = []
    for a, b in pairs:
        av, bv = vec(a), vec(b)
        if av is None or bv is None or len(av) != len(bv) or not av:
            continue
        diff = paired_bootstrap_diff(av, bv, iters, seed, st.get("ci", 0.95))
        p = paired_permutation_p(av, bv, piters, seed)
        pvals.append(p)
        out.append({"track": track_id, "pair": f"{a}_vs_{b}", "metric": "recall@5",
                    "mean_diff": round(diff["mean_diff"], 4), "ci95": [round(x, 4) for x in diff["ci95"]],
                    "p_value": round(p, 5), "significant": diff["significant_ci"]})
    if st.get("holm_correction", True) and pvals:
        adj = holm_correction(pvals)
        for row, pa in zip(out, adj):
            row["p_holm"] = round(pa, 5)
    return out


def _did_reading(did: float, significant: bool, gain_c0: float, gain_c3: float) -> str:
    """Plain-English reading of the difference-in-differences.

    The sign of the DiD alone does NOT determine the story: it must be read against the sign
    of the two component gains. An earlier version labelled any positive DiD
    "super-additive — the two compound (complements)", which is flatly wrong when BOTH gains
    are negative — there a positive DiD means the formatter *reduces the harm*, not that two
    benefits compound.
    """
    if not significant:
        return "no detectable interaction (additive within CI)"
    both_positive = gain_c0 > 0 and gain_c3 > 0
    both_negative = gain_c0 < 0 and gain_c3 < 0
    if both_positive:
        return ("super-additive — the two gains compound (complements)" if did > 0
                else "sub-additive — the reranker closes part of the same gap the formatter "
                     "closes (substitutes)")
    if both_negative:
        return ("the formatter REDUCES the reranker's harm — reranking costs less on the "
                "formatted corpus than on the naive one (both effects are negative)" if did > 0
                else "the formatter AMPLIFIES the reranker's harm (both effects are negative)")
    return (f"mixed signs — rerank gain on C0={gain_c0:+.4f}, on C3={gain_c3:+.4f}; "
            f"DiD={did:+.4f}. Read the component gains directly rather than the DiD label.")


def _rerank_stats(track_id: str, results: dict[str, EvalResult], cfg: dict) -> dict:
    """H6 (amendment v1.3): does reranking help, and does its gain stack with the formatter's?

    Two families, Holm-corrected SEPARATELY from the H1-H4 pairwise family — these test a
    different hypothesis and folding them into one correction would change the significance
    of already-reported v1.1 results.

      main effect  : per condition X, (X + rerank) vs X on recall@5, paired over queries
      interaction  : difference-in-differences, (C3+rr - C3) - (C0+rr - C0)

    The DiD is the part that matters for the composition story. ~0 means the two fixes are
    additive; clearly negative means the reranker closes some of the same gap the formatter
    closes — i.e. they are substitutes, not complements. Reported either way.
    """
    st = cfg.get("stats", {})
    iters = st.get("bootstrap_iters", 10000)
    piters = st.get("permutation_iters", 10000)
    seed = cfg["seed"]
    ci = st.get("ci", 0.95)

    def vec(cid: str, ranking: str):
        r = results.get(cid)
        if r is None or ranking not in r.metrics:
            return None
        return r.metrics[ranking]["any"]["_per_query"]["recall_at_k"].get(5, [])

    # Holm family = the PRIMARY conditions only. The pre-registered decision rule references
    # C0 and C3; the C3-* ablations and C4i are diagnostics, not decision-bearing. Folding all
    # ~11 into one correction would be needlessly conservative and could manufacture a KILL
    # from family size rather than from evidence. Ablations are still reported, marked
    # exploratory and uncorrected. Fixed before any result was observed (see v1.3 addendum).
    PRIMARY = ("C0", "C1", "C2", "C3", "C4", "C5")

    main: list[dict] = []
    pvals: list[float] = []
    for cid in sorted(results):
        base, rr = vec(cid, "hybrid"), vec(cid, "hybrid_rerank")
        if not base or not rr or len(base) != len(rr):
            continue
        d = paired_bootstrap_diff(rr, base, iters, seed, ci)
        p = paired_permutation_p(rr, base, piters, seed)
        is_primary = cid in PRIMARY
        row = {
            "track": track_id, "condition": cid, "comparison": f"{cid}+rerank_vs_{cid}",
            "metric": "recall@5",
            "family": "primary" if is_primary else "exploratory",
            "decision_bearing": is_primary,
            "base": round(sum(base) / len(base), 4),
            "reranked": round(sum(rr) / len(rr), 4),
            "mean_diff": round(d["mean_diff"], 4),
            "ci95": [round(x, 4) for x in d["ci95"]],
            "p_value": round(p, 5),
            "significant": d["significant_ci"],
        }
        if is_primary:
            pvals.append(p)
        main.append(row)
    if st.get("holm_correction", True) and pvals:
        primary_rows = [r for r in main if r["decision_bearing"]]
        for row, pa in zip(primary_rows, holm_correction(pvals)):
            row["p_holm"] = round(pa, 5)

    interaction: dict = {}
    c3, c3rr = vec("C3", "hybrid"), vec("C3", "hybrid_rerank")
    c0, c0rr = vec("C0", "hybrid"), vec("C0", "hybrid_rerank")
    if all(v for v in (c3, c3rr, c0, c0rr)) and len({len(c3), len(c3rr), len(c0), len(c0rr)}) == 1:
        did = [(a - b) - (c - d) for a, b, c, d in zip(c3rr, c3, c0rr, c0)]
        zeros = [0.0] * len(did)
        d = paired_bootstrap_diff(did, zeros, iters, seed, ci)
        p = paired_permutation_p(did, zeros, piters, seed)
        formatter_gain = sum(a - b for a, b in zip(c3, c0)) / len(c3)
        interaction = {
            "track": track_id,
            "quantity": "(C3+rerank - C3) - (C0+rerank - C0)",
            "formatter_gain_c3_vs_c0": round(formatter_gain, 4),
            "rerank_gain_on_c0": round(sum(a - b for a, b in zip(c0rr, c0)) / len(c0), 4),
            "rerank_gain_on_c3": round(sum(a - b for a, b in zip(c3rr, c3)) / len(c3), 4),
            "did": round(d["mean_diff"], 4),
            "ci95": [round(x, 4) for x in d["ci95"]],
            "p_value": round(p, 5),
            "significant": d["significant_ci"],
            "reading": _did_reading(
                did=d["mean_diff"],
                significant=d["significant_ci"],
                gain_c0=sum(a - b for a, b in zip(c0rr, c0)) / len(c0),
                gain_c3=sum(a - b for a, b in zip(c3rr, c3)) / len(c3),
            ),
        }
        # Does reranking alone match what the formatter buys? Directly relevant to the
        # composition story: a cheap query-side fix reaching a corpus-side fix's result.
        d2 = paired_bootstrap_diff(c0rr, c3, iters, seed, ci)
        interaction["c0_plus_rerank_vs_c3"] = {
            "mean_diff": round(d2["mean_diff"], 4),
            "ci95": [round(x, 4) for x in d2["ci95"]],
            "significant": d2["significant_ci"],
        }

    return {"main_effect": main, "interaction": interaction}


def _ablation_contributions(track_id: str, results: dict[str, EvalResult]) -> list[dict]:
    if "C3" not in results:
        return []
    def r5(cid):
        return results[cid].metrics["hybrid"]["any"]["recall_at_k"].get(5, 0.0) if cid in results else None
    c3 = r5("C3")
    mapping = {"reference_resolution": "C3-noref", "right_sizing": "C3-nosize",
               "de_duplication": "C3-nodedup", "text_editing_vs_markers": "C3-markeronly"}
    out = []
    for op, cid in mapping.items():
        ab = r5(cid)
        if ab is not None and c3 is not None:
            out.append({"track": track_id, "operation": op,
                        "delta_recall@5": round(c3 - ab, 4)})
    return out


def _faithfulness(results, dataset, test_q, llm, cfg) -> dict:
    n = cfg.get("judge", {}).get("faithfulness_n", 50)
    if "C3" not in results:
        return {"n": 0, "score_mean": 0.0}
    ctxs = results["C3"].contexts
    ans = {q.query_id: q for q in test_q}
    items = []
    for qid, q in ans.items():
        items.append({"query_id": qid, "question": q.text, "answer": q.answer,
                      "contexts": ctxs.get(qid, [])})
    per_cond = {}
    for cid in ["C0", "C1", "C2", "C3", "C4", "C5"]:
        if cid in results:
            c_items = [{"query_id": qid, "question": ans[qid].text, "answer": ans[qid].answer,
                        "contexts": results[cid].contexts.get(qid, [])} for qid in ans]
            per_cond[cid] = faithfulness_eval(c_items, llm, n, cfg["seed"])
    main = per_cond.get("C3", faithfulness_eval(items, llm, n, cfg["seed"]))
    main["by_condition"] = {k: round(v["score_mean"], 4) for k, v in per_cond.items()}
    return main


def _readability(dataset, ctx, cfg, llm) -> dict:
    n = cfg.get("judge", {}).get("readability_n_docs", 20)
    fmt = FormatterChunker(C.load_condition("C3").get("params", {}), ctx)
    pairs = []
    for doc in dataset.documents[:n]:
        units = fmt.chunk(doc)
        formatted = "\n\n".join(u.text for u in units)
        pairs.append({"doc_id": doc.doc_id, "original": doc.text, "formatted": formatted})
    return readability_eval(pairs, llm, n)


# --------------------------------------------------------------------------
# verdict (§2.4)
# --------------------------------------------------------------------------
def compute_verdict(track_bundles: list[dict]) -> dict:
    per_track = {}
    validate_tracks = 0
    beats_semantic_tracks = 0
    complement_tracks = 0
    h2_all, h3_all = True, True
    for tb in track_bundles:
        res = tb["results"]
        def r5(cid):
            return res[cid].metrics["hybrid"]["any"]["recall_at_k"].get(5, 0.0) if cid in res else None

        # significant, positive win from the Holm-corrected pairwise set (changelog-8)
        pw = {p["pair"]: p for p in tb.get("pairwise", [])}
        def sig_win(pair):
            p = pw.get(pair)
            return bool(p and p["significant"] and p["mean_diff"] > 0)
        def diff(pair):
            p = pw.get(pair)
            return p["mean_diff"] if p else None

        c3, c2, c1, c0 = r5("C3"), r5("C2"), r5("C1"), r5("C0")
        c4, c5 = r5("C4"), r5("C5")
        # H1
        h1 = (c3 is not None and c2 is not None and c1 is not None and c0 is not None
              and c3 + 1e-9 >= c2 and c3 > c1 >= c0)
        c3_ge_c2 = c3 is not None and c2 is not None and c3 + 1e-9 >= c2
        beats_semantic_sig = sig_win("C3_vs_C1")   # SIGNIFICANT win over semantic
        beats_naive_sig = sig_win("C3_vs_C0")      # SIGNIFICANT win over naive
        # H4 (complementarity): C5 > C2 significant; secondary C4 > C0.
        h4 = sig_win("C5_vs_C2")
        h4_secondary = sig_win("C4_vs_C0")
        # H2 guardrail
        c3_dense = res["C3"].metrics["dense"]["any"]["recall_at_k"].get(5, 0.0) if "C3" in res else 0.0
        c3_hybrid = c3 or 0.0
        term_fail = tb["readability"].get("preserved_term_failures", 0)
        h2 = (c3_hybrid + 1e-9 >= c3_dense - 0.02) and term_fail == 0
        # H3 readability (parity within judge noise + objective term-preservation).
        READABILITY_TOL = 0.25  # 1-5 scale
        rd = tb["readability"]
        c3m, origm = rd.get("c3_mean", 0.0), rd.get("original_mean", 0.0)
        readability_floored = max(c3m, origm) < 2.5  # judge finds BOTH texts poor
        h3 = (c3m + READABILITY_TOL >= origm) and term_fail == 0
        per_track[tb["track"]] = {
            "H1": h1, "C3>=C2": c3_ge_c2,
            "beats_semantic_sig": beats_semantic_sig, "beats_naive_sig": beats_naive_sig,
            "H2": h2, "H3": h3, "H3_reliable": not readability_floored,
            "H4": h4, "H4_secondary_C4>C0": h4_secondary,
            "preserved_term_failures": term_fail,
            "readability": {"c3": c3m, "original": origm},
            "recall@5": {"C0": c0, "C1": c1, "C2": c2, "C3": c3, "C4": c4, "C5": c5},
            "deltas": {"C5_vs_C2": diff("C5_vs_C2"), "C4_vs_C0": diff("C4_vs_C0"),
                       "C3_vs_C2": diff("C3_vs_C2")},
        }
        if c3_ge_c2 and h2 and h3:
            validate_tracks += 1
        if beats_semantic_sig or beats_naive_sig:
            beats_semantic_tracks += 1  # "beats naive OR semantic significantly" (§2.3 PARTIAL)
        if h4:
            complement_tracks += 1
        h2_all = h2_all and h2
        h3_all = h3_all and h3

    n_tracks = len(track_bundles)
    # COMPLEMENT: H4 on the public track (B) if present, else directional on the only track.
    tracks_present = {tb["track"] for tb in track_bundles}
    complement = (complement_tracks >= 1 and ("B" in tracks_present or n_tracks == 1))
    if not h2_all or not h3_all or beats_semantic_tracks == 0:
        decision = "KILL"
    elif validate_tracks >= 2:
        decision = "VALIDATE"
    elif validate_tracks >= 1 and n_tracks == 1:
        decision = "VALIDATE*"  # meets criteria on the only available track
    else:
        decision = "PARTIAL"

    H1 = "supported" if all(v["H1"] for v in per_track.values()) else "not"
    H4 = "supported" if (complement_tracks >= 1) else "not"
    H2 = "supported" if h2_all else "not"
    H3 = "supported" if h3_all else "not"
    any_floor = any(not v["H3_reliable"] for v in per_track.values())
    # Precise, significance-backed prose (changelog-8: no "beats" without a significant pair).
    rel = []
    for t, v in per_track.items():
        c3, c2 = v["recall@5"]["C3"], v["recall@5"]["C2"]
        # A condition subset (e.g. --conditions C0,C3) leaves these None. Formatting None as
        # a float raised TypeError here and took the whole run's artifacts down with it.
        if c3 is None or c2 is None:
            have = [k for k, val in v["recall@5"].items() if val is not None]
            parts = [f"{t}: C3/C2 comparison unavailable (conditions present: "
                     f"{', '.join(have) if have else 'none'})"]
        else:
            parts = [f"{t}: C3={c3:.3f} vs C2={c2:.3f} (Δ={c3 - c2:+.3f})"]
        wins = []
        if v["beats_naive_sig"]:
            wins.append("naive(C0)")
        if v["beats_semantic_sig"]:
            wins.append("semantic(C1)")
        parts.append("significantly beats " + (", ".join(wins) if wins else "neither C0 nor C1"))
        if v["H4"]:
            parts.append(f"H4 holds (C5>C2, Δ={v['deltas']['C5_vs_C2']:+.3f})")
        else:
            parts.append(f"H4 not significant (C5 vs C2 Δ={v['deltas']['C5_vs_C2']}) ")
        rel.append(" — ".join(parts))
    complement = (complement_tracks >= 1 and ("B" in tracks_present or n_tracks == 1))
    notes = (f"{n_tracks} track(s) evaluated; VALIDATE per §2.4 needs C3>=C2 on >=2 tracks + H2 + H3. "
             f"validate_tracks={validate_tracks}, complement_tracks={complement_tracks}. "
             + " | ".join(rel) + ". "
             "Per changelog-8, 'beats' claims above are only those with a Holm-significant, "
             "CI-excludes-0 pairwise difference. ")
    if complement:
        notes += ("COMPLEMENT: formatting improves an existing strategy (H4) — the strongest "
                  "outcome is C5>C2 significant on both tracks. ")
    if any_floor:
        notes += ("H3 note: the subjective readability rubric floored out on synthetic prose "
                  "(judge rated BOTH original and formatted poorly); the OBJECTIVE preserved-term "
                  "check (0 failures) is the trustworthy H3 signal — confirm subjective "
                  "readability on Track B real prose. ")
    if decision == "VALIDATE*":
        notes += ("* = criteria met on the single available track; confirm on a 2nd track. ")
    return {"H1": H1, "H2": H2, "H3": H3, "H4": H4, "complement": complement,
            "decision": decision, "per_track": per_track, "notes": notes}


# --------------------------------------------------------------------------
# artifacts
# --------------------------------------------------------------------------
def _append_blocker(msg: str) -> None:
    path = RESULTS / "BLOCKERS.md"
    header = "" if path.exists() else "# Blockers\n\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{header}- {_utc_now()} — {msg}\n")


def freeze_preregistration(cfg: dict) -> Path:
    path = ROOT / "preregistration.json"
    payload = {"frozen_utc": _utc_now(), "seed": cfg["seed"], "criteria": PREREG_CRITERIA}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def main(argv=None) -> int:
    # A Windows console defaults to cp1252 and raises on the Greek delta and em-dashes the
    # log lines use. That surfaced as the common-size control being reported "skipped" when
    # in fact BOTH evaluations had completed and only the print failed (the log call sat
    # inside the try). Fix the encoding at the source so no computed result is ever discarded
    # because it could not be printed.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    ap = argparse.ArgumentParser(description="RAG semantic-formatter retrieval eval")
    ap.add_argument("--track", default="A", help="A|B|C (comma-separated for several)")
    ap.add_argument("--provider", default=None, help="override llm.provider (none|anthropic)")
    ap.add_argument("--model", default=None, help="override llm.model (e.g. claude-haiku-4-5)")
    ap.add_argument("--conditions", default=None, help="comma-separated condition ids")
    ap.add_argument("--embedding-backend", default=None, help="sentence-transformers|hash")
    ap.add_argument("--embedding-model", default=None, help="override embedding.model")
    ap.add_argument("--smoke", action="store_true", help="fast zero-cost pipeline smoke")
    ap.add_argument("--rerank", action="store_true",
                    help="enable the v1.3 reranking axis (orthogonal; off by default)")
    ap.add_argument("--rerank-backend", default=None, dest="rerank_backend",
                    help="cross_encoder|noop (default cross_encoder)")
    ap.add_argument("--no-sweep", action="store_true", dest="no_sweep",
                    help="skip the live chunk-size sweep; use recorded dev-swept sizes")
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--out", default=None,
                    help="output directory (default: results/). Use a separate dir for "
                         "amendment runs so a smoke or side experiment cannot overwrite "
                         "the evidentiary artifacts of a previous published run.")
    args = ap.parse_args(argv)

    if args.out:
        global RESULTS
        RESULTS = ROOT / args.out
        RESULTS.mkdir(parents=True, exist_ok=True)
        # report.py holds its own module-level RESULTS/FIG; redirect those too or the
        # artifacts would still land in results/ and overwrite a published run.
        from src import report as _report
        _report.RESULTS = RESULTS
        _report.FIG = RESULTS / 'figures'

    def log(m):
        print(m, flush=True)

    cfg = C.load_default()
    if args.provider:
        cfg["llm"]["provider"] = args.provider
    if getattr(args, "rerank", False):
        cfg.setdefault("rerank", {})["enabled"] = True
        if getattr(args, "rerank_backend", None):
            cfg["rerank"]["backend"] = args.rerank_backend
    if args.model:
        cfg["llm"]["model"] = args.model
    if args.embedding_backend:
        cfg.setdefault("embedding", {})["backend"] = args.embedding_backend
    if args.embedding_model:
        cfg.setdefault("embedding", {})["model"] = args.embedding_model
    if args.smoke:
        cfg["embedding"]["backend"] = "hash"
        cfg["stats"]["bootstrap_iters"] = 1000
        cfg["stats"]["permutation_iters"] = 1000
        cfg["_smoke"] = True

    if args.conditions:
        args.conditions = [c.strip() for c in args.conditions.split(",")]

    if args.report_only:
        from src import report
        report.rebuild()
        log("report rebuilt from results/results.json")
        return 0

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "figures").mkdir(exist_ok=True)

    # Freeze pre-registration BEFORE any treatment metric is computed (§2.4).
    prereg_path = freeze_preregistration(cfg)
    log(f"pre-registration frozen -> {prereg_path.name}")

    tracks = [t.strip() for t in args.track.split(",")]
    bundles = []
    for t in tracks:
        log(f"== Track {t} ==")
        # One track failing must not discard the tracks that already succeeded. Each track is
        # tens of minutes of retrieval; losing a completed Track A because Track B could not
        # reach the LLM is a bookkeeping failure, not a scientific one. The failure is
        # recorded in BLOCKERS.md so it is visible in the write-up rather than silent.
        try:
            b = run_track(t, cfg, args, log)
        except Exception as e:
            msg = f"{type(e).__name__}: {str(e)[:200]}"
            log(f"  Track {t} FAILED mid-run -> {msg}")
            _append_blocker(f"Track {t}: failed mid-run -> {msg}")
            b = None
        if b:
            bundles.append(b)

    if not bundles:
        log("no tracks produced results; see results/BLOCKERS.md")
        return 1

    # Same principle as the judges: a summarisation failure must not destroy the artifacts.
    # The verdict is derived FROM the results; if it cannot be computed, write the results
    # anyway and say so, rather than losing an hour of retrieval to a formatting error.
    try:
        verdict = compute_verdict(bundles)
    except Exception as e:
        msg = f"{type(e).__name__}: {str(e)[:200]}"
        log(f"  verdict computation failed -> {msg} (results still written)")
        _append_blocker(f"verdict computation failed -> {msg}")
        verdict = {"decision": "UNAVAILABLE", "error": msg}
    from src import report
    run_id = _dt.datetime.now(_dt.timezone.utc).strftime("run-%Y%m%d-%H%M%S")
    results_json = report.assemble_results_json(
        run_id=run_id, created_utc=_utc_now(), git_commit=_git_commit(),
        config_digest=C.config_digest(cfg), cfg=cfg, bundles=bundles, verdict=verdict,
        prereg_hash=_sha256_file(prereg_path))
    report.write_all(results_json, bundles, cfg)

    log(f"\nDECISION: {verdict['decision']}{' +COMPLEMENT' if verdict.get('complement') else ''}  "
        f"(H1={verdict['H1']} H2={verdict['H2']} H3={verdict['H3']} H4={verdict.get('H4','n/a')})")
    log(f"artifacts -> {RESULTS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
