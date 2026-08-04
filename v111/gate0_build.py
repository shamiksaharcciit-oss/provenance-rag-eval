"""v1.11 Gate 0 census (§7). NO GENERATION CALL. The model list is enumerated, not generated."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "scripts")):
    if _p not in sys.path: sys.path.insert(0, _p)
OUT = ROOT / "v111" / "results_gate0"


def main() -> int:
    from src.textutil import count_tokens
    from v19.arms import build_inventories, test_queries
    from v19.control import b2_for_query, draw_control_sample, pair_with_successor
    from v19.packages import build_all
    from v111.ids import custom_id, parse_custom_id
    from v111.prompts import VARIANTS
    from v111.unanswerable import (PackageIsAnswerable, assert_no_gold_overlap,
                                   gold_bearing_ids, same_doc_answerless)
    from v110.arms import build_base, build_contextual, provenance_hash

    rep = {"experiment": "v1.11", "generation_calls_made": 0}
    ds, tcfg, built = build_inventories("A")
    _dev, test = test_queries(ds, tcfg, "A")
    invs = {a: built[a][0] for a in ("F768", "U768", "U256")}
    n = len(test)

    # --- E-A: zero-gold-overlap, executed on EVERY constructed package, both arms
    bad, gaps, sizes = [], [], []
    for q in test:
        b = b2_for_query(invs, q.gold_spans)["b2"]
        for arm in ("F768", "U768"):
            u = same_doc_answerless(invs[arm], q.gold_spans, b)
            if u is None:
                gaps.append((q.query_id, arm)); continue
            try:
                assert_no_gold_overlap(u, q.gold_spans, f"{q.query_id}/{arm}")
            except PackageIsAnswerable as e:
                bad.append(str(e)[:160])
            sizes.append(sum(count_tokens(x.text) for x in u))
    rep["EA_same_doc"] = {"packages_checked": len(sizes), "gold_overlaps": len(bad),
                          "construction_gaps": gaps, "n_gaps": len(gaps),
                          "token_min": min(sizes, default=None),
                          "token_median": sorted(sizes)[len(sizes)//2] if sizes else None,
                          "token_max": max(sizes, default=None), "examples": bad[:3]}

    # --- E-B: reuse-by-hash vs rebuild, decided by inspection of what v1.9 persisted
    v19rows = json.loads((ROOT/"v19"/"results_run"/"main_A.json").read_text(encoding="utf-8"))["rows"]
    has_pkg = any(("package" in k or "text" in k) for k in v19rows[0])
    rep["EB_packages"] = {"v19_persisted_package_text": has_pkg,
                          "decision": "REBUILD by the frozen v1.9 procedure" if not has_pkg
                                      else "REUSE byte-identical by hash",
                          "reason": ("v1.9 persisted b2/tokens/shortfalls and answers but NOT "
                                     "package text; there is nothing to hash for reuse")}

    # --- E-E: C768 arm, and whether its base is v1.6's U768 as the plan asserts
    from src.chunkers.base import ChunkContext
    from src.llm.client import build_llm
    ctx = ChunkContext(embedder=None, llm=build_llm(tcfg), config=tcfg)
    C = build_contextual(ds, ctx, {"base":"naive","chunk_tokens":768,"overlap_frac":0.0,
                                   "blurb_max_sentences":2})
    rep["EE_base_matches_U768"] = provenance_hash(C) == provenance_hash(invs["U768"])
    rep["EE_units"] = {"C768": len(C), "U768": len(invs["U768"])}

    # --- custom_id census over the DERIVED cross-product
    plan = ([("ea",a,v) for a in ("f768","u768") for v in ("xdoc","sdoc")]
            + [("eb",a,"frozen") for a in ("f768","u768")]
            + [("ec",a,v) for a in ("f768","u768") for v in ("v1","v2")]
            + [("ee",a,"frozen") for a in ("f768","c768")])
    ids = [custom_id(e,a,i,v) for (e,a,v) in plan for i in range(n)]
    rep["custom_id_census"] = {"total": len(ids), "unique": len(set(ids)),
                               "all_parse": all(parse_custom_id(c)["index"] < n for c in ids),
                               "max_len": max(len(c) for c in ids), "sample": ids[0]}
    rep["call_table"] = {"E-A": n*2*2, "E-B": n*2, "E-C": n*2*2, "E-E": n*2, "E-D": 0,
                         "total": n*2*2 + n*2 + n*2*2 + n*2, "ceiling": 4000}

    # --- prompts byte-frozen
    rep["prompts"] = {k: hashlib.sha256(v.encode()).hexdigest()[:16] for k,v in VARIANTS.items()}
    rep["prompts_retain_token"] = all("NOT FOUND" in v for v in VARIANTS.values())

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/"gate0_census.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    for k in ("EA_same_doc","EB_packages","EE_base_matches_U768","EE_units","custom_id_census",
              "call_table","prompts","prompts_retain_token","generation_calls_made"):
        print(f"  {k}: {json.dumps(rep[k])[:230]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
