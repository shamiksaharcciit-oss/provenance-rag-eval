"""v1.11 E-D — the containment re-score. CODE ONLY, ZERO CALLS (plan §4).

Recomputes exact containment for the EXISTING v1.9 answers against the package text each arm
actually showed the model, beside the already-reported original-gold containment. The procedure
was frozen in `v111/containment.py` at `be74c69`, before any value was seen.

The packages are rebuilt by the frozen v1.9 procedure — PF-G1: v1.9 never persisted them.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT = ROOT / "v111" / "results_run"


def main() -> int:
    from src.v17.reading import exact_containment, gold_text
    from v111.containment import containment_against
    from v111.requests_build import load_track_a, v19_packages

    ds, tcfg, invs, test = load_track_a()
    docs = {d.doc_id: d.text for d in ds.documents}
    rows19 = json.loads((ROOT / "v19" / "results_run" / "main_A.json").read_text(
        encoding="utf-8"))["rows"]
    by_id = {r["query_id"]: r for r in rows19}

    arms = ("F768", "U768")
    tally = {a: {"vs_original_gold": 0, "vs_package_text": 0, "n": 0} for a in arms}
    per_query = []
    for q in test:
        r = by_id[q.query_id]
        g = gold_text(docs[q.gold_spans[0].doc_id], q.gold_spans)
        _b, pkgs = v19_packages(invs, q)
        row = {"query_id": q.query_id}
        for a in arms:
            ans = r["arms"][a]["answer"]
            og = exact_containment(ans, g)
            pt = containment_against(ans, pkgs[a])
            tally[a]["n"] += 1
            tally[a]["vs_original_gold"] += og
            tally[a]["vs_package_text"] += pt
            row[a] = {"vs_original_gold": og, "vs_package_text": pt}
        per_query.append(row)

    # Directional support, declared in advance in v111/containment.py's docstring:
    # F768 containment RISES against its own text while U768's stays stable.
    rise = {a: tally[a]["vs_package_text"] - tally[a]["vs_original_gold"] for a in arms}
    rec = {"stage": "ed", "calls": 0,
           "procedure_frozen_at": "be74c69ef65a6a8174ee04c05715ca0888ab2c08",
           "tally": tally, "delta_package_minus_original": rise,
           "hypothesis": ("Gate 1 §2: containment measures verbatim fidelity against a text the "
                          "treatment may lawfully edit; support = F768 rises while U768 stable"),
           "per_query": per_query}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ed_containment.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    for a in arms:
        t = tally[a]
        print(f"  {a}: vs original gold {t['vs_original_gold']}/{t['n']}  "
              f"vs package text {t['vs_package_text']}/{t['n']}  delta {rise[a]:+d}")
    print(f"  wrote {OUT/'ed_containment.json'} (zero calls)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
