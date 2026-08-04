"""B4 — guard 1 on every remaining frozen cell.

B2 cleared MiniLM / Track A alone, per `guard_1_order`. This covers the rest and re-verifies
MiniLM / Track A as a consistency check, so one artifact carries the whole grid.

Composition cells (family 2 and the secondary family) reproduce by RE-SCORE of persisted ranked
lists — no embedding, no retrieval. Family 1's size-matched control has no persisted per-query
vectors, so its four cells reproduce by RE-RUN via `common_size_ci.py`; this script verifies the
artifacts those runs write.

Guard 4 rides along on every re-scored cell: the rebuild's claimed ranges are checked against
`top_hit_provenance`, which records what the published run actually scored with. Per template
A1d the check asserts EXACT equality and halts — it never reports a rate.

**Any failure exits non-zero and stops the analysis.** Per `guard_1_escalation` that is a
paper-level escalation, and no repair is attempted inside the frozen analysis.
"""
from __future__ import annotations

import json
import os
import sys
import zipfile
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
from src.chunkers.base import ChunkContext  # noqa: E402
from src.datasets import load_track_dataset  # noqa: E402
from src.datasets.base import GoldSpan, Query  # noqa: E402
from src.index.embed import Embedder  # noqa: E402
from src.llm.client import LLMClient, build_llm  # noqa: E402
from src.pipeline import build_units  # noqa: E402
from src.run import NO_SWEEP_PARAMS  # noqa: E402
from src.score.provenance import ANY, is_hit  # noqa: E402

MINILM, BGE = "all-MiniLM-L6-v2", "BAAI/bge-base-en-v1.5"
MINILM_SRC, BGE_SRC = "rag-formatter-results.zip", "results_v13"

# (family, embedder, track, source, {condition: published level})
COMPOSITION_CELLS = [
    ("family_2",  MINILM, "A", MINILM_SRC, {"C0": 0.7841, "C4": 0.8409}),
    ("family_2",  BGE,    "A", BGE_SRC,    {"C0": 0.7898, "C4": 0.8352}),
    ("secondary", MINILM, "B", MINILM_SRC, {"C0": 0.3867, "C4": 0.4200}),
    ("secondary", BGE,    "B", BGE_SRC,    {"C0": 0.3533, "C4": 0.4000}),
]
FROZEN_DELTAS = {("family_2", MINILM, "A"): 0.0568, ("family_2", BGE, "A"): 0.0455,
                 ("secondary", MINILM, "B"): 0.0333, ("secondary", BGE, "B"): 0.0467}

FAMILY_1_CELLS = {
    (MINILM, "A"): {"orig256": 0.5682, "fmt256": 0.7216, "delta": 0.1534},
    (MINILM, "B"): {"orig256": 0.3533, "fmt256": 0.3800, "delta": 0.0267},
    (BGE,    "A"): {"orig256": 0.6080, "fmt256": 0.7557, "delta": 0.1477},
    (BGE,    "B"): {"orig256": 0.3600, "fmt256": 0.4267, "delta": 0.0667},
}
F1_ARTIFACT = {(MINILM, "A"): "guard1_family1_minilm_A.json",
               (MINILM, "B"): "guard1_family1_minilm_B.json",
               (BGE, "A"): "guard1_family1_bge_A.json",
               (BGE, "B"): "guard1_family1_bge_B.json"}
K = 5


def _no_network(self, prompt, system):  # noqa: ANN001, ARG001
    raise RuntimeError("cache miss — guard 1 is cache-only and must not call the API")


def per_query(src: str, track: str) -> list:
    if src.endswith(".zip"):
        with zipfile.ZipFile(ROOT / src) as z:
            lines = z.read("per_query.jsonl").decode("utf-8").splitlines()
    else:
        lines = (ROOT / src / "per_query.jsonl").read_text(encoding="utf-8").splitlines()
    return [r for r in (json.loads(x) for x in lines) if r.get("track") == track]


def rescore(rows: list, by_id: dict) -> tuple[float, list]:
    hits, missing = 0, []
    for r in rows:
        q = Query(query_id=r["query_id"], text="",
                  gold_spans=[GoldSpan(doc_id=g["doc_id"], start_char=g["start_char"],
                                       end_char=g["end_char"]) for g in r["gold_spans"]])
        for uid in r["retrieved_unit_ids"][:K]:
            u = by_id.get(uid)
            if u is None:
                missing.append(uid)
                continue
            if is_hit(u, q, variant=ANY, min_overlap=1):
                hits += 1
                break
    return hits / len(rows), missing


def guard4(rows: list, by_id: dict) -> tuple[int, int]:
    """Template A1d: exact equality, asserted by the caller. Scans the FULL retrieved list."""
    agreed = checked = 0
    for r in rows:
        prov = r.get("top_hit_provenance")
        if not prov:
            continue
        pub = [tuple(x) for x in prov]
        for uid in r["retrieved_unit_ids"]:
            u = by_id.get(uid)
            if u is not None and [tuple(x) for x in u.source_ranges] == pub:
                agreed += 1
                break
        checked += 1
    return agreed, checked


