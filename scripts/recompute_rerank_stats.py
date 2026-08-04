"""Recompute the H6 statistics offline from a completed run's per_query.jsonl.

Why this exists: `per_query.jsonl` stores, for every (track, condition, query), both the
un-reranked `hit@k` and the reranked `rerank_hit@k`. Those per-query binary vectors are the
entire input to the H6 paired statistics — so the stats can be rebuilt exactly, without
repeating the expensive retrieval and cross-encoder passes.

Used when a statistics or labelling defect is found after a long run has already executed.
It recomputes; it never re-runs the model, so it cannot change what was measured — only how
what was measured is summarised.

    python scripts/recompute_rerank_stats.py --dir results_v13 [--write]

Without --write it prints and changes nothing.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.run import _did_reading  # noqa: E402  (single source of truth for the label)
from src.stats.tests import (  # noqa: E402
    holm_correction,
    paired_bootstrap_diff,
    paired_permutation_p,
)

PRIMARY = ("C0", "C1", "C2", "C3", "C4", "C5")
ITERS = 10000
SEED = 1337
CI = 0.95


def load_vectors(per_query: Path, k: int = 5):
    """(track, condition) -> {'base': [...], 'rerank': [...]} aligned by query order."""
    base = defaultdict(list)
    rerank = defaultdict(list)
    order = defaultdict(list)
    with open(per_query, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            key = (rec["track"], rec["condition"])
            hk, rk = rec.get("hit@k"), rec.get("rerank_hit@k")
            if hk is None or rk is None:
                continue
            base[key].append(int(hk[str(k)] if str(k) in hk else hk[k]))
            rerank[key].append(int(rk[str(k)] if str(k) in rk else rk[k]))
            order[key].append(rec["query_id"])
    return base, rerank, order


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="results_v13")
    ap.add_argument("--write", action="store_true",
                    help="patch the rerank block in results.json (default: print only)")
    args = ap.parse_args()

    d = ROOT / args.dir
    pq = d / "per_query.jsonl"
    if not pq.is_file():
        print(f"no per_query.jsonl in {d}", file=sys.stderr)
        return 2

    base, rerank, order = load_vectors(pq)
    tracks = sorted({t for (t, _c) in base})
    if not tracks:
        print("per_query.jsonl has no reranked records (was the run made with --rerank?)",
              file=sys.stderr)
        return 2

    main_effect: list[dict] = []
    interactions: list[dict] = []

    for track in tracks:
        conds = sorted({c for (t, c) in base if t == track})
        rows, pvals = [], []
        for cid in conds:
            b, r = base[(track, cid)], rerank[(track, cid)]
            if not b or len(b) != len(r):
                continue
            diff = paired_bootstrap_diff(r, b, ITERS, SEED, CI)
            p = paired_permutation_p(r, b, ITERS, SEED)
            is_primary = cid in PRIMARY
            row = {
                "track": track, "condition": cid, "comparison": f"{cid}+rerank_vs_{cid}",
                "metric": "recall@5",
                "family": "primary" if is_primary else "exploratory",
                "decision_bearing": is_primary,
                "n_queries": len(b),
                "base": round(sum(b) / len(b), 4),
                "reranked": round(sum(r) / len(r), 4),
                "mean_diff": round(diff["mean_diff"], 4),
                "ci95": [round(x, 4) for x in diff["ci95"]],
                "p_value": round(p, 5),
                "significant": diff["significant_ci"],
            }
            if is_primary:
                pvals.append(p)
            rows.append(row)
        if pvals:
            for row, pa in zip([r for r in rows if r["decision_bearing"]],
                               holm_correction(pvals)):
                row["p_holm"] = round(pa, 5)
        main_effect.extend(rows)

        # interaction, C3 vs C0
        need = [(track, "C0"), (track, "C3")]
        if all(k in base for k in need):
            c0, c0rr = base[(track, "C0")], rerank[(track, "C0")]
            c3, c3rr = base[(track, "C3")], rerank[(track, "C3")]
            if len({len(c0), len(c0rr), len(c3), len(c3rr)}) == 1:
                assert order[(track, "C0")] == order[(track, "C3")], \
                    "query order differs between C0 and C3 — pairing would be invalid"
                did = [(a - b) - (c - e) for a, b, c, e in zip(c3rr, c3, c0rr, c0)]
                zeros = [0.0] * len(did)
                dd = paired_bootstrap_diff(did, zeros, ITERS, SEED, CI)
                pp = paired_permutation_p(did, zeros, ITERS, SEED)
                g0 = sum(a - b for a, b in zip(c0rr, c0)) / len(c0)
                g3 = sum(a - b for a, b in zip(c3rr, c3)) / len(c3)
                d2 = paired_bootstrap_diff(c0rr, c3, ITERS, SEED, CI)
                interactions.append({
                    "track": track,
                    "quantity": "(C3+rerank - C3) - (C0+rerank - C0)",
                    "formatter_gain_c3_vs_c0": round(
                        sum(a - b for a, b in zip(c3, c0)) / len(c3), 4),
                    "rerank_gain_on_c0": round(g0, 4),
                    "rerank_gain_on_c3": round(g3, 4),
                    "did": round(dd["mean_diff"], 4),
                    "ci95": [round(x, 4) for x in dd["ci95"]],
                    "p_value": round(pp, 5),
                    "significant": dd["significant_ci"],
                    "reading": _did_reading(dd["mean_diff"], dd["significant_ci"], g0, g3),
                    "c0_plus_rerank_vs_c3": {
                        "mean_diff": round(d2["mean_diff"], 4),
                        "ci95": [round(x, 4) for x in d2["ci95"]],
                        "significant": d2["significant_ci"],
                    },
                })

    print("H6 main effect — recall@5 (hybrid, any)\n")
    print(f"{'track':6} {'cond':6} {'base':>7} {'+rr':>7} {'delta':>8} {'95% CI':>20} "
          f"{'p':>8} {'holm':>8}  sig")
    for r in main_effect:
        ci = f"[{r['ci95'][0]:+.3f},{r['ci95'][1]:+.3f}]"
        holm = f"{r['p_holm']:.4f}" if "p_holm" in r else "  --  "
        print(f"{r['track']:6} {r['condition']:6} {r['base']:7.3f} {r['reranked']:7.3f} "
              f"{r['mean_diff']:+8.4f} {ci:>20} {r['p_value']:8.4f} {holm:>8}  "
              f"{'YES' if r['significant'] else 'no'}")
    for it in interactions:
        print(f"\nH6a interaction — Track {it['track']}")
        print(f"  formatter gain (C3-C0):  {it['formatter_gain_c3_vs_c0']:+.4f}")
        print(f"  rerank gain on C0:       {it['rerank_gain_on_c0']:+.4f}")
        print(f"  rerank gain on C3:       {it['rerank_gain_on_c3']:+.4f}")
        print(f"  DiD:                     {it['did']:+.4f}  CI "
              f"[{it['ci95'][0]:+.4f},{it['ci95'][1]:+.4f}]  p={it['p_value']:.4f}  "
              f"{'SIG' if it['significant'] else 'n.s.'}")
        print(f"  reading: {it['reading']}")

    if args.write:
        rj_path = d / "results.json"
        rj = json.loads(rj_path.read_text(encoding="utf-8"))
        rr = rj.setdefault("rerank", {})
        rr["main_effect"] = main_effect
        rr["interaction"] = interactions
        rr["recomputed_offline"] = (
            "H6 statistics recomputed from per_query.jsonl after a labelling/Holm-family fix. "
            "Recomputation only re-summarises the per-query vectors already measured; no "
            "model was re-run and no measurement changed.")
        rj_path.write_text(json.dumps(rj, indent=2), encoding="utf-8")
        print(f"\npatched {rj_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
