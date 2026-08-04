"""v1.8 Gate 0 — build the arms, measure the corpus, project the cost. Spend nothing.

Run: `python -m v18.gate0_build`

This script is the Gate 0 deliverable §9 asks for, minus the determinism probes, which are held
back for the ruling (see `v18_Gate0_Findings_2026-08-01.md`, finding G1). It builds the three
arms by importing v1.6's `build_arm`, retrieves at the field-standard fixed k = 5, records
descriptive build diagnostics, and derives the §6 projection from the frozen prompt constants.

**Zero spend is asserted, not claimed.** `LLMClient.calls` counts fresh (paid) completions and
`cache_hits` counts served-from-cache ones. The run asserts `calls == 0` at the end of every
track, so "no generation call, no judge call, no arm value spent" is an executed check that
would halt the build if it were false. A second guarantee sits underneath it: with
`ANTHROPIC_API_KEY` unset, a cache miss raises before any request is constructed, so the failure
mode is a stop rather than a charge.

Nothing here scores an arm. Retrieved contexts are build material — the input generation would
consume — and no I1 or I2 value is computed on any test query before the ruling.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

from v18.arms import ARMS, FIXED_K, build_arm, inventory_diagnostics, retrieve_fixed_k
from v18.cost import project
from v18.judge_prompts import JUDGE_MODEL

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "v18" / "results_gate0"

from src import config as C  # noqa: E402
from src.chunkers.base import ChunkContext  # noqa: E402
from src.datasets import load_track_dataset  # noqa: E402
from src.index.embed import Embedder  # noqa: E402
from src.llm.client import LLMClient, build_llm  # noqa: E402
from src.run import split_dev_test  # noqa: E402

#: §1 — the published primary embedder. bge is out of scope, declared not silent.
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

#: §2 — the generator, pinned. Same model as the judge; see finding G6.
GENERATOR_MODEL = "claude-sonnet-5"

TRACKS = ("A", "B")


def _free_mb() -> int:
    """Free physical memory, recorded as a pair with the known failure point (§8)."""
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


def build_track(track: str, log) -> dict:
    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    cfg["llm"]["provider"] = "anthropic"          # so the formatter reads its real cache
    cfg["embedding"]["model"] = EMBEDDING_MODEL
    traw = C.load_track(track)
    tm = traw.get("params", {}).get("llm_model")
    tcfg = C.deep_merge(cfg, {"llm": {"model": tm}}) if tm else cfg

    ds = load_track_dataset(traw, tcfg["seed"])
    # Explicit `is None` sentinel — a declared 0.0 must not be replaced by a falsy-zero default.
    # This is v1.7 Gate 0's F5 suggestion, adopted rather than repeated.
    dev_frac = traw.get("params", {}).get("dev_fraction")
    dev_frac = dev_frac if dev_frac is not None else tcfg.get("sweep", {}).get("dev_fraction", 0.2)
    dev_q, test_q = split_dev_test(ds, dev_frac, tcfg["seed"])

    embedder = Embedder(tcfg, cache_root=tcfg["_cache_root"])
    llm = build_llm(tcfg)
    ctx_full = ChunkContext(embedder=embedder, llm=llm, config=tcfg)
    ctx_det = ChunkContext(embedder=embedder, llm=LLMClient(provider="none"), config=tcfg)

    log(f"track {track} · {EMBEDDING_MODEL} · docs={len(ds.documents)} "
        f"· dev={len(dev_q)} · test={len(test_q)} · dev_fraction={dev_frac}")

    out = {"track": track, "embedding_model": EMBEDDING_MODEL,
           "n_documents": len(ds.documents), "n_dev": len(dev_q), "n_test": len(test_q),
           "dev_fraction_declared": dev_frac, "fixed_k": FIXED_K,
           "arms": {}, "memory_margin_mb": {}}

    for arm in ARMS:
        t0 = time.time()
        hits0, calls0 = llm.cache_hits, llm.calls
        units, _rungs, _diag = build_arm(arm, ds, ctx_full, ctx_det)
        retrieved = retrieve_fixed_k(units, test_q, embedder, tcfg, FIXED_K)

        pkg = [r["package_tokens"] for r in retrieved]
        ks = [r["realised_k"] for r in retrieved]
        row = {**inventory_diagnostics(units, ds),
               "package_tokens_mean": round(sum(pkg) / len(pkg), 2),
               "package_tokens_min": min(pkg), "package_tokens_max": max(pkg),
               "realised_k_mean": round(sum(ks) / len(ks), 3), "realised_k_min": min(ks),
               "seconds": round(time.time() - t0, 1),
               "llm_cache_hits_delta": llm.cache_hits - hits0,
               "llm_fresh_calls_delta": llm.calls - calls0}
        # The zero-spend guarantee, as an executed check per arm.
        assert row["llm_fresh_calls_delta"] == 0, (
            f"SPEND STOP: {arm} made {row['llm_fresh_calls_delta']} fresh LLM calls. Gate 0 "
            f"spends nothing (plan status header, §6).")
        out["arms"][arm] = row
        out["memory_margin_mb"][arm] = {"free_after_arm": _free_mb(),
                                        "known_failure_point": 393,
                                        "_note": "PW-1 bge memory-exhaustion segfault"}

        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"contexts_{track}_{arm}.json").write_text(
            json.dumps({"track": track, "arm": arm, "fixed_k": FIXED_K,
                        "retrieved": retrieved}, indent=2), encoding="utf-8")
        log(f"  {arm:6} units={row['index_units']:5} tok_mean={row['token_mean']:7.1f} "
            f"pkg_mean={row['package_tokens_mean']:7.1f} k={row['realised_k_mean']:.2f} "
            f"cache_hits={row['llm_cache_hits_delta']:3} fresh={row['llm_fresh_calls_delta']} "
            f"{row['seconds']:.0f}s")

    assert llm.calls == 0, f"SPEND STOP: {llm.calls} fresh LLM calls on track {track}"
    out["total_fresh_llm_calls"] = llm.calls
    out["total_llm_cache_hits"] = llm.cache_hits
    return out


def main(argv=None) -> int:
    log = lambda m: print(m, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    log("v1.8 Gate 0 build — arms, corpus, projection. NOT A FREEZE. Spends nothing.\n")
    log(f"free memory at start: {_free_mb()} MB (known failure point 393 MB)\n")

    tracks = {}
    for track in TRACKS:
        tracks[track] = build_track(track, log)
        log("")

    n_by_track = {f"track_{t}": tracks[t]["n_test"] for t in TRACKS}
    projection = project(n_by_track, n_arms=len(ARMS))

    manifest = {
        "experiment": "v1.8-instrument-divergence",
        "stage": "GATE-0-BUILD",
        "status": "NOT FROZEN — becomes a pre-registration only at the Gate 0 freeze commit",
        "plan": "Plan_v18_InstrumentDivergence_2026-08-01.md",
        "arms": list(ARMS), "fixed_k": FIXED_K,
        "embedding_model": EMBEDDING_MODEL,
        "generator_model": GENERATOR_MODEL, "judge_model": JUDGE_MODEL,
        "ragas_library": "not installed; §3's second branch selected (see judge_prompts.py)",
        "tracks": tracks,
        "cost_projection": projection,
        "spend_this_stage": {
            "fresh_llm_calls": sum(tracks[t]["total_fresh_llm_calls"] for t in TRACKS),
            "llm_cache_hits": sum(tracks[t]["total_llm_cache_hits"] for t in TRACKS),
            "_note": "asserted per arm and per track, not claimed in prose",
        },
        "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    # The retrieved-context dumps are ~17 MB of DERIVED material: deterministic from the frozen
    # inventories, fixed k, and seed 1337, and free to rebuild (zero LLM spend). They are pinned
    # by content hash here and excluded from the commit by `v18/.gitignore`, matching v1.7, which
    # committed per-query records and diagnostics rather than whole inventories. The hash is what
    # makes "these are the contexts that were built" checkable without shipping the bytes.
    manifest["context_artifacts_sha256"] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(OUT.glob("contexts_*.json"))}
    (OUT / "gate0_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    log("== §6 cost projection ==")
    log(f"  corpus: {n_by_track}, arms={len(ARMS)}, "
        f"judge calls per (query, arm) = {projection['judge_calls_per_query_arm']}")
    for k, v in projection["stages"].items():
        log(f"    {k:26} {v:7,}")
    for branch in ("branch_single_run", "branch_median_x3"):
        b = projection[branch]
        verdict = "WITHIN GATE" if b["within_gate"] else "EXCEEDS GATE -> §6 STOP"
        log(f"  {branch:20} {b['total_calls']:7,} / {b['gate']:,}   {verdict}")
    log(f"\nfresh LLM calls spent this stage: {manifest['spend_this_stage']['fresh_llm_calls']}")
    log(f"wrote {OUT / 'gate0_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
