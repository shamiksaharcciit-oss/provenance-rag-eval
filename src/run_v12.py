"""v1.2 — Document-Identity Injection experiment (one variable, one verdict).

Decides ONLY on the fresh held-out Track B2 (§0). Freezes preregistration (hypotheses,
decision rules §5, one-shot rule, exclusion + doc-list hashes) BEFORE any B2 metric.
Conditions: C0/C2/C4 (cache replay) + C4i (treatment). Emits results_v12/.

Run:
  python -m src.run_v12 --provider anthropic --b2-model claude-sonnet-5 --a-model claude-opus-4-8
"""
from __future__ import annotations

import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import argparse
import datetime as _dt
import gc
import hashlib
import json
from pathlib import Path

from src import config as C
from src.chunkers import build_chunker
from src.chunkers.base import ChunkContext
from src.chunkers.formatter import protected_tokens
from src.datasets import track_a_synthetic
from src.datasets import track_b_public as TB
from src.index.embed import Embedder
from src.llm.client import build_llm
from src.pipeline import build_units, evaluate
from src.stats.tests import bootstrap_ci_mean, holm_correction, paired_bootstrap_diff, paired_permutation_p

ROOT = C.ROOT
OUT = ROOT / "results_v12"
CONDITIONS = ["C0", "C2", "C4", "C4i"]
B2_SEED = 1337          # pool/exclusion seed (matches v1.1)
B2_NEW_SEED = 20272     # fresh draw seed
B2_N = 180              # stretch target (§3, option b)
CHOSEN = {"C0": {"chunk_tokens": 768, "overlap_frac": 0.0}}  # match v1.1 no-sweep floor

PREREG_V12 = {
    "experiment": "v1.2-identity-injection",
    "decides_on": "Track B2 (fresh held-out); old B-150 is contaminated development data",
    "hypotheses": {
        "H5": "C4i recall@5 > C4 on B2; paired CI excludes 0 after Holm over "
              "{C4i vs C4, C4i vs C2, C4i vs C0}",
        "H5a": "the C4i-C4 gain is concentrated in identity_poor queries; identity_rich ~ 0",
        "H5b": "0 preserved-term failures; 0 identity-source violations; hybrid tracks dense for C4i",
        "H5c": "3-way readability: C4i within 0.15 of BOTH original and C4 on the 1-5 rubric",
    },
    "expectation": "on Track A (identity-rich synthetic), C4i ~ C4",
    "decision_rules": {
        "ADOPT": "H5 significant AND H5b clean AND H5c passes",
        "ADOPT_SCOPED": "H5 significant only within identity_poor subgroup AND H5b/H5c clean",
        "REJECT": "H5 and subgroup both non-sig, OR any H5b violation>0 unresolved, OR H5c fails",
    },
    "one_shot_rule": "if H5 fails on B2, do NOT iterate + re-test on B2; a retry needs a B3 split",
    "tag_rule": "identity_rich iff query shares >=1 proper-noun token with gold-doc title+abstract",
}


def _utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(items) -> str:
    return hashlib.sha256("\n".join(items).encode("utf-8")).hexdigest()


def _base_cfg(model: str, provider: str) -> dict:
    cfg = C.load_default()
    cfg["embedding"]["model"] = "all-MiniLM-L6-v2"
    cfg["llm"]["provider"] = provider
    cfg["llm"]["model"] = model
    if provider == "none":  # offline wiring smoke: hash embedder, rule-based formatter
        cfg["embedding"]["backend"] = "hash"
        cfg["stats"]["bootstrap_iters"] = 1000
        cfg["stats"]["permutation_iters"] = 1000
    return cfg


def _apply_sizes(cid: str, cond_cfg: dict) -> dict:
    if cid in CHOSEN:
        cond_cfg["params"] = {**cond_cfg.get("params", {}), **CHOSEN[cid]}
    return cond_cfg


