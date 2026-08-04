"""v1.11 scoring — fresh process, from the persisted artifacts only.

Reads `answers_*.json`, `packages.json` and `specs.json`; recomputes nothing from memory of the
run. The persistence acceptor runs FIRST: if any package text or output text is missing, no
number is produced, because a score over a partial record is worse than no score.
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
SIX = None  # filled from construction_gaps.json


def load():
    specs = json.loads((OUT / "specs.json").read_text(encoding="utf-8"))
    packages = json.loads((OUT / "packages.json").read_text(encoding="utf-8"))
    answers = json.loads((OUT / "answers_all.json").read_text(encoding="utf-8"))
    gaps = json.loads((OUT / "construction_gaps.json").read_text(encoding="utf-8"))
    return specs, packages, answers, gaps


def assert_complete(specs, packages, answers):
    """Every request has both its package text and its output text persisted (PF-G1)."""
    miss_p = [s["custom_id"] for s in specs if not packages.get(s["custom_id"])]
    miss_a = [s["custom_id"] for s in specs if s["custom_id"] not in answers]
    assert not miss_p, f"{len(miss_p)} packages not persisted, e.g. {miss_p[:3]}"
    assert not miss_a, f"{len(miss_a)} outputs not persisted, e.g. {miss_a[:3]}"
    return {"requests": len(specs), "packages_persisted": len(specs) - len(miss_p),
            "outputs_persisted": len(specs) - len(miss_a)}


def main() -> int:
    from src.v17.reading import gold_text, is_not_found, token_f1
    from src.v17.e1 import contrast
    from v111.unanswerable import false_answer
    from v111.requests_build import load_track_a

    specs, packages, answers, gaps = load()
    integrity = assert_complete(specs, packages, answers)
    print(f"  persistence acceptor: {integrity}")

    ds, tcfg, invs, test = load_track_a()
    docs = {d.doc_id: d.text for d in ds.documents}
    gold = {q.query_id: gold_text(docs[q.gold_spans[0].doc_id], q.gold_spans) for q in test}
    order = [q.query_id for q in test]
    by = {}
    for s in specs:
        by[(s["exp"], s["arm"], s["variant"], s["query_id"])] = answers[s["custom_id"]]

    res = {"integrity": integrity, "construction_gaps": gaps}

    # ---------------- E-A: false answering. PS-1 on the same-doc construction, 170 pairs.
    ea = {}
    for variant in ("sdoc", "xdoc"):
        vec = {}
        for arm in ("F768", "U768"):
            vec[arm] = {q: false_answer(by[("ea", arm, variant, q)])
                        for q in order if ("ea", arm, variant, q) in by}
        paired = [q for q in order if q in vec["F768"] and q in vec["U768"]]
        a = [vec["F768"][q] for q in paired]
        b = [vec["U768"][q] for q in paired]
        c = contrast(a, b, len(paired), 10000, 1337)
        ea[variant] = {"n_paired": len(paired),
                       "rate": {arm: {"numerator": sum(vec[arm].values()),
                                      "denominator": len(vec[arm])} for arm in vec},
                       "contrast": c}
        # the six unpaired F768 packages, their own table (Gate 0 ruling §1.2)
        if variant == "sdoc":
            unp = [q for q in order if q in vec["F768"] and q not in vec["U768"]]
            ea["unpaired_F768"] = [{"query_id": q, "false_answer": vec["F768"][q],
                                    "answer": by[("ea", "F768", "sdoc", q)][:200]} for q in unp]
    res["EA"] = ea

    # ---------------- E-B / E-C / E-E: token-F1 and abstention, with direction counts
    def f1_block(exp, arms, variant):
        out = {"arms": {}, "n": 0}
        per = {}
        for arm in arms:
            per[arm] = {q: by[(exp, arm, variant, q)] for q in order if (exp, arm, variant, q) in by}
            out["arms"][arm] = {
                "mean_f1": round(sum(token_f1(t, gold[q]) for q, t in per[arm].items())
                                 / max(1, len(per[arm])), 6),
                "not_found": sum(1 for t in per[arm].values() if is_not_found(t)),
                "n": len(per[arm])}
        a0, a1 = arms
        common = [q for q in order if q in per[a0] and q in per[a1]]
        d = [token_f1(per[a0][q], gold[q]) - token_f1(per[a1][q], gold[q]) for q in common]
        out["n"] = len(common)
        out["mean_diff"] = round(sum(d) / len(d), 6)
        out["direction_counts"] = {f"{a0}_higher": sum(1 for x in d if x > 0),
                                   f"{a1}_higher": sum(1 for x in d if x < 0),
                                   "tied": sum(1 for x in d if x == 0)}
        return out

    res["EB"] = f1_block("eb", ("F768", "U768"), "frozen")
    res["EC"] = {v: f1_block("ec", ("F768", "U768"), v) for v in ("v1", "v2")}
    res["EE"] = f1_block("ee", ("C768", "U768"), "frozen")
    res["ED"] = json.loads((OUT / "ed_containment.json").read_text(encoding="utf-8"))["tally"]

    (OUT / "scores.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"  EA sdoc: {res['EA']['sdoc']['rate']} contrast {res['EA']['sdoc']['contrast']['delta_exact']} "
          f"p={res['EA']['sdoc']['contrast']['p_permutation']}")
    print(f"  EA xdoc: {res['EA']['xdoc']['rate']}")
    print(f"  EA unpaired F768: {len(res['EA']['unpaired_F768'])} rows, "
          f"false={sum(r['false_answer'] for r in res['EA']['unpaired_F768'])}")
    for k in ("EB", "EE"):
        print(f"  {k}: {res[k]['arms']} diff {res[k]['mean_diff']:+.6f} {res[k]['direction_counts']}")
    for v in ("v1", "v2"):
        b = res["EC"][v]
        print(f"  EC-{v}: {b['arms']} diff {b['mean_diff']:+.6f} {b['direction_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
