"""v1.9 Gate 0 (§7) — domain census, control sample, cost projection. NO MODEL IS CALLED.

Three things, all of which must happen before the freeze rather than during the run:

  1. **Domain census.** The package builder is exercised against both real corpora for all three
     arms, producing the B2(q) escalation table with its attribution column. The point is that
     the builder meets the corpus's real structural variety before the freeze, not the author's
     model of it — v1.7's F2 was found exactly this way.
  2. **Control sample**, drawn with seed 1337 and written to disk so it is frozen by the Gate 0
     commit rather than redrawn at run time.
  3. **Cost projection** against §6's declared 5,000-call ceiling.

Inventories are built from cache only; a formatter cache miss raises rather than spends.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "v19" / "results_gate0"
TRACKS = ("A", "B")
JUDGE_TRACK = "A"
PROBE_REPEATS = 3
CALL_CEILING = 5000


def census(track: str) -> dict:
    from v19.arms import ARMS, build_inventories, test_queries
    from v19.control import b2_for_query, draw_control_sample, pair_with_successor
    from src.v17.packages import PaddingUnsupported, build_package

    ds, tcfg, built = build_inventories(track)
    _dev, test = test_queries(ds, tcfg, track)
    invs = {a: built[a][0] for a in ARMS}

    rows, failures, b2s, setters = [], [], [], Counter()
    for q in test:
        try:
            b = b2_for_query(invs, q.gold_spans)
        except PaddingUnsupported as e:
            failures.append({"query_id": q.query_id, "stage": "b2", "error": str(e)[:200]})
            continue
        sizes = {}
        for a, inv in invs.items():
            try:
                sizes[a] = build_package(inv, q.gold_spans, b["b2"]).tokens
            except PaddingUnsupported as e:
                failures.append({"query_id": q.query_id, "stage": f"package/{a}",
                                 "error": str(e)[:200]})
        b2s.append(b["b2"])
        for a in b["set_by"]:
            setters[a] += 1
        rows.append({"query_id": q.query_id, "b2": b["b2"], "escalated": b["escalated"],
                     "set_by": b["set_by"], "costs": b["costs"],
                     "package_tokens": sizes,
                     "equal_across_arms": len(set(sizes.values())) == 1 and len(sizes) == len(ARMS)})

    unequal = [r for r in rows if not r["equal_across_arms"]]
    esc = [r for r in rows if r["escalated"]]
    ids = [q.query_id for q in test]
    sample = draw_control_sample(ids)
    return {"track": track, "n_queries": len(test),
            "n_scored": len(rows), "failures": failures,
            "b2_min": min(b2s, default=None), "b2_median": sorted(b2s)[len(b2s) // 2] if b2s else None,
            "b2_max": max(b2s, default=None),
            "n_escalated": len(esc), "escalation_attribution": dict(setters),
            "cap_8192_hits": sum(1 for x in b2s if x > 8192),
            "n_unequal_across_arms": len(unequal),
            "unequal_examples": unequal[:5],
            "control_sample": sample,
            "control_pairs": [{"query_id": p.query_id, "mismatched_package_of": p.mismatched_package_of}
                              for p in pair_with_successor(sample)],
            "inventory_sizes": {a: built[a][2]["index_units"] for a in ARMS},
            "rows": rows}


def project_costs(cen: dict) -> dict:
    """§6's projection, recomputed from the census rather than restated from the plan."""
    n = {c["track"]: c["n_scored"] for c in cen["tracks"]}
    from v19.arms import ARMS
    gen_single = sum(n.values()) * len(ARMS)
    control = sum(len(c["control_sample"]) for c in cen["tracks"]) * 2   # correct + mismatched
    probe = 20 * PROBE_REPEATS
    judge = n.get(JUDGE_TRACK, 0)
    single = gen_single + control + probe + judge
    # G3: targeted repeats only for Track A F768/U768 generation, and Track A judge.
    repeats_extra = 2 * (n.get("A", 0) * 2) + 2 * n.get("A", 0)
    return {"generation_single_run": gen_single, "control": control, "probe": probe,
            "judge": judge, "total_single_run_branch": single,
            "total_worst_case_targeted_repeats": single + repeats_extra,
            "ceiling": CALL_CEILING,
            "over_ceiling": (single + repeats_extra) > CALL_CEILING,
            "_note": ("control counts BOTH the correct and mismatched generation per sampled "
                      "query (§2); probe is 20 Track A dev prompts x 3 (G2/G6)")}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    from v19.arms import assert_builder_identity
    assert_builder_identity()
    cen = {"tracks": [census(t) for t in TRACKS]}
    cen["costs"] = project_costs(cen)
    slim = json.loads(json.dumps(cen))
    for t in slim["tracks"]:
        t.pop("rows", None)
    (OUT / "gate0_census.json").write_text(json.dumps(cen, indent=2), encoding="utf-8")
    (OUT / "gate0_summary.json").write_text(json.dumps(slim, indent=2), encoding="utf-8")

    for c in cen["tracks"]:
        print(f"\n=== track {c['track']} n={c['n_queries']} scored={c['n_scored']} ===")
        print(f"  inventories {c['inventory_sizes']}")
        print(f"  B2(q) min/median/max: {c['b2_min']} / {c['b2_median']} / {c['b2_max']}")
        print(f"  escalated {c['n_escalated']}/{c['n_scored']}  attribution {c['escalation_attribution']}")
        print(f"  cap 8192 hits: {c['cap_8192_hits']}")
        print(f"  packages unequal across arms: {c['n_unequal_across_arms']}")
        print(f"  builder failures: {len(c['failures'])}"
              + (f"  first: {c['failures'][0]}" if c["failures"] else ""))
        print(f"  control sample {len(c['control_sample'])} queries, first 3 {c['control_sample'][:3]}")
    k = cen["costs"]
    print(f"\n=== cost projection (ceiling {k['ceiling']}) ===")
    for key in ("generation_single_run", "control", "probe", "judge",
                "total_single_run_branch", "total_worst_case_targeted_repeats"):
        print(f"  {key:36} {k[key]}")
    print(f"  OVER CEILING: {k['over_ceiling']}")
    print(f"\nwrote {OUT/'gate0_census.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