def run_conditions(dataset, cfg, log):
    embedder = Embedder(cfg, cache_root=cfg["_cache_root"])
    llm = build_llm(cfg)
    ctx = ChunkContext(embedder=embedder, llm=llm, config=cfg)
    test_q = list(dataset.queries)
    results, identity_stats, cost_by, fmt_fallbacks = {}, {}, {}, {}
    for cid in CONDITIONS:
        cond = _apply_sizes(cid, C.load_condition(cid))
        chunker = build_chunker(cond, ctx)
        before = llm.snapshot()
        units = build_units(chunker, dataset)
        res = evaluate(cid, units, embedder, cfg, test_q, len(dataset.documents))
        res.llm_cost = llm.delta(before, llm.snapshot())
        results[cid] = res
        cost_by[cid] = res.llm_cost
        inner = getattr(chunker, "formatter", None)
        if inner is not None:  # formatted conditions (C4/C4i): per-doc failure accounting
            fmt_fallbacks[cid] = {"llm_docs": inner.fmt_llm_docs,
                                  "fallback_docs": len(inner.fmt_fallback_ids),
                                  "fallback_ids": list(inner.fmt_fallback_ids)}
        if cid == "C4i":
            identity_stats = dict(inner.identity_stats) if inner else {}
        r5 = res.metrics["hybrid"]["any"]["recall_at_k"].get(5, 0.0)
        fb = fmt_fallbacks.get(cid, {})
        log(f"    {cid}: recall@5={r5:.3f} units={res.chunk_stats['index_units']} "
            f"llm(fresh/cached)={res.llm_cost['fresh_calls']}/{res.llm_cost['cached_calls']}"
            + (f" fmt_fallback={fb['fallback_docs']}/{fb['llm_docs']}" if fb else ""))
        gc.collect()
    return {"results": results, "identity_stats": identity_stats, "cost": cost_by,
            "fmt_fallbacks": fmt_fallbacks,
            "test_q": test_q, "embedder": embedder, "llm": llm, "ctx": ctx}


def _vec(res, cid):
    return res["results"][cid].metrics["hybrid"]["any"]["_per_query"]["recall_at_k"].get(5, [])


def _pairwise(bundle, cfg, track):
    st = cfg.get("stats", {})
    iters, piters, seed = st.get("bootstrap_iters", 10000), st.get("permutation_iters", 10000), cfg["seed"]
    out, pvals = [], []
    c4i = _vec(bundle, "C4i")
    for base in ["C4", "C2", "C0"]:
        bv = _vec(bundle, base)
        if len(bv) != len(c4i) or not c4i:
            continue
        d = paired_bootstrap_diff(c4i, bv, iters, seed, st.get("ci", 0.95))
        p = paired_permutation_p(c4i, bv, piters, seed)
        pvals.append(p)
        out.append({"track": track, "pair": f"C4i_vs_{base}", "metric": "recall@5",
                    "mean_diff": round(d["mean_diff"], 4), "ci95": [round(x, 4) for x in d["ci95"]],
                    "p_value": round(p, 5), "significant": d["significant_ci"]})
    if pvals:
        for row, pa in zip(out, holm_correction(pvals)):
            row["p_holm"] = round(pa, 5)
    return out


def _subgroup(bundle, tags, cfg):
    """Delta (C4i - C4) recall@5 within identity_poor and identity_rich (paired CI)."""
    st = cfg.get("stats", {})
    iters, seed = st.get("bootstrap_iters", 10000), cfg["seed"]
    c4i, c4 = _vec(bundle, "C4i"), _vec(bundle, "C4")
    test_q = bundle["test_q"]
    out = {}
    for grp in ("identity_poor", "identity_rich"):
        idx = [i for i, q in enumerate(test_q) if tags.get(q.query_id) == grp]
        if not idx:
            out[grp] = {"n": 0}
            continue
        a = [c4i[i] for i in idx]
        b = [c4[i] for i in idx]
        d = paired_bootstrap_diff(a, b, iters, seed, st.get("ci", 0.95))
        out[grp] = {"n": len(idx),
                    "c4i_recall5": round(sum(a) / len(a), 4), "c4_recall5": round(sum(b) / len(b), 4),
                    "delta": round(d["mean_diff"], 4), "ci95": [round(x, 4) for x in d["ci95"]],
                    "significant": d["significant_ci"]}
    return out


