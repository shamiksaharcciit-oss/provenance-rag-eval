"""v1.8 — score the collected batches into I1, I2, and `F_BIAS`. Runs only after J2 collects.

    python -m v18.score_run

This is the first module in the run allowed to derive numbers from judge output. Everything
before it — the builders, the collection steps — was held to counts, pins and triage, because
the results document is assembled once and reading signal early is how a pre-registration turns
into a search.

Structure follows the frozen instruments, not convenience:

* **I1** — the five RAGAS-class metrics, computed by `instruments.py`'s frozen formulas from the
  judge rows. Answer-level metrics are computed **per generated answer** and medianed;
  context-level metrics are single-judgement (PF-14).
* **I2** — token-F1 against the gold span text, imported from `src.v17.reading` by citation.
* **B1** — per-answer pairing, `analysis.b1_for_query`: difference first, median second.
* **I3** contributes nothing computed here. v1.6's record is quoted with hashes, never
  recomputed (§3).

`answer_relevancy` needs cosine similarity between each reverse-engineered question and the real
one; that uses the local MiniLM encoder, so it costs nothing and involves no judge.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from v18.analysis import assemble_query_arm, b1_for_query, median
from v18.batch import custom_id
from v18.contrasts import F_BIAS, context_contrast_table, descriptive_contrast, holm_family
from v18.contrasts import tested_contrast as family_stat
from v18.instruments import (JudgeReplyError, _verdict_list, answer_correctness,
                             answer_relevancy, context_precision, context_recall, faithfulness,
                             parse_json_object, split_reference_sentences, token_f1)
from v18.judge_prompts import ANSWER_RELEVANCY_STRICTNESS, FIXED_K
from v18.run import (ARMS, OUT, TRACKS, _load, build_inventories, migrate_answers, reps_for)

ROOT = Path(__file__).resolve().parents[1]

from src.index.embed import Embedder  # noqa: E402
from src.v17.reading import gold_text  # noqa: E402


def _cos(a, b) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb)) if na and nb else 0.0


def score(log) -> dict:
    inv = build_inventories(log)
    gen = migrate_answers(json.loads((OUT / "answers_G.json").read_text(encoding="utf-8")))
    j1 = json.loads((OUT / "replies_j1.json").read_text(encoding="utf-8"))
    j2 = json.loads((OUT / "replies_j2.json").read_text(encoding="utf-8"))
    log(f"  rows: gen {len(gen):,} · j1 {len(j1):,} · j2 {len(j2):,}")

    tcfg, _, _ = _load("A")
    embedder = Embedder(tcfg, cache_root=tcfg["_cache_root"])

    per_cell: dict = {}
    i2: dict = {}
    parse_failures: list[str] = []

    for track in TRACKS:
        _tc, ds, _tq = _load(track)
        doc_text = {d.doc_id: d.text for d in ds.documents}
        for arm in ARMS:
            for rec, q in zip(inv[track]["contexts"][arm], inv[track]["queries"]):
                ref = gold_text(doc_text[q.gold_spans[0].doc_id], q.gold_spans)
                R = reps_for(track, arm)

                def cid(stage, metric, a=0, s=0):
                    return custom_id(stage, track, arm, q.query_id, metric, a, s)

                try:
                    cp = [int(parse_json_object(
                        j1[cid("judge1", "context_precision", 0, s)],
                        expected_keys={"verdict"})["verdict"]) for s in range(FIXED_K)]
                    n_sent = len(split_reference_sentences(ref))
                    cr = _verdict_list(j1[cid("judge1", "context_recall")], "verdicts", n_sent)
                    ctx_vals = {"context_precision": context_precision(cp),
                                "context_recall": context_recall(cr)}

                    qvec = embedder.encode([q.text])[0]
                    by_rep = {}
                    for a in range(R):
                        stmts = parse_json_object(
                            j1[cid("judge1", "faithfulness", a)],
                            expected_keys={"statements"})["statements"] or ["(none)"]
                        fv = _verdict_list(j2[cid("judge2", "faithfulness", a)],
                                           "verdicts", len(stmts))
                        gen_qs = [parse_json_object(
                            j1[cid("judge1", "answer_relevancy", a, s)],
                            expected_keys={"question"})["question"]
                            for s in range(ANSWER_RELEVANCY_STRICTNESS)]
                        sims = [_cos(qvec, v) for v in embedder.encode(gen_qs)]
                        acc = parse_json_object(j1[cid("judge1", "answer_correctness", a)],
                                                expected_keys={"TP", "FP", "FN"})
                        ans_text = gen[custom_id(
                            "generate", track, arm, q.query_id, None, a, 0)]
                        a_sim = _cos(qvec, embedder.encode([ans_text])[0])
                        by_rep[a] = {
                            "faithfulness": faithfulness(fv),
                            "answer_relevancy": answer_relevancy(sims),
                            "answer_correctness": answer_correctness(
                                int(acc["TP"]), int(acc["FP"]), int(acc["FN"]), a_sim),
                        }
                        i2[(track, arm, q.query_id, a)] = token_f1(ans_text, ref)
                    per_cell[(track, arm, q.query_id)] = assemble_query_arm(by_rep, ctx_vals)
                except (JudgeReplyError, KeyError, ValueError) as e:
                    parse_failures.append(f"{track}/{arm}/{q.query_id}: {type(e).__name__}: {e}")

    return {"per_cell": per_cell, "i2": i2, "parse_failures": parse_failures,
            "inventories": inv}


def contrasts(per_cell, i2, log) -> dict:
    """`F_BIAS` (B1 alone) plus every descriptive companion, per track."""
    out = {}
    for track in TRACKS:
        qids = [q.query_id for q in _load(track)[2]]
        ctx = {arm: [per_cell[(track, arm, q)]["context_composite"] for q in qids]
               for arm in ARMS}
        out[f"context_contrasts_{track}"] = context_contrast_table(
            ctx["F768"], ctx["U768"], ctx["U256"])
        ans = {arm: [per_cell[(track, arm, q)]["answer_composite"] for q in qids]
               for arm in ARMS}
        out[f"answer_contrasts_{track}"] = {
            "F768_minus_U256": descriptive_contrast(ans["F768"], ans["U256"]),
            "U768_minus_U256": descriptive_contrast(ans["U768"], ans["U256"]),
            "F768_minus_U768": descriptive_contrast(ans["F768"], ans["U768"])}

        b1 = []
        for q in qids:
            R = reps_for(track, "F768")
            jf = [per_cell[(track, "F768", q)]["answer_composite_by_rep"][r] for r in range(R)]
            ju = [per_cell[(track, "U768", q)]["answer_composite_by_rep"][r] for r in range(R)]
            ff = [i2[(track, "F768", q, r)] for r in range(R)]
            fu = [i2[(track, "U768", q, r)] for r in range(R)]
            b1.append(b1_for_query(jf, ju, ff, fu))
        out[f"B1_{track}"] = family_stat(b1)
        def i2_med(arm):
            """Per-query I2: median token-F1 over the judged answers (PF-3/PF-14)."""
            return [median([i2[(track, arm, q, r)] for r in range(reps_for(track, arm))])
                    for q in qids]

        out[f"i2_contrasts_{track}"] = {
            "F768_minus_U768": descriptive_contrast(i2_med("F768"), i2_med("U768")),
            "F768_minus_U256": descriptive_contrast(i2_med("F768"), i2_med("U256")),
            "U768_minus_U256": descriptive_contrast(i2_med("U768"), i2_med("U256"))}

    # F_BIAS is Track A only, one member; Holm over one member is the identity.
    out["F_BIAS"] = holm_family({"B1": out["B1_A"]["p_permutation"]})
    return out


def main(argv=None) -> int:
    log = lambda m: print(m, flush=True)
    log("v1.8 scoring — I1, I2, B1. First numbers derived from judge output.\n")
    s = score(log)
    if s["parse_failures"]:
        log(f"  PARSE FAILURES: {len(s['parse_failures'])} cell(s)")
        for f in s["parse_failures"][:10]:
            log(f"    {f}")
        log("  STOP — a cell that cannot be scored must not be silently dropped; n is declared.")
        (OUT / "scoring_failures.json").write_text(
            json.dumps(s["parse_failures"], indent=2), encoding="utf-8")
        return 1
    c = contrasts(s["per_cell"], s["i2"], log)
    payload = {"n_cells": len(s["per_cell"]), "contrasts": c}
    (OUT / "scored.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    log(f"\n  scored cells: {len(s['per_cell']):,}")
    log(f"  wrote {OUT / 'scored.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