def main() -> int:
    LLMClient._call_provider = _no_network
    base = C.load_default()
    base.setdefault("_cache_root", str(ROOT / "cache"))
    base["llm"]["provider"] = "anthropic"

    failures, report = [], {"composition": [], "family_1": []}
    print("GUARD 1 — B4, all remaining frozen cells\n")
    print("COMPOSITION CELLS — by RE-SCORE of persisted ranked lists")

    cache: dict = {}
    for fam, emb, track, src, targets in COMPOSITION_CELLS:
        cfg = C.deep_merge(base, {"embedding": {"model": emb}})
        tcfg_raw = C.load_track(track)
        tm = tcfg_raw.get("params", {}).get("llm_model")
        tcfg = C.deep_merge(cfg, {"llm": {"model": tm}}) if tm else cfg
        if track not in cache:
            ds = load_track_dataset(tcfg_raw, tcfg["seed"])
            ctx = ChunkContext(embedder=Embedder(tcfg, cache_root=tcfg["_cache_root"]),
                               llm=build_llm(tcfg), config=tcfg)
            cache[track] = (ds, ctx, {})
        ds, ctx, units_cache = cache[track]
        rows_all = per_query(src, track)
        levels = {}
        for cond, target in targets.items():
            if cond not in units_cache:
                cond_cfg = C.load_condition(cond)
                if cond in NO_SWEEP_PARAMS:
                    cond_cfg["params"] = {**cond_cfg.get("params", {}),
                                          **NO_SWEEP_PARAMS[cond]}
                units_cache[cond] = build_units(build_chunker(cond_cfg, ctx), ds)
            by_id = {u.unit_id: u for u in units_cache[cond]}
            rows = [r for r in rows_all if r["condition"] == cond]
            got, missing = rescore(rows, by_id)
            ag, ch = guard4(rows, by_id)
            ok = round(got, 4) == target and not missing and ag == ch
            levels[cond] = got            # UNROUNDED; see the delta note below
            print(f"  {fam:10} {emb[:22]:24}{track}  {cond}: {round(got,4):.4f} vs {target:.4f}  "
                  f"n={len(rows)}  guard4 {ag}/{ch}  "
                  f"{'OK' if ok else '*** FAILED ***'}")
            if not ok:
                failures.append(f"{fam} {emb} {track} {cond}: got {got:.4f}, want {target:.4f}, "
                                f"guard4 {ag}/{ch}, missing {len(missing)}")
        # Compute the delta from UNROUNDED levels, then round ONCE at the end. Differencing
        # rounded levels reported +0.0454 for bge/Track A against a frozen +0.0455 and HALTED
        # guard 1 on a false failure: the true delta is 8/176 = 1/22 = 0.045454..., which rounds
        # to 0.0455, while 0.8352 - 0.7898 = 0.0454. Three of the four cells coincided, so only
        # one surfaced it. Never difference rounded values.
        delta = round(levels["C4"] - levels["C0"], 4)
        want = FROZEN_DELTAS[(fam, emb, track)]
        dok = delta == want
        print(f"  {'':10} {'':24}   delta {delta:+.4f} vs frozen {want:+.4f}  "
              f"{'OK' if dok else '*** FAILED ***'}")
        if not dok:
            failures.append(f"{fam} {emb} {track}: delta {delta:+.4f}, frozen {want:+.4f}")
        report["composition"].append({"family": fam, "embedder": emb, "track": track,
                                      "levels": {k: round(v, 4) for k, v in levels.items()},
                                      "levels_unrounded": levels, "targets": targets,
                                      "delta": delta, "delta_full_frozen": want,
                                      "reproduced": ok and dok})

    print("\nFAMILY 1 (size-matched control) — by RE-RUN; verifying written artifacts")
    for (emb, track), t in FAMILY_1_CELLS.items():
        path = ROOT / "results_pw1" / F1_ARTIFACT[(emb, track)]
        if not path.is_file():
            print(f"  {emb[:22]:24}{track}: artifact not written yet — run "
                  f"scripts/common_size_ci.py --track {track} --embedding-model {emb}")
            report["family_1"].append({"embedder": emb, "track": track, "reproduced": None})
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        row = d[0] if isinstance(d, list) else d
        got = {"orig256": row["original_256"], "fmt256": row["formatted_256"],
               "delta": row["delta"]}
        ok = all(round(got[k], 4) == v for k, v in t.items())
        print(f"  {emb[:22]:24}{track}: orig {got['orig256']:.4f}/{t['orig256']:.4f}  "
              f"fmt {got['fmt256']:.4f}/{t['fmt256']:.4f}  "
              f"delta {got['delta']:+.4f}/{t['delta']:+.4f}  "
              f"{'OK' if ok else '*** FAILED ***'}")
        if not ok:
            failures.append(f"family_1 {emb} {track}: {got} vs {t}")
        report["family_1"].append({"embedder": emb, "track": track, "levels": got,
                                   "targets": t, "reproduced": ok,
                                   "environment": row.get("environment"),
                                   "vectors_persisted": bool(row.get("_vectors"))})

    out = ROOT / "results_pw1" / "guard1_all_cells.json"
    pending = [r for r in report["family_1"] if r["reproduced"] is None]
    report["verdict"] = ("GUARD 1 FAILED" if failures else
                         ("GUARD 1 PASSED on all cells" if not pending else
                          f"GUARD 1 PASSED so far; {len(pending)} family-1 re-run(s) pending"))
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n{report['verdict']}")
    if failures:
        print("STOPPING. Per guard_1_escalation this is a PAPER-LEVEL escalation.")
        for f in failures:
            print(f"  {f}")
        return 1
    print(f"wrote {out}")
    return 0 if not pending else 2


if __name__ == "__main__":
    raise SystemExit(main())
