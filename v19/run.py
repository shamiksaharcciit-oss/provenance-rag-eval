"""v1.9 — the run. Written after the freeze (`5bc4aeb`). Staged, so each gate can stop.

Stages, in the frozen order:
  probe    determinism, Track A dev only, cache-bypassed, fresh-call assertion, <= 500 calls
  control  PR-0 context ablation, BOTH tracks, before any test-set scoring is read
  main     packages + generation + scoring for the declared arms

The affordability check is branch-contingent and is re-run before `main`: the single-run branch
fits the guard, the targeted-repeat branch does not, and §6 makes a guard-aborting run a STOP for
a ruling rather than an edit.
"""
from __future__ import annotations

import argparse
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
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src import config as C  # noqa: E402
from src.v17.packages import build_package  # noqa: E402
from v19.arms import ARMS, PRIMARY_PAIR, assert_builder_identity, build_inventories, test_queries  # noqa: E402
from v19.control import CONTROL_N, b2_for_query, draw_control_sample, pair_with_successor  # noqa: E402
from v19.generate import V19Client, determinism_probe  # noqa: E402
from v19.packages import build_all, gold_delivery_costs  # noqa: E402
from v19.reading_scores import score_pair  # noqa: E402  (thin wrapper over the frozen scorers)

FREEZE = "5bc4aebea635fdc10d83c349d2a37486d1f337bf"
OUT = ROOT / "v19" / "results_run"
PROBE_N, PROBE_REPEATS = 20, 3


#: Plan §1 names ONE generator. It is pinned here from the plan, never resolved from config.
#:
#: The first probe took the model from `tcfg["llm"]["model"]` and ran on `claude-opus-4-8`:
#: the repo default is Opus 4.8 and Track A declares no override, so config resolution silently
#: substituted a different model than the freeze names. Worse, Track B's config DOES declare
#: `llm_model: claude-sonnet-5`, so config resolution would have run the two tracks on DIFFERENT
#: generators and made them incomparable. G5's pin caught it by logging `response.model`.
GENERATOR = "claude-sonnet-5"


def client(tcfg) -> V19Client:
    """A V19Client on the plan's generator, carrying the config's cost guard (never edited, §6)."""
    g = tcfg.get("cost_guard", {})
    llm = tcfg.get("llm", {})
    c = V19Client(provider="anthropic", model=GENERATOR,
                  temperature=llm.get("temperature", 0.0),
                  max_tokens=llm.get("max_tokens", 1024),
                  cache_dir=Path(tcfg["_cache_root"]) / "llm",
                  max_llm_calls=g.get("max_llm_calls", 100000),
                  max_usd=g.get("max_usd", 60.0))
    assert c.model == GENERATOR, (
        f"generator is {c.model!r}, plan §1 names {GENERATOR!r} — config resolution must never "
        f"choose the model for this experiment")
    return c


def load(track):
    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    cfg["llm"]["provider"] = "anthropic"
    ds, tcfg, built = build_inventories(track)
    tcfg = C.deep_merge(tcfg, {"_cache_root": cfg["_cache_root"]})
    dev, test = test_queries(ds, tcfg, track)
    return ds, tcfg, {a: built[a][0] for a in ARMS}, dev, test


def packages_for(invs, q, doc_text):
    b = b2_for_query(invs, q.gold_spans)
    r = build_all(invs, q.gold_spans, b["b2"])
    return b, r