def _guardrail(bundle, dataset, identity_stats):
    """H5b: preserved-term failures (C4i formatted vs original), identity-source violations,
    hybrid-vs-dense for C4i."""
    import re
    ctx = bundle["ctx"]
    from src.chunkers import build_chunker as _bc
    fmt = _bc(_apply_sizes("C4i", C.load_condition("C4i")), ctx)
    term_failures = 0
    for doc in dataset.documents[:20]:
        units = fmt.chunk(doc)
        formatted = "\n\n".join(u.text for u in units)
        src = set(protected_tokens(doc.text))
        got = set(re.findall(r"[A-Za-z0-9][A-Za-z0-9.\-]*", formatted))
        term_failures += sum(1 for t in src if t not in got)
    res = bundle["results"]["C4i"].metrics
    dense5 = res["dense"]["any"]["recall_at_k"].get(5, 0.0)
    hybrid5 = res["hybrid"]["any"]["recall_at_k"].get(5, 0.0)
    return {"preserved_term_failures": term_failures,
            "source_violations": identity_stats.get("source_violations", 0),
            "c4i_dense5": round(dense5, 4), "c4i_hybrid5": round(hybrid5, 4),
            "hybrid_tracks_dense": bool(hybrid5 + 1e-9 >= dense5 - 0.02)}


def _readability3(bundle, dataset, cfg):
    """3-way blind readability (original / C4 / C4i) on 20 B2 docs (§4 H5c)."""
    from src.judge.rubric import _parse_score, _READ_SYS
    ctx, llm = bundle["ctx"], bundle["llm"]
    from src.chunkers import build_chunker as _bc
    c4 = _bc(_apply_sizes("C4", C.load_condition("C4")), ctx)
    c4i = _bc(_apply_sizes("C4i", C.load_condition("C4i")), ctx)
    o, f4, f4i = [], [], []
    stub = llm.is_none
    for doc in dataset.documents[:20]:
        variants = {
            "original": doc.text[:6000],
            "c4": "\n\n".join(u.text for u in c4.chunk(doc))[:6000],
            "c4i": "\n\n".join(u.text for u in c4i.chunk(doc))[:6000],
        }
        for k, bucket in (("original", o), ("c4", f4), ("c4i", f4i)):
            if stub:
                bucket.append(4.0)
            else:
                bucket.append(_parse_score(llm.complete(f"DOCUMENT:\n{variants[k]}", system=_READ_SYS)))
    mean = lambda xs: round(sum(xs) / len(xs), 3) if xs else 0.0
    return {"n": len(o), "original": mean(o), "c4": mean(f4), "c4i": mean(f4i)}


FMT_FALLBACK_MAX_RATE = 0.10  # >10% formatter fallbacks on any formatted condition
                              # => a SYSTEMIC failure (like the original thinking bug);
                              # the run is INVALID rather than a real feature verdict.


