"""v1.10 — the run. Written after the freeze (`e52a9a8`). ZERO fresh LLM calls.

Three arms differing only in what is prepended; `recall@budget` at B=1920 on the S2 basis, with
prepended text charged to the budget and unable to score; `recall@5` as the published-frame
companion. Retrieval is the standard stack, unchanged.

APPARATUS STOPS, all halting:
  * PC-1 — the published `recall@5` for the base arm and C2 must reproduce exactly;
  * any fresh LLM call (§0), enforced by a raising provider around arm construction;
  * the memory order — no encode without ≥ 2× the 393 MB failure point, or the sharded path;
  * the lattice identity `D_pad + D_info == D_total` on integer numerators.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from segment_size_sweep import DEPTH, _environment  # noqa: E402  (v1.6 retrieval, unchanged)

from src import config as C  # noqa: E402
from src.chunkers.base import ChunkContext  # noqa: E402
from src.datasets import load_track_dataset  # noqa: E402
from src.index.embed import Embedder  # noqa: E402
from src.llm.client import build_llm  # noqa: E402
from src.pw1.interpret import holm_within_family  # noqa: E402
from src.retrieve.retriever import Retriever  # noqa: E402
from src.run import split_dev_test  # noqa: E402
from src.score.provenance import ANY, is_hit  # noqa: E402
from src.textutil import count_tokens  # noqa: E402
from src.v17.e1 import contrast, units_at_budget  # noqa: E402
from v110.arms import (ARMS, assert_prepended_text_is_unattributed, build_base,  # noqa: E402
                       build_contextual, build_padded, provenance_hash)

FREEZE = "e52a9a88299de7efd00435e0c63be349e64e041f"
FREEZE_UTC = "2026-08-01T20:24:16Z"
MEM_FAILURE_POINT = 393
MEM_REQUIRED = 2 * MEM_FAILURE_POINT
C2_PARAMS = {"base": "naive", "chunk_tokens": 768, "overlap_frac": 0.0, "blurb_max_sentences": 2}
F_CTX = ("D_info", "D_total")


def free_mb() -> int:
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


def published(track: str) -> dict:
    """Published MiniLM recall@5 for C0 (the base arm) and C2, read from the v1.1 bundle."""
    import zipfile
    with zipfile.ZipFile(ROOT / "rag-formatter-results.zip") as z:
        r = json.loads(z.read("results.json").decode("utf-8"))
    return {x["condition"]: x["recall_at_k"]["5"] for x in r["results"]
            if x.get("track") == track and x.get("overlap_variant") == "any"}


def score(units, queries, embedder, cfg, budget, log):
    r = Retriever(units, embedder, cfg)
    toks = {u.unit_id: count_tokens(u.text) for u in units}
    by_id = {u.unit_id: u for u in units}
    out = {"recall@budget": [], "recall@5": []}
    ks, max_k, charged = [], 0, []
    for q in queries:
        ranked = [u.unit_id for u in r.retrieve(q.text, DEPTH)["hybrid"]]
        taken = units_at_budget(ranked, toks, budget)
        ks.append(len(taken))
        max_k = max(max_k, len(taken))
        charged.append(sum(toks[i] for i in taken))
        out["recall@budget"].append(
            1 if any(is_hit(by_id[i], q, variant=ANY, min_overlap=1) for i in taken) else 0)
        out["recall@5"].append(
            1 if any(is_hit(by_id[i], q, variant=ANY, min_overlap=1) for i in ranked[:5]) else 0)
    assert max_k < DEPTH, f"R4: realised k reached the ranked depth ({max_k}/{DEPTH})"
    return out, {"mean": round(sum(ks) / len(ks), 3), "max": max_k, "depth": DEPTH,
                 "tokens_charged_mean": round(sum(charged) / len(charged), 1)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--budget-tokens", type=int, default=1920)
    ap.add_argument("--iters", type=int, default=10000)
    ap.add_argument("--sharded-encode", action="store_true")
    args = ap.parse_args(argv)

    out_dir = ROOT / args.out
    assert out_dir.name != "results", "§A4: never write to results/"
    out_dir.mkdir(parents=True, exist_ok=True)
    log = lambda m: print(m, flush=True)

    fm = free_mb()
    sharded = args.sharded_encode or fm < MEM_REQUIRED
    assert fm >= MEM_REQUIRED or sharded, (
        f"memory order: {fm} MB free < {MEM_REQUIRED} required and sharded path not enabled")
    if sharded:
        from src.index.embed import Embedder as _E
        from src.pw1.safe_encode import sharded_encode_st
        _E._encode_st = lambda self, texts: sharded_encode_st(
            self.model_name, self.revision, list(texts), self.batch_size, self.device, True)
        log("  sharded encoding ON (bit-identical)")

    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    cfg["llm"]["provider"] = "anthropic"
    cfg["embedding"]["model"] = "sentence-transformers/all-MiniLM-L6-v2"
    traw = C.load_track(args.track)
    tm = traw.get("params", {}).get("llm_model")
    tcfg = C.deep_merge(cfg, {"llm": {"model": tm}}) if tm else cfg
    ds = load_track_dataset(traw, tcfg["seed"])
    dev_frac = traw.get("params", {}).get("dev_fraction")
    if dev_frac is None:
        dev_frac = tcfg.get("sweep", {}).get("dev_fraction", 0.2)
    _dev, test = split_dev_test(ds, dev_frac, tcfg["seed"])
    n = len(test)

    embedder = Embedder(tcfg, cache_root=tcfg["_cache_root"])
    llm = build_llm(tcfg)
    ctx = ChunkContext(embedder=embedder, llm=llm, config=tcfg)

    calls0 = llm.calls
    U = build_base(ds, ctx)
    Cc = build_contextual(ds, ctx, C2_PARAMS)
    P = build_padded(U, Cc)
    assert llm.calls - calls0 == 0, f"§0 VIOLATED: {llm.calls - calls0} fresh LLM calls"
    assert provenance_hash(U) == provenance_hash(Cc) == provenance_hash(P)
    inv = {"U": U, "P": P, "C": Cc}

    pub = published(args.track)
    log(f"v1.10 · track {args.track} · MiniLM · n={n} · budget={args.budget_tokens} · depth={DEPTH}")
    log(f"  freeze {FREEZE[:7]} @ {FREEZE_UTC} · free {fm} MB (need {MEM_REQUIRED})")

    manifest = {"experiment": "v1.10-context-budget", "freeze_commit": FREEZE,
                "freeze_utc": FREEZE_UTC, "pre_freeze_amendments": ["PF-G1"],
                "track": args.track, "n_queries": n, "budget_tokens": args.budget_tokens,
                "retrieval_depth": DEPTH, "embedding_model": tcfg["embedding"]["model"],
                "sharded_encode": bool(sharded), "fresh_llm_calls": 0,
                "provenance_sha256": provenance_hash(U),
                "prepended": {"C": assert_prepended_text_is_unattributed(U, Cc, "C"),
                              "P": assert_prepended_text_is_unattributed(U, P, "P")},
                "memory_margin_mb": {}, "environment": _environment(), "arms": {},
                "published_recall_at_5": pub}
    vecs = {}
    for arm in ARMS:
        t0 = time.time()
        v, k = score(inv[arm], test, embedder, tcfg, args.budget_tokens, log)
        vecs[arm] = v
        row = {"index_units": len(inv[arm]),
               "token_mean": round(sum(count_tokens(u.text) for u in inv[arm]) / len(inv[arm]), 2),
               "realised_k": k, "seconds": round(time.time() - t0, 1)}
        for met in ("recall@budget", "recall@5"):
            row[met] = {"numerator": sum(v[met]), "denominator": n,
                        "rate": round(sum(v[met]) / n, 6)}
        manifest["arms"][arm] = row
        manifest["memory_margin_mb"][arm] = {"free_after_arm": free_mb(),
                                             "known_failure_point": MEM_FAILURE_POINT}
        (out_dir / f"arm_{arm}.json").write_text(json.dumps(
            {"arm": arm, "row": row,
             "per_query": [{"query_id": q.query_id, **{m: v[m][i] for m in v}}
                           for i, q in enumerate(test)]}, indent=2), encoding="utf-8")
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        log(f"  {arm}  units={row['index_units']:5} tok_mean={row['token_mean']:7.1f} "
            f"r@budget={row['recall@budget']['numerator']:3}/{n} "
            f"r@5={row['recall@5']['numerator']:3}/{n} k={k['mean']:.1f} {row['seconds']:.0f}s")

    # PC-1 — APPARATUS STOP, on integer numerators
    pc1 = {}
    for arm, cond in (("U", "C0"), ("C", "C2")):
        got = manifest["arms"][arm]["recall@5"]["numerator"]
        exp = round(pub[cond] * n)
        pc1[arm] = {"condition": cond, "v110_numerator": got, "published_rate": pub[cond],
                    "published_numerator": exp, "reproduces": got == exp}
        assert got == exp, (
            f"PC-1 APPARATUS STOP: arm {arm} recall@5 {got}/{n} does not reproduce published "
            f"{cond} {pub[cond]} = {exp}/{n}. Nothing downstream is interpreted.")
    manifest["PC1_reproduction"] = pc1
    log(f"  PC-1: U=C0 {pc1['U']['v110_numerator']}/{n} and C=C2 {pc1['C']['v110_numerator']}/{n} "
        f"both reproduce")

    dec = {}
    for met in ("recall@budget", "recall@5"):
        g = lambda a: vecs[a][met]
        d = {"D_pad": contrast(g("P"), g("U"), n, args.iters, tcfg["seed"]),
             "D_info": contrast(g("C"), g("P"), n, args.iters, tcfg["seed"]),
             "D_total": contrast(g("C"), g("U"), n, args.iters, tcfg["seed"])}
        assert d["D_pad"]["numerator"] + d["D_info"]["numerator"] == d["D_total"]["numerator"], \
            f"lattice identity failed for {met}"
        dec[met] = d
        log(f"  -- {met} --")
        for kk, x in d.items():
            log(f"    {kk:8}{x['delta_exact']:>9} = {x['delta']:+.6f} "
                f"CI[{x['ci95'][0]:+.4f},{x['ci95'][1]:+.4f}] p={x['p_permutation']:.5f} "
                f"n01={x['discordant']['n01']:3} n10={x['discordant']['n10']:3}")

    raw = [dec["recall@budget"][k]["p_permutation"] for k in F_CTX]
    manifest["family_F_CTX"] = {"members": list(F_CTX), "metric": "recall@budget",
                                "p_raw": dict(zip(F_CTX, raw)),
                                "p_holm": dict(zip(F_CTX, holm_within_family(raw)))}
    manifest["decomposition"] = dec
    manifest["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    log(f"  F_CTX Holm: {manifest['family_F_CTX']['p_holm']}")
    log(f"wrote {out_dir/'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