def stage_probe(args):
    from v19.reading_scores import render
    ds, tcfg, invs, dev, _test = load("A")
    docs = {d.doc_id: d.text for d in ds.documents}
    sample = dev[:PROBE_N]
    prompts = []
    for q in sample:
        b, r = packages_for(invs, q, docs)
        prompts.append(render(r["packages"]["F768"].package.text, q.text))
    cl = client(tcfg)
    t0 = time.time()
    rec = determinism_probe(cl, prompts, repeats=PROBE_REPEATS, max_calls=500)
    assert cl.pin_record()["response_model_distinct"] == [GENERATOR], (
        f"APPARATUS-STOP: response.model {cl.pin_record()['response_model_distinct']} is not "
        f"[{GENERATOR!r}] (G5)")
    rec.update({"seconds": round(time.time() - t0, 1), "pin": cl.pin_record(),
                "anomalies": cl.anomaly_record(), "cost": cl.cost_summary(),
                "stage": "probe", "freeze": FREEZE})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "probe.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    print(f"  probe: {rec['verdict']}  fresh_calls={rec['fresh_calls']} "
          f"identical={rec['n_prompts_identical']}/{rec['n_prompts']}  {rec['seconds']:.0f}s")
    print(f"  pin: {rec['pin']['response_model_distinct']}  anomalies={rec['anomalies']['finish_reasons']}")
    print(f"  cost so far: {rec['cost']}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=("probe", "judge_probe", "control", "main", "pr3"))
    args = ap.parse_args(argv)
    assert_builder_identity()
    return {"probe": stage_probe, "judge_probe": stage_judge_probe,
            "control": stage_control, "main": stage_main, "pr3": stage_pr3}[args.stage](args)




# ---------------------------------------------------------------- judge

JUDGE_SYS = ("You compare two candidate answers against a reference. Reply with exactly one "
             "token: A if the first is better, B if the second is better, TIE if equal.")


def judge_prompt(question, gold, a, b):
    return (f"Question: {question}\n\nReference answer: {gold}\n\n"
            f"Candidate A:\n{a}\n\nCandidate B:\n{b}\n\nWhich is better? Reply A, B or TIE.")


def stage_judge_probe(args):
    """Judge determinism under the same cache-bypass protocol, within the remaining bound."""
    from v19.reading_scores import gold_text
    ds, tcfg, invs, dev, _t = load("A")
    docs = {d.doc_id: d.text for d in ds.documents}
    prompts = []
    for q in dev[:PROBE_N]:
        g = gold_text(docs[q.gold_spans[0].doc_id], q.gold_spans)
        prompts.append(judge_prompt(q.text, g, g, "The document does not say."))
    cl = client(tcfg)
    t0 = time.time()
    rec = determinism_probe(cl, prompts, repeats=PROBE_REPEATS, max_calls=440)  # 500 - 60 used
    assert cl.pin_record()["response_model_distinct"] == [GENERATOR], "APPARATUS-STOP (G5)"
    rec.update({"seconds": round(time.time() - t0, 1), "pin": cl.pin_record(),
                "anomalies": cl.anomaly_record(), "cost": cl.cost_summary(),
                "stage": "judge_probe", "freeze": FREEZE})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "judge_probe.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    print(f"  judge probe: {rec['verdict']}  fresh={rec['fresh_calls']} "
          f"identical={rec['n_prompts_identical']}/{rec['n_prompts']}  {rec['cost']['est_usd']}")
    return 0


# ---------------------------------------------------------------- PR-0 control