def _verdict(pairwise_b2, subgroup, guardrail, read3, identity_stats, fmt_fallbacks=None):
    # Validity gate FIRST: if the formatter fell back on a large fraction of docs,
    # the treatment did not actually run on those docs and no ADOPT/REJECT is
    # meaningful. A handful of malformed-JSON docs is fine (transparent deviation);
    # a high rate means re-run, not decide.
    fmt_fallbacks = fmt_fallbacks or {}
    fmt_rates = {c: (v["fallback_docs"] / v["llm_docs"] if v.get("llm_docs") else 0.0)
                 for c, v in fmt_fallbacks.items()}
    fmt_valid = all(r <= FMT_FALLBACK_MAX_RATE for r in fmt_rates.values())

    pw = {p["pair"]: p for p in pairwise_b2}
    # H5 is the pre-registered primary test: C4i > C4 on the full held-out B2 set,
    # judged by the HOLM-CORRECTED permutation p across the {C4,C2,C0} family
    # (not the raw CI-excludes-0 flag). Require both direction (mean_diff>0) and
    # Holm-adjusted p < 0.05.
    c4i_c4 = pw.get("C4i_vs_C4", {})
    h5 = bool(c4i_c4.get("mean_diff", 0) > 0 and c4i_c4.get("p_holm", 1.0) < 0.05)
    sub_poor = subgroup.get("identity_poor", {})
    h5a = bool(sub_poor.get("significant") and sub_poor.get("delta", 0) > 0)
    h5b = (guardrail["preserved_term_failures"] == 0 and guardrail["source_violations"] == 0
           and guardrail["hybrid_tracks_dense"])
    within = lambda a, b: abs(a - b) <= 0.15
    h5c = within(read3["c4i"], read3["original"]) and within(read3["c4i"], read3["c4"])

    if not fmt_valid:
        decision = "INVALID"  # systemic formatter fallback -> treatment did not run
    elif h5 and h5b and h5c:
        decision = "ADOPT"
    elif h5a and (not h5) and h5b and h5c:
        decision = "ADOPT_SCOPED"
    else:
        decision = "REJECT"
    fmt_note = "; ".join(f"{c}={fmt_fallbacks[c]['fallback_docs']}/{fmt_fallbacks[c]['llm_docs']}"
                         for c in sorted(fmt_fallbacks)) or "n/a"
    notes = (f"fmt_valid={fmt_valid} (fallbacks {fmt_note}, max_rate={FMT_FALLBACK_MAX_RATE}); "
             f"H5(C4i>C4 full-set)={'sig' if h5 else 'n.s.'}; "
             f"H5a(identity_poor)={'sig' if h5a else 'n.s.'} "
             f"(delta={sub_poor.get('delta')}, n={sub_poor.get('n')}); "
             f"H5b term_fail={guardrail['preserved_term_failures']} "
             f"src_viol={guardrail['source_violations']} hybrid>=dense={guardrail['hybrid_tracks_dense']}; "
             f"H5c c4i={read3['c4i']} orig={read3['original']} c4={read3['c4']}; "
             f"stamps={identity_stats.get('stamps_total')}.")
    return {"H5": "supported" if h5 else "not", "H5a": "supported" if h5a else "not",
            "H5b": "supported" if h5b else "not", "H5c": "supported" if h5c else "not",
            "fmt_valid": fmt_valid, "fmt_fallback_rates": {c: round(r, 4) for c, r in fmt_rates.items()},
            "decision": decision, "notes": notes}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="anthropic")
    ap.add_argument("--b2-model", default="claude-sonnet-5")
    ap.add_argument("--a-model", default="claude-opus-4-8")
    args = ap.parse_args(argv)
    log = lambda m: print(m, flush=True)

    OUT.mkdir(parents=True, exist_ok=True)

    # 1) Load B2 (tags only, NO retrieval) -> freeze prereg with hashes BEFORE any metric.
    log("Loading Track B2 (fresh held-out) ...")
    ds_b2 = TB.load_b2(seed=B2_SEED, new_seed=B2_NEW_SEED, n_queries=B2_N)
    tags = ds_b2.meta["tags"]
    excl_hash = _sha(ds_b2.meta["exclusion_ids"])
    doc_hash = _sha(ds_b2.meta["doc_ids"])
    prereg = {"frozen_utc": _utc(), **PREREG_V12,
              "b2": {"n_queries": ds_b2.meta["n_queries"], "n_docs": ds_b2.meta["n_docs"],
                     "new_seed": B2_NEW_SEED, "n_identity_poor": ds_b2.meta["n_identity_poor"],
                     "n_identity_rich": ds_b2.meta["n_identity_rich"]},
              "exclusion_list_hash": excl_hash, "doc_list_hash": doc_hash}
    (ROOT / "preregistration_v12.json").write_text(json.dumps(prereg, indent=2), encoding="utf-8")
    prereg_hash = hashlib.sha256((ROOT / "preregistration_v12.json").read_bytes()).hexdigest()
    log(f"  prereg frozen: B2 n={ds_b2.meta['n_queries']} ({ds_b2.meta['n_identity_poor']} poor / "
        f"{ds_b2.meta['n_identity_rich']} rich), doc_list_hash={doc_hash[:12]}")

    # 2) Track A regression (opus, cache replay for C0/C2/C4 + fresh C4i).
    log("== Track A regression ==")
    cfg_a = _base_cfg(args.a_model, args.provider)
    ds_a_full = track_a_synthetic.load(C.load_track("A"), cfg_a["seed"])
    import random
    qs = list(ds_a_full.queries)
    random.Random(cfg_a["seed"] * 7 + 1).shuffle(qs)
    ds_a_full.queries = qs[int(round(len(qs) * 0.2)):]  # same 176-query test split as v1.1
    bundle_a = run_conditions(ds_a_full, cfg_a, log)

    # 3) Track B2 (sonnet).
    log("== Track B2 (decision data) ==")
    cfg_b2 = _base_cfg(args.b2_model, args.provider)
    # Output headroom for the formatter on long QASPER papers (up to ~335 sents).
    # With thinking disabled (client.py) the full budget goes to the JSON answer;
    # 8192 is comfortably above any full resolve/drop list and prevents a
    # truncate-and-abort now that formatter failures fail loud. This changes only
    # B2's cache keys (Track A / cfg_a untouched -> stays 100% cached).
    cfg_b2["llm"]["max_tokens"] = 8192
    bundle_b2 = run_conditions(ds_b2, cfg_b2, log)

    # 4) Analysis.
    pairwise_b2 = _pairwise(bundle_b2, cfg_b2, "B2")
    subgroup = _subgroup(bundle_b2, tags, cfg_b2)
    guardrail = _guardrail(bundle_b2, ds_b2, bundle_b2["identity_stats"])
    read3 = _readability3(bundle_b2, ds_b2, cfg_b2)
    # A regression: C4i within CI of C4
    a_diff = paired_bootstrap_diff(_vec(bundle_a, "C4i"), _vec(bundle_a, "C4"),
                                   cfg_a["stats"]["bootstrap_iters"], cfg_a["seed"])
    a_reg = {"c4": round(bundle_a["results"]["C4"].metrics["hybrid"]["any"]["recall_at_k"].get(5, 0), 4),
             "c4i": round(bundle_a["results"]["C4i"].metrics["hybrid"]["any"]["recall_at_k"].get(5, 0), 4),
             "delta": round(a_diff["mean_diff"], 4), "ci95": [round(x, 4) for x in a_diff["ci95"]],
             "within_ci_of_c4": not a_diff["significant_ci"]}

    verdict = _verdict(pairwise_b2, subgroup, guardrail, read3, bundle_b2["identity_stats"],
                       bundle_b2.get("fmt_fallbacks"))

    from src import report_v12
    # run_id was absent from the v1.2 artifacts (run_id: null in both results_v12/results.json
    # and the REJECT bundle) because this writer never generated one. It cannot be
    # reconstructed after the fact — deriving one from created_utc would fabricate lineage, not
    # recover it. Fixed forward so any future invocation records it; the spent v1.2 artifacts
    # are left untouched, since they are the frozen evidentiary record and match the bundle
    # byte-for-byte. Lineage for v1.2 remains pinned by created_utc + preregistration_hash +
    # doc_list_hash + exclusion_list_hash, which jointly identify the run.
    report_v12.write_all(OUT, {
        "run_id": "run-" + _utc().replace("-", "").replace(":", "").replace("T", "-").rstrip("Z"),
        "created_utc": _utc(), "experiment": "v1.2-identity-injection",
        "preregistration_hash": prereg_hash, "exclusion_list_hash": excl_hash,
        "doc_list_hash": doc_hash,
        "prompts_version_by_condition": {"C0": "n/a", "C2": "eval-run-20260724-135411",
                                         "C4": "eval-run-20260724-135411", "C4i": "v1.2-identity"},
        "b2": bundle_b2, "a": bundle_a, "tags": tags,
        "pairwise": pairwise_b2, "subgroup": subgroup, "guardrail": guardrail,
        "readability3way": read3, "a_regression": a_reg,
        "identity_checks": {
            "stamps_total": bundle_b2["identity_stats"].get("stamps_total", 0),
            "stamps_per_doc": bundle_b2["identity_stats"].get("stamps_per_doc", []),
            "source_violations": bundle_b2["identity_stats"].get("source_violations", 0),
            "preserved_term_failures": guardrail["preserved_term_failures"],
        },
        "fmt_fallbacks": bundle_b2.get("fmt_fallbacks", {}),
        "verdict": verdict, "b2_cost": bundle_b2["llm"].cost_summary(),
        "b2_meta": {k: ds_b2.meta[k] for k in ("n_queries", "n_docs", "n_identity_poor", "n_identity_rich")},
    })
    log(f"\nDECISION: {verdict['decision']}  (H5={verdict['H5']} H5a={verdict['H5a']} "
        f"H5b={verdict['H5b']} H5c={verdict['H5c']})")
    log(f"artifacts -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
