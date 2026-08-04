"""v1.7 E1 — span integrity at matched budget.

Frozen at `Plan_v17_ReadingValue_2026-08-01.md` (commit e19dd35, 2026-08-01T11:40:20Z), with
pre-freeze amendments PF-1/PF-2/PF-3 recorded in its §0. This script is written AFTER the freeze,
following v1.6's precedent, so it cannot be shaped by anything the freeze was meant to fix.

ARM CONSTRUCTION IS IMPORTED, NOT COPIED. Plan §2.1 says to reuse v1.6's arm construction
*unchanged*; importing `build_arm` from `scripts/segment_size_sweep.py` guarantees that rather
than asserting it. A transcribed copy would be a second procedure for one quantity (A5b) and
would drift the moment either file was touched.

Retrieval is v1.6's, unchanged: dense + BM25, RRF k_rrf=60, candidate_pool=50, seed 1337,
DEPTH=50, budget B=1920, take units in rank order and include the unit that crosses B.

What is new is only the metric: `integrity_single` and `integrity_full` over the units retrieved
at budget, at rung S2 (primary) and S3 (reported, per PF-1).

APPARATUS STOPS, all halting rather than reporting:
  * the v1.6 recall@budget reproduction check (§2.5) — a mismatch means the apparatus moved,
    which is not a finding about integrity;
  * `integrity_single = 1` with `integrity_full = 0`, asserted per query inside `score_query`;
  * the decomposition identity on integer numerators;
  * R4's realised-k assertion, inherited with the retrieval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from segment_size_sweep import DEPTH, _environment, build_arm  # noqa: E402  (v1.6, unchanged)

from src import config as C  # noqa: E402
from src.chunkers.base import ChunkContext  # noqa: E402
from src.chunkers.base import Unit  # noqa: E402
from src.datasets import load_track_dataset  # noqa: E402
from src.index.embed import Embedder  # noqa: E402
from src.llm.client import LLMClient, build_llm  # noqa: E402
from src.pw1.interpret import holm_within_family  # noqa: E402
from src.retrieve.retriever import Retriever  # noqa: E402
from src.run import split_dev_test  # noqa: E402
from src.score.provenance import ANY, is_hit  # noqa: E402
from src.textutil import count_tokens  # noqa: E402
from src.v17.e1 import assert_decomposition, contrast, units_at_budget  # noqa: E402
from src.v17.integrity import (count_degenerate_spans, feasible_single,  # noqa: E402
                               score_query)

ARMS = ("U256", "U768", "U768-ws", "S768", "F768")
FREEZE = "e19dd353a3b1e5eeba8b523168744c9cedd69330"
FREEZE_UTC = "2026-08-01T11:40:20Z"
#: §2.4 — the decision-bearing family, exactly two members, Holm-corrected.
F_INT = ("D_int_seam", "D_int_edit")


def score_arm(units, rungs, queries, embedder, cfg, budget, log):
    """Retrieve once at DEPTH; score integrity and the recall reproduction check together."""
    r = Retriever(units, embedder, cfg)
    by_id = {u.unit_id: (rungs[i][0], rungs[i][1]) for i, u in enumerate(units)}
    toks = {u.unit_id: count_tokens(u.text) for u in units}
    docs = {u.unit_id: u.doc_id for u in units}
    inv = {rung: [(u.doc_id, by_id[u.unit_id][ix]) for u in units]
           for rung, ix in (("S2", 0), ("S3", 1))}

    out = {rung: {"integrity_single": [], "integrity_full": [], "recall@budget": []}
           for rung in ("S2", "S3")}
    feas = {"S2": [], "S3": []}
    per_query, ks, max_k, degenerate = [], [], 0, 0

    for q in queries:
        ranked = [u.unit_id for u in r.retrieve(q.text, DEPTH)["hybrid"]]
        taken = units_at_budget(ranked, toks, budget)
        ks.append(len(taken))
        max_k = max(max_k, len(taken))
        degenerate += count_degenerate_spans(q.gold_spans)
        rec = {"query_id": q.query_id, "realised_k": len(taken),
               "budget_tokens_taken": sum(toks[i] for i in taken),
               "gold_spans": [g.as_dict() for g in q.gold_spans]}
        for rung, ix in (("S2", 0), ("S3", 1)):
            sel = [(docs[i], by_id[i][ix]) for i in taken]
            sc = score_query(sel, q.gold_spans)
            out[rung]["integrity_single"].append(sc["integrity_single"])
            out[rung]["integrity_full"].append(sc["integrity_full"])
            feas[rung].append(feasible_single(inv[rung], q.gold_spans))
            hit = 0
            for i in taken:
                probe = Unit(unit_id=i, text="", doc_id=docs[i], source_ranges=by_id[i][ix])
                if is_hit(probe, q, variant=ANY, min_overlap=1):
                    hit = 1
                    break
            out[rung]["recall@budget"].append(hit)
            rec[f"integrity_single_{rung}"] = sc["integrity_single"]
            rec[f"integrity_full_{rung}"] = sc["integrity_full"]
            rec[f"recall@budget_{rung}"] = hit
        per_query.append(rec)

    assert max_k < DEPTH, f"R4: realised k reached the ranked depth ({max_k}/{DEPTH})"
    return {"vectors": out, "feasible": feas, "per_query": per_query, "degenerate_spans": degenerate,
            "realised_k": {"mean": round(sum(ks) / len(ks), 3), "max": max_k, "depth": DEPTH}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", required=True)
    ap.add_argument("--embedding-model", required=True)   # Template §B: never inherited
    ap.add_argument("--budget-tokens", type=int, default=1920)
    ap.add_argument("--iters", type=int, default=10000)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repro-against", default=None,
                    help="v1.6 results dir for the §2.5 recall@budget reproduction check")
    ap.add_argument("--sharded-encode", action="store_true",
                    help="process-isolated per-batch encoding; bit-identical, see "
                         "tests/test_pw1_safe_encode.py. Needed for bge on this host.")
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
    llm = build_llm(tcfg)
    ctx_full = ChunkContext(embedder=embedder, llm=llm, config=tcfg)
    ctx_det = ChunkContext(embedder=embedder, llm=LLMClient(provider="none"), config=tcfg)

    repro = {}
    if args.repro_against:
        m = json.loads((ROOT / args.repro_against / "manifest.json").read_text(encoding="utf-8"))
        repro = {a: v["recall@budget_S2"]["numerator"] for a, v in m["arms"].items()}

    log(f"v1.7 E1 · track {args.track} · {args.embedding_model} · n={n} · "
        f"budget={args.budget_tokens} · depth={DEPTH}")
    log(f"  freeze {FREEZE[:7]} @ {FREEZE_UTC} · rungs S2 (primary) + S3 (PF-1)")

    results: dict = {}
    manifest = {"experiment": "v1.7-E1-integrity",
                "preregistration": "Plan_v17_ReadingValue_2026-08-01.md",
                "freeze_commit": FREEZE, "freeze_utc": FREEZE_UTC,
                "pre_freeze_amendments": ["PF-1 S1->S3", "PF-2 B2(q)", "PF-3 prompt canonical"],
                "track": args.track, "embedding_model": args.embedding_model,
                "n_queries": n, "budget_tokens": args.budget_tokens, "retrieval_depth": DEPTH,
                "primary_rung": "S2", "reported_rung": "S3",
                "sharded_encode": bool(args.sharded_encode),
                "environment": _environment(), "arms": {},
                # PROC-1 — restores recorded at the moment they happen, per arm, never
                # reconstructed afterwards. Empty when sharded encoding is off.
                "PROC-1_encoder_restores": {},
                "memory_margin_mb": {}}

    def _free_mb() -> int:
        """Free physical memory. Recorded as a pair with the known failure point (§1)."""
        import ctypes

        class _M(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        s = _M()
        s.dwLength = ctypes.sizeof(_M)
        try:
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
            return int(s.ullAvailPhys / 2 ** 20)
        except Exception:
            return -1

    for arm in ARMS:
        t0 = time.time()
        hits0 = llm.cache_hits
        calls0 = getattr(llm, "api_calls", None)
        units, rungs, diag = build_arm(arm, ds, ctx_full, ctx_det)
        sc = score_arm(units, rungs, test_q, embedder, tcfg, args.budget_tokens, log)
        v = sc["vectors"]
        row = {**diag, "realised_k": sc["realised_k"], "degenerate_gold_spans": sc["degenerate_spans"],
               "seconds": round(time.time() - t0, 1),
               "llm_cache_hits_delta": llm.cache_hits - hits0}
        for rung in ("S2", "S3"):
            for met in ("integrity_single", "integrity_full", "recall@budget"):
                row[f"{met}_{rung}"] = {"numerator": sum(v[rung][met]), "denominator": n,
                                        "rate": round(sum(v[rung][met]) / n, 6)}
            row[f"feasible_single_{rung}"] = {"numerator": sum(sc["feasible"][rung]),
                                              "denominator": n}
            row[f"infeasible_single_{rung}"] = n - sum(sc["feasible"][rung])
        # §2.5 apparatus STOP — the reproduction check, on integer numerators
        if arm in repro:
            got = row["recall@budget_S2"]["numerator"]
            assert got == repro[arm], (
                f"§2.5 APPARATUS STOP: {arm} recall@budget {got}/{n} does not reproduce v1.6's "
                f"{repro[arm]}/{n}. The apparatus moved; nothing here is a finding about "
                f"integrity until that is explained.")
            row["reproduces_v16_recall_at_budget"] = True
        results[arm] = {"row": row, "vec": v}
        manifest["arms"][arm] = row
        # §1 — memory margin as a PAIR: free now, against the known bge failure point.
        manifest["memory_margin_mb"][arm] = {"free_after_arm": _free_mb(),
                                             "known_failure_point": 393,
                                             "_note": "PW-1 bge memory-exhaustion segfault"}
        if args.sharded_encode:
            from src.pw1.safe_encode import CHECKPOINT_DIR
            ck = sorted(CHECKPOINT_DIR.glob("*.npy")) if CHECKPOINT_DIR.exists() else []
            manifest["PROC-1_encoder_restores"][arm] = {
                "checkpoint_dir": str(CHECKPOINT_DIR), "n_checkpoints_present": len(ck),
                "sha256_head": [hashlib.sha256(p.read_bytes()).hexdigest()[:16] for p in ck[:8]],
                "_note": ("content-hash keyed by model+revision+batch_size; bit-identical to "
                          "monolithic encoding, pinned by tests/test_pw1_safe_encode.py")}
        # §A2 — persist at the moment it exists, not at the end
        (out_dir / f"arm_{arm.replace('@', 'at')}.json").write_text(json.dumps(
            {"arm": arm, "row": row, "per_query": sc["per_query"]}, indent=2), encoding="utf-8")
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        log(f"  {arm:8} units={row['index_units']:5} tok_mean={row['token_mean']:7.1f} "
            f"single={row['integrity_single_S2']['numerator']:3}/{n} "
            f"full={row['integrity_full_S2']['numerator']:3}/{n} "
            f"r@b={row['recall@budget_S2']['numerator']:3}/{n}"
            f"{' REPRO-OK' if arm in repro else ''} "
            f"k={sc['realised_k']['mean']:.1f} {row['seconds']:.0f}s")

    log(f"\n== decomposition (n={n}) ==")
    dec: dict = {}
    for met in ("integrity_single", "integrity_full"):
        g = lambda a: results[a]["vec"]["S2"][met]
        d = {"D_int_size": contrast(g("U768"), g("U256"), n, args.iters, tcfg["seed"]),
             "D_int_ws": contrast(g("U768-ws"), g("U768"), n, args.iters, tcfg["seed"]),
             "D_int_seam": contrast(g("S768"), g("U768-ws"), n, args.iters, tcfg["seed"]),
             "D_int_edit": contrast(g("F768"), g("S768"), n, args.iters, tcfg["seed"]),
             "D_int_total": contrast(g("F768"), g("U256"), n, args.iters, tcfg["seed"])}
        assert_decomposition(d)
        dec[met] = d
        log(f"  -- {met} --")
        for k, x in d.items():
            log(f"    {k:12}{x['delta_exact']:>9} = {x['delta']:+.6f}  "
                f"CI[{x['ci95'][0]:+.4f},{x['ci95'][1]:+.4f}]  p={x['p_permutation']:.5f}  "
                f"n01={x['discordant']['n01']:3} n10={x['discordant']['n10']:3}")

    # §2.4 — Holm within the DECLARED family only, and only on the decision-bearing metric.
    raw = [dec["integrity_single"][k]["p_permutation"] for k in F_INT]
    holm = holm_within_family(raw)          # list in, list out — order is F_INT's
    manifest["family_F_INT"] = {"members": list(F_INT), "metric": "integrity_single",
                                "p_raw": dict(zip(F_INT, raw)),
                                "p_holm": dict(zip(F_INT, holm)),
                                "_note": ("decision-bearing only in the primary cell; see the "
                                          "results document for which cell that is")}
    manifest["decomposition"] = dec
    manifest["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    log(f"\n  F_INT Holm: {manifest['family_F_INT']['p_holm']}")
    log(f"wrote {out_dir/'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
