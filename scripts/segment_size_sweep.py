"""v1.6 — the segment-size / retrieval-budget sweep.

Frozen at `preregistration_v16.json` (commit 1b01f9b, 2026-07-31T10:06:54Z), augmented by
`preregistration_v16_addendum_01.json` (74d741e, +8.2 min). Plan:
`Experiment_Plan_v1.6_SegmentSize.md`. This script is written AFTER the freeze, per halt
condition 10.

Arms are defined INLINE (never in `config/conditions/`, which `all_condition_ids()` globs).
`overlap_frac` is pinned at 0.0 everywhere so overlap is not a second free variable.

Four implementation-correctness requirements, all verifying that the SEALED specification was
met rather than adding commitments to it:

  R1  integer numerators beside every rate and every difference; denominator per track.
  R2  every point-estimate difference must lie on the k/n lattice. Per-query recall is binary,
      so a difference off the lattice is a pairing or denominator bug wearing the costume of a
      small effect. A WIRING check.
  R3  discordant pairs n01/n10 recorded beside every net difference. A net +6 built from 8 and 2
      is a different object from one built from 40 and 34. REPORTED DESCRIPTIVELY — no test is
      computed from them, because the frozen procedure is paired_bootstrap_diff +
      paired_permutation_p and a second test on one quantity violates A5b.
  R4  the retrieval budget must not be truncated by the ranked list's depth.

**R4, corrected.** The requirement as handed over named `candidate_pool = 50` as the ceiling. It
is not the binding one. `evaluate()` calls `retrieve(q, top_k = max(k_values)) = 10`, and
reaching a 1920-token budget needs ~16 units at m=128 and up to 32 worst-case — so a depth of 10
would truncate the small-unit arms on most queries and understate them, which flatters the
large-unit arms. That is the programme's existing bias, reached five times lower than the
requirement anticipated.

So this script retrieves at depth 50 and asserts realised k stays under it. 50 is chosen because
`Retriever.retrieve` computes `pool = max(candidate_pool, top_k)`: at top_k <= 50 the pool is
unchanged at 50 and the fused ranking is byte-identical to what depth 10 would have produced in
its first 10. Requesting MORE than 50 would enlarge the fusion pool and could change the
ranking — a design change, not a fix.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src import config as C  # noqa: E402
from src.chunkers import build_chunker  # noqa: E402
from src.chunkers.base import ChunkContext, Unit  # noqa: E402
from src.chunkers.formatter import FormatterChunker  # noqa: E402
from src.datasets import load_track_dataset  # noqa: E402
from src.index.embed import Embedder  # noqa: E402
from src.llm.client import LLMClient, build_llm  # noqa: E402
from src.pipeline import build_units  # noqa: E402
from src.retrieve.retriever import Retriever  # noqa: E402
from src.run import split_dev_test  # noqa: E402
from src.score.provenance import ANY, STRICT, is_hit  # noqa: E402
from src.stats.tests import paired_bootstrap_diff, paired_permutation_p  # noqa: E402
from src.textutil import count_tokens, merge_ranges  # noqa: E402
from src.v16.regroup import _capture_groups, build_fas_units, seam_segment_spans  # noqa: E402

DEPTH = 50                      # R4; see the module docstring
SIZES_U = (128, 256, 384, 512, 768)
SIZES_SF = (384, 768)
_WS = re.compile(r"\s+")


def U(n):
    return {"id": f"U{n}", "chunker": "naive",
            "params": {"chunk_tokens": n, "overlap_frac": 0.0}}


def S(n):
    return {"soft_target_tokens": n, "reference_resolution": False, "dedup": False,
            "right_size": False, "boundary_markers": False, "markers_only": True,
            "verbatim_guardrail": True, "diff_gate": True}


def F(n):
    return {"soft_target_tokens": n, "reference_resolution": True, "dedup": True,
            "right_size": True, "boundary_markers": True, "verbatim_guardrail": True,
            "diff_gate": True}


def _environment() -> dict:
    """Template §B — the native stack, not just the analysis configuration."""
    import importlib
    import platform
    env = {"python": platform.python_version(), "platform": platform.platform()}
    for mod in ("torch", "sentence_transformers", "transformers", "tokenizers", "numpy",
                "faiss", "rank_bm25", "scipy", "safetensors", "huggingface_hub"):
        try:
            env[mod] = getattr(importlib.import_module(mod), "__version__", "unknown")
        except Exception:
            env[mod] = "not installed"
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "KMP_DUPLICATE_LIB_OK", "OMP_STACKSIZE",
                "TOKENIZERS_PARALLELISM"):
        env[f"env:{var}"] = os.environ.get(var, "<unset>")
    try:
        import torch
        env["device"] = "cuda" if torch.cuda.is_available() else "cpu"
        env["torch_num_threads"] = torch.get_num_threads()
    except Exception:
        env["device"] = "unknown"
    return env


# ---------------------------------------------------------------- arms

def _formatter_rungs(groups) -> list[tuple[list, list]]:
    """(S2, S3) ranges per emitted unit. S2 = own + absorbed; S3 = own only."""
    out = []
    for g in groups:
        own = [(s.start, s.end) for s in g]
        absorbed = [r for s in g for r in s.absorbed]
        out.append((merge_ranges(own + absorbed), merge_ranges(own)))
    return out


def build_arm(arm_id: str, dataset, ctx_full: ChunkContext, ctx_det: ChunkContext):
    """Return (units, rungs, diagnostics). `rungs[i]` is (S2_ranges, S3_ranges) for units[i]."""
    diag = {}
    if arm_id.startswith("U") and not arm_id.endswith("ws"):
        n = int(arm_id[1:])
        units = build_units(build_chunker(U(n), ctx_det), dataset)
        rungs = [(list(u.source_ranges), list(u.source_ranges)) for u in units]
    elif arm_id.endswith("-ws"):
        n = int(arm_id[1:-3])
        base = build_units(build_chunker(U(n), ctx_det), dataset)
        units = [Unit(unit_id=u.unit_id + "-ws", text=_WS.sub(" ", u.text), doc_id=u.doc_id,
                      source_ranges=list(u.source_ranges), meta=dict(u.meta)) for u in base]
        rungs = [(list(u.source_ranges), list(u.source_ranges)) for u in units]
    elif arm_id.startswith("S"):
        n = int(arm_id[1:])
        units, rungs = [], []
        for d in dataset.documents:
            us, gs = _capture_groups(FormatterChunker(S(n), ctx_det), d)
            units += us
            rungs += _formatter_rungs(gs)
    elif arm_id.startswith("F@S"):
        n = int(arm_id[3:])
        units, rungs, empty = [], [], 0
        for d in dataset.documents:
            us, dg = build_fas_units(d, F(n), S(n), ctx_full, ctx_det)
            empty += dg["empty_segments"]
            units += us
            # F@S emits through FULL's _emit, so its source_ranges are already S2; S3 needs the
            # own-only set, recovered from the same regrouping.
            _u, gs = _capture_groups(FormatterChunker(F(n), ctx_full), d)
            by_start = {s.start: s for g in gs for s in g}
            spans = seam_segment_spans(_capture_groups(FormatterChunker(S(n), ctx_det), d)[1])
            buckets: list[list] = [[] for _ in spans]
            for s in by_start.values():
                for i, (a, b) in enumerate(spans):
                    if a <= s.start < b:
                        buckets[i].append(s)
                        break
                else:
                    buckets[-1].append(s)
            rungs += _formatter_rungs([sorted(b, key=lambda x: x.start)
                                       for b in buckets if b])
        diag["empty_segments"] = empty
    elif arm_id.startswith("F"):
        n = int(arm_id[1:])
        units, rungs = [], []
        for d in dataset.documents:
            us, gs = _capture_groups(FormatterChunker(F(n), ctx_full), d)
            units += us
            rungs += _formatter_rungs(gs)
    else:
        raise ValueError(f"unknown arm {arm_id}")

    assert len(units) == len(rungs), f"{arm_id}: {len(units)} units vs {len(rungs)} rung sets"
    diag.setdefault("empty_segments", 0)
    toks = [count_tokens(u.text) for u in units]
    diag.update({"index_units": len(units),
                 "units_per_doc": round(len(units) / len(dataset.documents), 4),
                 "token_mean": round(sum(toks) / len(toks), 2)})
    return units, rungs, diag


# ---------------------------------------------------------------- scoring

def score_arm(units, rungs, queries, embedder, cfg, budget: int, log):
    """Retrieve once at DEPTH, then score every metric off the same ranked lists."""
    r = Retriever(units, embedder, cfg)
    by_id = {u.unit_id: (rungs[i][0], rungs[i][1]) for i, u in enumerate(units)}
    toks = {u.unit_id: count_tokens(u.text) for u in units}
    docs = {u.unit_id: u.doc_id for u in units}

    out = {rung: {"recall@5": [], "recall@budget": []} for rung in ("S2", "S3")}
    strict5 = {"S2": [], "S3": []}
    realised_k, per_query, max_k_seen = [], [], 0

    for q in queries:
        ranked = r.retrieve(q.text, DEPTH)["hybrid"]
        # R4 — the budget must be reachable inside the ranked list.
        acc, k = 0, 0
        while k < len(ranked) and acc < budget:
            acc += toks[ranked[k].unit_id]
            k += 1
        if acc < budget:
            raise RuntimeError(
                f"R4: budget {budget} not met for {q.query_id} — only {acc} tokens in "
                f"{len(ranked)} units. The ranked list truncated the metric; do NOT raise the "
                f"pool, that changes retrieval for every arm.")
        realised_k.append(k)
        max_k_seen = max(max_k_seen, k)

        rec = {"query_id": q.query_id,
               "gold_spans": [g.as_dict() for g in q.gold_spans],
               "retrieved_unit_ids": [u.unit_id for u in ranked],
               "realised_k": k}
        for rung, ix in (("S2", 0), ("S3", 1)):
            def hit(units_slice, variant=ANY):
                for u in units_slice:
                    probe = Unit(unit_id=u.unit_id, text="", doc_id=docs[u.unit_id],
                                 source_ranges=by_id[u.unit_id][ix])
                    if is_hit(probe, q, variant=variant, min_overlap=1):
                        return 1
                return 0
            out[rung]["recall@5"].append(hit(ranked[:5]))
            out[rung]["recall@budget"].append(hit(ranked[:k]))
            strict5[rung].append(hit(ranked[:5], STRICT))
            rec[f"hit@5_{rung}"] = out[rung]["recall@5"][-1]
            rec[f"hit@budget_{rung}"] = out[rung]["recall@budget"][-1]
        per_query.append(rec)

    assert max_k_seen < DEPTH, f"R4: realised k reached the ranked depth ({max_k_seen}/{DEPTH})"
    return {"vectors": out, "strict5": strict5, "per_query": per_query,
            "realised_k": {"mean": round(sum(realised_k) / len(realised_k), 3),
                           "max": max_k_seen, "depth": DEPTH}}


def contrast(a: list[int], b: list[int], n: int, iters: int, seed: int) -> dict:
    """R1 + R2 + R3: integer numerator, lattice assertion, discordant pairs."""
    assert len(a) == len(b) == n, f"pairing broken: {len(a)}, {len(b)}, n={n}"
    num = sum(a) - sum(b)
    d = paired_bootstrap_diff(a, b, iters, seed, 0.95)
    delta = d["mean_diff"]
    assert abs(delta - num / n) < 1e-9, (           # R2 — wiring check
        f"R2: delta {delta} is off the k/{n} lattice (numerator {num})")
    n01 = sum(1 for x, y in zip(a, b) if x and not y)
    n10 = sum(1 for x, y in zip(a, b) if y and not x)
    return {"numerator": num, "denominator": n, "delta": round(delta, 6),
            "delta_exact": f"{num}/{n}",
            "ci95": [round(x, 6) for x in d["ci95"]],
            "p_permutation": round(paired_permutation_p(a, b, iters, seed), 6),
            "discordant": {"n01": n01, "n10": n10, "informative": n01 + n10,
                           "_note": "descriptive only; no test is computed from these (A5b)"}}


# ---------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", required=True)
    ap.add_argument("--embedding-model", required=True)     # Template §B: never inherited
    ap.add_argument("--budget-tokens", type=int, default=1920)
    ap.add_argument("--iters", type=int, default=10000)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sharded-encode", action="store_true")
    args = ap.parse_args(argv)

    out_dir = ROOT / args.out
    assert out_dir.name != "results", "§A4: never write to results/"
    out_dir.mkdir(parents=True, exist_ok=True)
    log = lambda m: print(m, flush=True)

    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    cfg["llm"]["provider"] = "anthropic"
    cfg["embedding"]["model"] = args.embedding_model
    traw = C.load_track(args.track)
    tm = traw.get("params", {}).get("llm_model")
    tcfg = C.deep_merge(cfg, {"llm": {"model": tm}}) if tm else cfg

    if args.sharded_encode:
        from src.index.embed import Embedder as _E
        from src.pw1.safe_encode import sharded_encode_st
        _E._encode_st = lambda self, texts: sharded_encode_st(
            self.model_name, self.revision, list(texts), self.batch_size, self.device, True)
        log("  sharded encoding ON (bit-identical; tests/test_pw1_safe_encode.py)")

    ds = load_track_dataset(traw, tcfg["seed"])
    dev_frac = traw.get("params", {}).get("dev_fraction")
    dev_frac = dev_frac if dev_frac is not None else tcfg.get("sweep", {}).get("dev_fraction", 0.2)
    _dev, test_q = split_dev_test(ds, dev_frac, tcfg["seed"])
    n = len(test_q)
    embedder = Embedder(tcfg, cache_root=tcfg["_cache_root"])
    ctx_full = ChunkContext(embedder=embedder, llm=build_llm(tcfg), config=tcfg)
    ctx_det = ChunkContext(embedder=embedder, llm=LLMClient(provider="none"), config=tcfg)

    log(f"v1.6 · track {args.track} · {args.embedding_model} · n={n} · budget="
        f"{args.budget_tokens} · depth={DEPTH}")
    log(f"  freeze 1b01f9b @ 2026-07-31T10:06:54Z + addendum 74d741e")

    arms = ([f"U{k}" for k in SIZES_U] + [f"U{k}-ws" for k in SIZES_SF]
            + [f"S{k}" for k in SIZES_SF] + [f"F{k}" for k in SIZES_SF]
            + [f"F@S{k}" for k in SIZES_SF])
    results: dict = {}
    manifest = {"experiment": "v1.6-segment-size",
                "preregistration": "preregistration_v16.json",
                "freeze_commit": "1b01f9b4c760123eb7a26a713e473ad69346bc8d",
                "freeze_utc": "2026-07-31T10:06:54Z",
                "addendum": "preregistration_v16_addendum_01.json (74d741e)",
                "track": args.track, "embedding_model": args.embedding_model,
                "n_queries": n, "budget_tokens": args.budget_tokens,
                "retrieval_depth": DEPTH,
                "depth_note": ("R4 corrected: evaluate() uses depth 10, which truncates the "
                               "budget for small-unit arms. 50 leaves the fusion pool unchanged "
                               "at max(candidate_pool, top_k) = 50."),
                "environment": _environment(), "arms": {}}

    for arm in arms:
        t0 = time.time()
        units, rungs, diag = build_arm(arm, ds, ctx_full, ctx_det)
        sc = score_arm(units, rungs, test_q, embedder, tcfg, args.budget_tokens, log)
        v = sc["vectors"]
        # halt condition 2 — scoped to NO-DEDUP arms only
        if arm.startswith("U") or arm.startswith("S"):
            assert v["S2"]["recall@budget"] == v["S3"]["recall@budget"], \
                f"halt 2: S2 != S3 on the no-dedup arm {arm}"
        row = {**diag,
               "recall@budget_S2": {"numerator": sum(v["S2"]["recall@budget"]), "denominator": n,
                                    "rate": round(sum(v["S2"]["recall@budget"]) / n, 6)},
               "recall@budget_S3": {"numerator": sum(v["S3"]["recall@budget"]), "denominator": n,
                                    "rate": round(sum(v["S3"]["recall@budget"]) / n, 6)},
               "recall@5_S2": {"numerator": sum(v["S2"]["recall@5"]), "denominator": n,
                               "rate": round(sum(v["S2"]["recall@5"]) / n, 6)},
               "recall@5_S3": {"numerator": sum(v["S3"]["recall@5"]), "denominator": n,
                               "rate": round(sum(v["S3"]["recall@5"]) / n, 6)},
               "recall@5_strict_S2": {"numerator": sum(sc["strict5"]["S2"]), "denominator": n},
               "realised_k": sc["realised_k"],
               "seconds": round(time.time() - t0, 1)}
        results[arm] = {"row": row, "vec": v}
        manifest["arms"][arm] = row
        # §A2 — persist at the moment it exists, not at the end.
        (out_dir / f"arm_{arm.replace('@','at')}.json").write_text(json.dumps(
            {"arm": arm, "row": row, "per_query": sc["per_query"],
             "units": [{"unit_id": u.unit_id, "doc_id": u.doc_id,
                        "S2": [list(x) for x in rungs[i][0]],
                        "S3": [list(x) for x in rungs[i][1]]} for i, u in enumerate(units)]},
            indent=2), encoding="utf-8")
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        log(f"  {arm:8} units={row['index_units']:5} tok_mean={row['token_mean']:7.1f} "
            f"r@budget={row['recall@budget_S2']['numerator']:3}/{n} "
            f"r@5={row['recall@5_S2']['numerator']:3}/{n} "
            f"k={sc['realised_k']['mean']:.1f}(max {sc['realised_k']['max']}) "
            f"{row['seconds']:.0f}s")

    log("\n== decomposition (S2, recall@budget) ==")
    g = lambda a: results[a]["vec"]["S2"]["recall@budget"]
    dec = {}
    for m in SIZES_SF:
        dec[f"D_size({m})"] = contrast(g(f"U{m}"), g("U256"), n, args.iters, tcfg["seed"])
        dec[f"D_ws({m})"] = contrast(g(f"U{m}-ws"), g(f"U{m}"), n, args.iters, tcfg["seed"])
        dec[f"D_seam({m})"] = contrast(g(f"S{m}"), g(f"U{m}-ws"), n, args.iters, tcfg["seed"])
        dec[f"D_edit({m})"] = contrast(g(f"F{m}"), g(f"S{m}"), n, args.iters, tcfg["seed"])
        dec[f"D_text({m})"] = contrast(g(f"F@S{m}"), g(f"S{m}"), n, args.iters, tcfg["seed"])
        dec[f"D_reseam({m})"] = contrast(g(f"F{m}"), g(f"F@S{m}"), n, args.iters, tcfg["seed"])
        dec[f"D_total({m})"] = contrast(g(f"F{m}"), g("U256"), n, args.iters, tcfg["seed"])
        # halt condition 3 — WIRING checks, on integer numerators
        outer = (dec[f"D_size({m})"]["numerator"] + dec[f"D_ws({m})"]["numerator"]
                 + dec[f"D_seam({m})"]["numerator"] + dec[f"D_edit({m})"]["numerator"])
        assert outer == dec[f"D_total({m})"]["numerator"], f"halt 3: outer identity, m={m}"
        split = dec[f"D_text({m})"]["numerator"] + dec[f"D_reseam({m})"]["numerator"]
        assert split == dec[f"D_edit({m})"]["numerator"], f"halt 3: split identity, m={m}"
        for k in ("D_size", "D_ws", "D_seam", "D_edit", "D_text", "D_reseam", "D_total"):
            d = dec[f"{k}({m})"]
            log(f"  {k}({m}):{d['delta_exact']:>9} = {d['delta']:+.6f}  "
                f"CI[{d['ci95'][0]:+.4f},{d['ci95'][1]:+.4f}]  p={d['p_permutation']:.5f}  "
                f"n01={d['discordant']['n01']:3} n10={d['discordant']['n10']:3}")
        log(f"    identities hold (wiring check, not validity): outer {outer}, split {split}")

    manifest["decomposition"] = dec
    manifest["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    log(f"\nwrote {out_dir/'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