def stage_control(args):
    """PR-0 context ablation, BOTH tracks, before any test-set scoring is read."""
    from v19.reading_scores import gold_text, render, token_f1
    out = {"stage": "control", "freeze": FREEZE, "tracks": {}}
    total = 0.0
    for track in ("A", "B"):
        ds, tcfg, invs, _dev, test = load(track)
        docs = {d.doc_id: d.text for d in ds.documents}
        byid = {q.query_id: q for q in test}
        sample = draw_control_sample([q.query_id for q in test])
        pairs = pair_with_successor(sample)
        pkg = {}
        for qid in sample:
            q = byid[qid]
            b = b2_for_query(invs, q.gold_spans)
            pkg[qid] = build_all(invs, q.gold_spans, b["b2"])["packages"]["F768"].package.text
        cl = client(tcfg)
        rows = []
        for p in pairs:
            q = byid[p.query_id]
            g = gold_text(docs[q.gold_spans[0].doc_id], q.gold_spans)
            corr = cl.complete_uncached(render(pkg[p.query_id], q.text))
            mism = cl.complete_uncached(render(pkg[p.mismatched_package_of], q.text))
            rows.append({"query_id": p.query_id, "mismatched_package_of": p.mismatched_package_of,
                         "f1_correct": token_f1(corr, g), "f1_mismatched": token_f1(mism, g),
                         "answer_correct": corr[:300], "answer_mismatched": mism[:300]})
        assert cl.pin_record()["response_model_distinct"] == [GENERATOR], "APPARATUS-STOP (G5)"
        med = lambda xs: sorted(xs)[len(xs) // 2]
        mc, mm = med([r["f1_correct"] for r in rows]), med([r["f1_mismatched"] for r in rows])
        passes = mm < 0.2 and (mc - mm) > 0.3
        out["tracks"][track] = {"n": len(rows), "median_f1_correct": round(mc, 4),
                                "median_f1_mismatched": round(mm, 4), "gap": round(mc - mm, 4),
                                "criterion": "mismatched median < 0.2 AND gap > 0.3",
                                "PR0_passes": bool(passes), "rows": rows,
                                "pin": cl.pin_record(), "cost": cl.cost_summary()}
        total += cl.cost_summary()["est_usd"]
        print(f"  PR-0 track {track}: correct {mc:.3f} vs mismatched {mm:.3f}, gap {mc-mm:.3f} "
              f"-> {'PASS' if passes else 'FAIL (track quarantined)'}  est_usd {cl.cost_summary()['est_usd']}")
    both_fail = not any(v["PR0_passes"] for v in out["tracks"].values())
    out["APPARATUS_STOP"] = both_fail
    out["total_est_usd"] = round(total, 4)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "control.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    if both_fail:
        print("  BOTH TRACKS FAIL PR-0 -> APPARATUS-STOP: unmeasurable as designed.")
    return 0




# ---------------------------------------------------------------- main run

REPEAT_ARMS = {"A": ("F768", "U768")}      # G3: targeted repeats, Track A primary pair only


def median(xs):
    s = sorted(xs)
    return s[len(s) // 2]


def stage_main(args):
    from src.v17.e1 import contrast
    from src.stats.tests import paired_bootstrap_diff, paired_permutation_p
    from v19.reading_scores import (exact_containment, gold_text, is_not_found, render, token_f1)

    ctrl = json.loads((OUT / "control.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {"stage": "main", "freeze": FREEZE, "branch": "targeted_repeats",
               "repeat_arms": REPEAT_ARMS, "tracks": {}}

    for track in ("A", "B"):
        quarantined = not ctrl["tracks"][track]["PR0_passes"]
        ds, tcfg, invs, _dev, test = load(track)
        docs = {d.doc_id: d.text for d in ds.documents}
        cl = client(tcfg)
        rows, t0 = [], time.time()
        for i, q in enumerate(test):
            g = gold_text(docs[q.gold_spans[0].doc_id], q.gold_spans)
            b = b2_for_query(invs, q.gold_spans)
            built = build_all(invs, q.gold_spans, b["b2"])
            rec = {"query_id": q.query_id, "b2": b["b2"], "escalated": b["escalated"],
                   "set_by": b["set_by"], "T_a": b["costs"],
                   "tokens": built["tokens"], "shortfalls": built["shortfalls"], "arms": {}}
            for arm in ARMS:
                pkg = built["packages"][arm].package.text
                reps = 3 if arm in REPEAT_ARMS.get(track, ()) else 1
                ans = [cl.complete_uncached(render(pkg, q.text)) for _ in range(reps)]
                f1s = [token_f1(a, g) for a in ans]
                rec["arms"][arm] = {"repeats": reps, "f1": median(f1s), "f1_all": f1s,
                                    "contain": exact_containment(ans[0], g),
                                    "not_found": is_not_found(ans[0]), "answer": ans[0][:400]}
            rows.append(rec)
            if (i + 1) % 25 == 0:
                (OUT / f"main_{track}.json").write_text(json.dumps(
                    {"track": track, "rows": rows, "cost": cl.cost_summary()}, indent=2),
                    encoding="utf-8")
                print(f"    {track} {i+1}/{len(test)}  est_usd {cl.cost_summary()['est_usd']}",
                      flush=True)
        assert cl.pin_record()["response_model_distinct"] == [GENERATOR], "APPARATUS-STOP (G5)"
        n = len(rows)
        a = [r["arms"]["F768"]["f1"] for r in rows]
        bb = [r["arms"]["U768"]["f1"] for r in rows]
        d = [x - y for x, y in zip(a, bb)]
        bs = paired_bootstrap_diff(a, bb, 10000, 1337, 0.95)
        res = {"n": n, "quarantined": quarantined,
               "mean_f1": {arm: round(sum(r["arms"][arm]["f1"] for r in rows) / n, 6)
                           for arm in ARMS},
               "contain": {arm: sum(r["arms"][arm]["contain"] for r in rows) for arm in ARMS},
               "not_found": {arm: sum(r["arms"][arm]["not_found"] for r in rows) for arm in ARMS},
               "F_READ2": {"mean_diff": round(bs["mean_diff"], 6),
                           "ci95": [round(x, 6) for x in bs["ci95"]],
                           "p_permutation": round(paired_permutation_p(a, bb, 10000, 1337), 6),
                           "direction_counts": {"F768_higher": sum(1 for x in d if x > 0),
                                                "U768_higher": sum(1 for x in d if x < 0),
                                                "tied": sum(1 for x in d if x == 0)}},
               "pin": cl.pin_record(), "cost": cl.cost_summary(),
               "seconds": round(time.time() - t0, 1)}
        (OUT / f"main_{track}.json").write_text(json.dumps(
            {"track": track, "summary": res, "rows": rows}, indent=2), encoding="utf-8")
        summary["tracks"][track] = res
        (OUT / "main_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"  {track}: mean F1 {res['mean_f1']} | F_READ2 {res['F_READ2']['mean_diff']:+.4f} "
              f"CI{res['F_READ2']['ci95']} p={res['F_READ2']['p_permutation']} "
              f"dir {res['F_READ2']['direction_counts']} | quarantined={quarantined} "
              f"est_usd {res['cost']['est_usd']}", flush=True)
    return 0




# ------------------------------------------------- PR-3 supplement (post-STOP, by ruling)

def stage_pr3(args):
    """PR-3, per Decisions_v19_PR3_2026-08-02.md §3. Track A primary pair only.

    Step 1 REGENERATE F768/U768 at 3 reps per arm, PERSISTING EVERY REP'S TEXT. The main run
      kept only the median F1 and rep 0's text, which made rep-pairing by index impossible --
      the persistence defect this supplement exists to work around.
    Step 2 score token-F1 on the regenerated answers, locally and free, frozen normalisation.
      PR-1 IS UNTOUCHED: its scores stand as scored. These F1 values exist SOLELY as PR-3's
      reference, because the agreement comparison must run on identical answers and these are
      new draws.
    Step 3 judge each rep-pair ONCE, paired by index -- 3 judge calls per query over the JOINT
      draw (the G13 logic), not one pair judged three times.
    Step 4 PR-3 scored as sealed on this answer set.
    """
    import random
    from v19.reading_scores import gold_text, render, token_f1

    ds, tcfg, invs, _dev, test = load("A")
    docs = {d.doc_id: d.text for d in ds.documents}
    cl = client(tcfg)
    rows, t0 = [], time.time()

    for i, q in enumerate(test):
        g = gold_text(docs[q.gold_spans[0].doc_id], q.gold_spans)
        b = b2_for_query(invs, q.gold_spans)
        built = build_all(invs, q.gold_spans, b["b2"])
        # --- step 1+2: regenerate all reps, persist every text, score locally
        reps = {}
        for arm in PRIMARY_PAIR:
            pkg = built["packages"][arm].package.text
            texts = [cl.complete_uncached(render(pkg, q.text)) for _ in range(3)]
            reps[arm] = {"answers": texts, "f1": [token_f1(a, g) for a in texts]}
        # --- step 3: judge each rep-pair once, paired by INDEX
        verdicts = []
        for r in range(3):
            rng = random.Random(f"1337:{q.query_id}:{r}")
            f_first = rng.random() < 0.5
            fa, ua = reps["F768"]["answers"][r], reps["U768"]["answers"][r]
            a, bb = (fa, ua) if f_first else (ua, fa)
            v = cl.complete_uncached(judge_prompt(q.text, g, a, bb), system=JUDGE_SYS).strip().upper()
            tok = "TIE"
            if v.startswith("A"):
                tok = "F768" if f_first else "U768"
            elif v.startswith("B"):
                tok = "U768" if f_first else "F768"
            verdicts.append(tok)
        counts = {k: verdicts.count(k) for k in set(verdicts)}
        top = max(counts.values())
        win = sorted(k for k, c in counts.items() if c == top)
        jdir = win[0] if len(win) == 1 else "TIE"
        med = lambda xs: sorted(xs)[len(xs) // 2]
        fd = med(reps["F768"]["f1"]) - med(reps["U768"]["f1"])
        rows.append({"query_id": q.query_id, "verdicts": verdicts, "judge_direction": jdir,
                     "supp_f1_F768": med(reps["F768"]["f1"]), "supp_f1_U768": med(reps["U768"]["f1"]),
                     "supp_f1_diff": fd,
                     "f1_direction": "F768" if fd > 0 else ("U768" if fd < 0 else "TIE"),
                     "reps": reps})
        if (i + 1) % 20 == 0:
            (OUT / "pr3_partial.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
            print(f"    pr3 {i+1}/{len(test)} calls={cl.cost_summary()['llm_calls']} "
                  f"est_usd {cl.cost_summary()['est_usd']}", flush=True)

    assert cl.pin_record()["response_model_distinct"] == [GENERATOR], "APPARATUS-STOP (G5)"
    n = len(rows)
    agree = sum(1 for r in rows if r["judge_direction"] == r["f1_direction"])
    jf = sum(1 for r in rows if r["judge_direction"] == "F768")
    ju = sum(1 for r in rows if r["judge_direction"] == "U768")
    bias = sum(1 for r in rows if r["judge_direction"] == "F768" and r["f1_direction"] != "F768")
    supp_mean = {a: round(sum(r[f"supp_f1_{a}"] for r in rows) / n, 6) for a in PRIMARY_PAIR}
    rec = {"stage": "pr3_supplement", "freeze": FREEZE,
           "executed_post_stop_by": "Decisions_v19_PR3_2026-08-02.md §3",
           "answer_set": "DISJOINT from PR-1's draws — regenerated; PR-1 untouched",
           "n": n, "calls": cl.cost_summary()["llm_calls"],
           "judge_direction_counts": {"F768": jf, "U768": ju, "TIE": n - jf - ju},
           "agreement_with_f1": agree, "agreement_rate": round(agree / n, 4),
           "bias_signature_count": bias,
           "_bias_note": "judge favours F768 while F1 does not = bias signature, not support",
           "supplement_mean_f1": supp_mean,
           "supplement_mean_diff": round(supp_mean["F768"] - supp_mean["U768"], 6),
           "_reproduction_note": ("descriptive reproduction observation across INDEPENDENT draws; "
                                  "the nondeterminism verdict predicts it will not equal PR-1's "
                                  "+0.110581 exactly. PR-1 is not re-scored."),
           "pin": cl.pin_record(), "anomalies": cl.anomaly_record(),
           "cost": cl.cost_summary(), "seconds": round(time.time() - t0, 1), "rows": rows}
    (OUT / "pr3.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    print(f"  PR-3: judge F768 {jf} / U768 {ju} / TIE {n-jf-ju} | agreement {agree}/{n} "
          f"({rec['agreement_rate']:.1%}) | bias-signature {bias}")
    print(f"  supplement mean F1 {supp_mean} diff {rec['supplement_mean_diff']:+.6f} "
          f"(PR-1 was +0.110581, NOT re-scored)")
    print(f"  calls {rec['calls']} est_usd {rec['cost']['est_usd']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
