"""Merge the v1.5 per-condition artifacts and recompute H7 with the FROZEN Holm family.

Track B's conditions were run in isolated processes after repeated segfaults, so each printed a
Holm value computed within a single-test family. The frozen design specifies **Holm across all
six tests (3 conditions x 2 child sizes) as ONE family, per track**. Those printed values are
therefore artifacts of the execution strategy and must not be reported.

This recomputes from the persisted per-query vectors — the reason `vectors.json` is written
separately — so no model is re-run and nothing measured changes; only the correction does.

**p-values are EXACT** (handoff 2026-07-29 §1). The pre-registered test is a sign-flip
permutation on per-query differences; on paired binary outcomes that null is exactly enumerable
over the 2**K sign assignments of the K discordant pairs (K <= 35 in every cell here), which is
McNemar's exact test. Same test, same null, no sampling error — not a substitute test, and no
amendment needed. The 10k Monte-Carlo estimates are retained alongside as `p_mc_10k`, because
the gap between them is exactly the sampling noise that put Track B C2@128 on the wrong side of
alpha in the first report.

`k_discordant` is reported for every cell: it is the sample size the test actually runs on, and
a paired binary p cannot be judged without it.

p-values are stored and printed to **six significant figures**, not to a fixed number of decimal
places. Track B C0@128's exact p is 8.04663e-07; rounding it to 6 dp gives 0.000001 and to 4 dp
gives 0.0000, both of which discard the value the exactness was computed for.

A Bonferroni-adjusted CI (99.167%, m=6) is reported beside the unadjusted one. It is NOT a
decision criterion — the frozen rule is the Holm-corrected one — but the two disagree on C2@128,
and that disagreement is a defect in the criteria worth recording rather than resolving silently
at analysis time.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.stats.tests import (exact_signflip_p, holm_correction,  # noqa: E402
                             paired_bootstrap_diff, paired_permutation_p)

ITERS, SEED, CI = 10000, 1337, 0.95
CI_BONF = 1.0 - 0.05 / 6   # 99.167%, m=6 — reported, never a decision criterion
SOURCES = {
    "A": ["results_v15_A"],
    "B": ["results_v15_B", "results_v15_B_C4_128", "results_v15_B_C0_256",
          "results_v15_B_C2_256", "results_v15_B_C4_256"],
}


def load(track: str):
    cells, vecs = [], {}
    for d in SOURCES[track]:
        p = ROOT / d
        rj, vj = p / "results.json", p / "vectors.json"
        if not rj.is_file():
            continue
        for r in json.loads(rj.read_text(encoding="utf-8"))["results"]:
            cells.append({**r, "track": track, "_source": d})
        if vj.is_file():
            for v in json.loads(vj.read_text(encoding="utf-8")):
                vecs[(v["condition"], v["child_tokens"])] = v
    return cells, vecs


def main() -> int:
    out = ROOT / "results_v15_merged"
    out.mkdir(parents=True, exist_ok=True)
    summary = {"experiment": "v1.5-small-to-big",
               "preregistration": "preregistration_v15.json",
               "holm_family": "all six tests (3 conditions x 2 child sizes) as ONE family, per track",
               "p_value_method": "exact sign-flip enumeration over the 2**K assignments of the K "
                                 "discordant pairs (== McNemar exact) — the pre-registered "
                                 "permutation null computed without sampling error",
               "note": "Track B conditions ran in isolated processes after repeated segfaults; "
                       "the per-invocation Holm values in those artifacts are single-test "
                       "artifacts and are superseded by the values here.",
               "tracks": {}}

    for track in ("A", "B"):
        cells, vecs = load(track)
        if not cells:
            continue
        cells.sort(key=lambda c: (c["child_tokens"], c["condition"]))
        stats, pvals = [], []
        for c in cells:
            key = (c["condition"], c["child_tokens"])
            v = vecs.get(key)
            if not v:
                print(f"  !! {track} {key} has no vectors — cannot recompute", file=sys.stderr)
                continue
            a, b = v["s2b"], v["base"]
            d = paired_bootstrap_diff(a, b, ITERS, SEED, CI)
            d_adj = paired_bootstrap_diff(a, b, ITERS, SEED, CI_BONF)
            ex = exact_signflip_p(a, b)
            pvals.append(ex["p_exact"])
            stats.append({"track": track, "condition": c["condition"],
                          "child_tokens": c["child_tokens"], "n_queries": len(a),
                          "baseline": c["baseline"]["5"], "s2b": c["s2b"]["5"],
                          "mean_diff": round(d["mean_diff"], 4),
                          "ci95": [round(x, 4) for x in d["ci95"]],
                          "ci_bonferroni_99_17": [round(x, 4) for x in d_adj["ci95"]],
                          "p_exact": float(f'{ex["p_exact"]:.6g}'),
                          "p_mc_10k": round(paired_permutation_p(a, b, ITERS, SEED), 5),
                          "k_discordant": ex["k_discordant"],
                          "n_gains": ex["n_gains"], "n_losses": ex["n_losses"],
                          "significant_ci": d["significant_ci"],
                          "significant_ci_bonferroni": d_adj["significant_ci"]})
        for s, pa in zip(stats, holm_correction(pvals)):
            s["p_holm"] = float(f"{pa:.6g}")
            s["significant_holm"] = pa < 0.05

        print(f"\n=== Track {track} — H7, exact enumeration, Holm over all {len(stats)} tests "
              f"as ONE family ===")
        hdr = (f"{'cond':6}{'size':>6}{'base':>9}{'+s2b':>9}{'delta':>9}{'95% CI':>22}"
               f"{'K':>5}{'+/-':>9}{'p_exact':>13}{'p(Holm)':>13}{'p_mc':>9}  verdict")
        print(hdr)
        for s in stats:
            ci = f"[{s['ci95'][0]:+.4f},{s['ci95'][1]:+.4f}]"
            split = f"{s['n_gains']}/{s['n_losses']}"
            sig = "SIG" if s["significant_holm"] else "n.s."
            direction = "GAIN" if s["mean_diff"] > 0 else ("HARM" if s["mean_diff"] < 0 else "-")
            print(f"{s['condition']:6}{s['child_tokens']:6}{s['baseline']:9.4f}{s['s2b']:9.4f}"
                  f"{s['mean_diff']:+9.4f}{ci:>22}{s['k_discordant']:5}{split:>9}"
                  f"{s['p_exact']:>13.4g}{s['p_holm']:>13.4g}{s['p_mc_10k']:9.4f}  "
                  f"{sig} {direction if sig else ''}")
        summary["tracks"][track] = {"cells": cells, "h7": stats}

    # Verdict against the frozen decision rules.
    harms, gains, disagreements = [], [], []
    for t, blk in summary["tracks"].items():
        for s in blk["h7"]:
            if s["significant_holm"] and s["mean_diff"] < 0:
                harms.append(s)
            elif s["significant_holm"] and s["mean_diff"] > 0:
                gains.append(s)
            if s["significant_ci"] != s["significant_holm"] or \
               s["significant_ci"] != s["significant_ci_bonferroni"]:
                disagreements.append(
                    f"{s['track']} {s['condition']}@{s['child_tokens']}: CI95 excludes 0 = "
                    f"{s['significant_ci']}, p_holm<0.05 = {s['significant_holm']} "
                    f"(p_holm={s['p_holm']}), Bonferroni-99.17% CI excludes 0 = "
                    f"{s['significant_ci_bonferroni']} {s['ci_bonferroni_99_17']}")
    verdict = "REJECT_HARM" if harms else ("see outcome table" if gains else "KILL")
    summary["verdict"] = {
        "verdict": verdict,
        "significant_harms": [f"{s['track']} {s['condition']}@{s['child_tokens']} "
                              f"{s['mean_diff']:+.4f} (p_holm={s['p_holm']:.4g}, K={s['k_discordant']})"
                              for s in harms],
        "significant_gains": [f"{s['track']} {s['condition']}@{s['child_tokens']} "
                              f"{s['mean_diff']:+.4f} (p_holm={s['p_holm']:.4g}, K={s['k_discordant']})"
                              for s in gains],
        "criteria_disagreements": disagreements,
        "criteria_note": "The frozen significant_definition — 'paired CI excludes 0 after Holm' — "
                         "names two procedures that can disagree. Where they do, the "
                         "Holm-corrected p governs and the disagreement is listed above. The next "
                         "amendment must define significance by exactly ONE procedure.",
        "rule": "REJECT_HARM: significant negative on any primary condition on EITHER track. "
                "Takes precedence over every other branch, including a full ADOPT sweep; a harm "
                "finding is reported as harm, never offset by gains elsewhere.",
    }
    (out / "results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nVERDICT: {verdict}")
    print(f"  significant harms: {len(harms)} — {summary['verdict']['significant_harms']}")
    print(f"  significant gains: {len(gains)} — {summary['verdict']['significant_gains']}")
    if disagreements:
        print("  CRITERIA DISAGREEMENT (CI vs Holm-p vs Bonferroni CI):")
        for d_ in disagreements:
            print(f"    {d_}")
    print(f"\nwrote {out/'results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
