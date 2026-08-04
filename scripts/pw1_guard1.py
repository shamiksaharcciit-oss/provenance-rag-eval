"""PW-1 guard 1 — reproduce published levels EXACTLY before computing anything new.

Frozen order (`guard_1_order`): MiniLM / Track A first, alone. It is the single point of failure
for both primary families — family 1's only applicable MiniLM cell and family 2's only applicable
cell full stop.

Family 2 is reproduced by RE-SCORE of the published run's persisted ranked lists
(`rag-formatter-results.zip`, run-20260724-135411): rebuild the units, look up the claimed ranges
of each retrieved unit id, and apply the frozen S0 hit test. No embedding, no retrieval, so this
also validates the rebuild against the exact artifact the paper reports.

Guard 4 rides along: `top_hit_provenance` in each row records the ranges the published run
actually scored with, so the rebuild's claimed set is checked against it per query.

**If any level fails to reproduce, this exits non-zero and the analysis STOPS.** Per
`guard_1_escalation` that is a paper-level escalation, not a PW-1 blocker, and no repair is
attempted inside the frozen analysis.
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
from src.score.provenance import ANY, is_hit  # noqa: E402

PUBLISHED_RUN = "rag-formatter-results.zip"
RUN_ID = "run-20260724-135411"
K = 5

# Frozen guard-1 targets for MiniLM / Track A only.
FAMILY_2_TARGETS = {"C0": 0.7841, "C4": 0.8409}
FAMILY_1_TARGETS = {"orig256": 0.5682, "fmt256": 0.7216}


def _no_network(self, prompt, system):  # noqa: ANN001, ARG001
    raise RuntimeError("cache miss — guard 1 is cache-only and must not call the API")


def load_published_rows(track: str, conditions: set[str]) -> dict:
    with zipfile.ZipFile(ROOT / PUBLISHED_RUN) as z:
        meta = json.loads(z.read("results.json").decode("utf-8"))
        assert meta["run_id"] == RUN_ID, f"expected {RUN_ID}, got {meta['run_id']}"
        assert meta["environment"]["embedding_model"] == "all-MiniLM-L6-v2"
        rows = [json.loads(ln) for ln in
                z.read("per_query.jsonl").decode("utf-8").splitlines()]
    out: dict[str, list] = {c: [] for c in conditions}
    for r in rows:
        if r.get("track") == track and r.get("condition") in conditions:
            out[r["condition"]].append(r)
    return out


def rescore(rows: list, units_by_id: dict) -> tuple[float, int, list[str]]:
    """Recall@K under the frozen S0 hit test, from persisted ranked lists."""
    hits, missing = 0, []
    for r in rows:
        q = Query(query_id=r["query_id"], text="",
                  gold_spans=[GoldSpan(doc_id=g["doc_id"], start_char=g["start_char"],
                                       end_char=g["end_char"]) for g in r["gold_spans"]])
        hit = False
        for uid in r["retrieved_unit_ids"][:K]:
            u = units_by_id.get(uid)
            if u is None:
                missing.append(uid)
                continue
            if is_hit(u, q, variant=ANY, min_overlap=1):
                hit = True
                break
        hits += hit
    return hits / len(rows), len(rows), missing


def guard4_provenance_check(rows: list, units_by_id: dict) -> tuple[int, int]:
    """`top_hit_provenance` records the ranges the published run scored with. Compare.

    Scans the FULL retrieved list, not the top K. `top_hit_provenance` is populated for any row
    with a hit within k=10, so a top-5 scan structurally cannot match rows whose first hit sits
    at rank 6-10 — 9 such rows for C0 and 12 for C4. The first version of this check scanned only
    the top 5 and reported 138/147 and 148/160, which looked like a 92-94% agreement and was in
    fact a bug in the checker.
    """
    checked = agreed = 0
    for r in rows:
        prov = r.get("top_hit_provenance")
        if not prov:
            continue
        published = [tuple(x) for x in prov]
        for uid in r["retrieved_unit_ids"]:
            u = units_by_id.get(uid)
            if u is None:
                continue
            if [tuple(x) for x in u.source_ranges] == published:
                agreed += 1
                break
        checked += 1
    return agreed, checked


def main() -> int:
    LLMClient._call_provider = _no_network
    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    cfg["llm"]["provider"] = "anthropic"
    cfg["embedding"]["model"] = "all-MiniLM-L6-v2"     # the published stack for this cell

    track = "A"
    tcfg_raw = C.load_track(track)
    tm = tcfg_raw.get("params", {}).get("llm_model")
    tcfg = C.deep_merge(cfg, {"llm": {"model": tm}}) if tm else cfg
    dataset = load_track_dataset(tcfg_raw, tcfg["seed"])
    ctx = ChunkContext(embedder=Embedder(tcfg, cache_root=tcfg["_cache_root"]),
                       llm=build_llm(tcfg), config=tcfg)

    print(f"GUARD 1 — MiniLM / Track A, alone (frozen guard_1_order)")
    print(f"  published run {RUN_ID} from {PUBLISHED_RUN}\n")

    published = load_published_rows(track, set(FAMILY_2_TARGETS))
    failures, results = [], {}

    print("FAMILY 2 (composition, C4 vs C0) — by RE-SCORE of persisted ranked lists")
    for cond, target in FAMILY_2_TARGETS.items():
        cond_cfg = C.load_condition(cond)
        from src.run import NO_SWEEP_PARAMS
        if cond in NO_SWEEP_PARAMS:
            cond_cfg["params"] = {**cond_cfg.get("params", {}), **NO_SWEEP_PARAMS[cond]}
        units = build_units(build_chunker(cond_cfg, ctx), dataset)
        by_id = {u.unit_id: u for u in units}
        rows = published[cond]
        got, n, missing = rescore(rows, by_id)
        agreed, checked = guard4_provenance_check(rows, by_id)
        ok = round(got, 4) == target and not missing
        results[cond] = round(got, 4)
        print(f"  {cond}: recall@{K} = {got:.4f}  target {target:.4f}  n={n}  "
              f"units={len(units)}  {'REPRODUCED' if ok else '*** FAILED ***'}")
        g4_ok = agreed == checked
        print(f"       guard 4: rebuilt claimed ranges match top_hit_provenance on "
              f"{agreed}/{checked} rows  {'OK' if g4_ok else '*** MISMATCH ***'}")
        if not g4_ok:
            failures.append(f"guard 4 {cond}: {checked - agreed} rows disagree with "
                            f"top_hit_provenance")
        if missing:
            print(f"       *** {len(missing)} retrieved unit ids not in the rebuild, e.g. "
                  f"{missing[:3]}")
        if not ok:
            failures.append(f"family 2 {cond}: got {got:.4f}, expected {target:.4f}")

    if failures:
        print("\nGUARD 1 FAILED — stopping. Per guard_1_escalation this is a PAPER-LEVEL")
        print("escalation, not a PW-1 blocker. No repair attempted inside the frozen analysis.")
        for f in failures:
            print(f"  {f}")
        return 1

    delta = results["C4"] - results["C0"]
    print(f"\n  C4 - C0 = {delta:+.4f}   (frozen delta_full +0.0568)")
    if round(delta, 4) != 0.0568:
        print("  *** delta does not match the frozen delta_full — stopping")
        return 1

    print("\nFAMILY 1 (size-matched control) — requires a RE-RUN; run separately:")
    print("  python scripts/common_size_ci.py --track A --embedding-model all-MiniLM-L6-v2 \\")
    print("      --out results_pw1/guard1_family1_minilm_A.json")
    print(f"  targets: orig256 {FAMILY_1_TARGETS['orig256']:.4f}  "
          f"fmt256 {FAMILY_1_TARGETS['fmt256']:.4f}")

    out = ROOT / "results_pw1" / "guard1_minilm_A.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "guard": "guard_1", "cell_group": "MiniLM / Track A",
        "published_run": RUN_ID, "method": "re-score of persisted ranked lists",
        "family_2": {"levels": results, "targets": FAMILY_2_TARGETS,
                     "delta": round(delta, 4), "delta_full_frozen": 0.0568,
                     "reproduced": True},
        "family_1": {"method": "re-run required — no persisted per-query vectors",
                     "targets": FAMILY_1_TARGETS, "reproduced": None},
    }, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
