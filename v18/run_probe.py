"""v1.8 §2 — execute the determinism probes on Track A dev, within the 1,000-call bound.

Run: `python -m v18.run_probe`

This is step 3 of `Decisions_v18_Gate0_2026-08-01.md` §10. It spends, on the **dev split only**,
under PF-1's authorisation and PF-1's ceiling. It touches no test query.

**Budget arithmetic, fixed here and asserted before anything is spent (PF-1: 1,000 calls):**

    generation :  20 dev queries x 3 arms x 3 repeats                   =  180
    answers    :   7 dev queries x 2 arms, single call each             =   14
    judging    :   7 dev queries x 2 arms (F768/U768) x 12 calls x 3    =  504
                                                                   total   698

**Prior spend against the same bound is indeterminate, so the worst case is assumed.** Two
earlier attempts spent: 1 auth check, 3 sampling-parameter checks, 60 on an aborted generation
probe whose bypass failed (`probe.py`), and an unknown number on a second attempt that died on
`credit balance too low` — bounded above by 180. Plus 1 credit re-check. Worst case
245 + 698 = 943 of 1,000. PF-1 is a hard bound, so the unknown is resolved against us.

**Why the judge probe shrank from the 10 queries first drafted.** Only the generation probe's
size is fixed by §2 ("20 dev queries"); the judge probe's was never specified, so it absorbs the
reductions rather than the mandated one. Detection power is not the binding constraint here: the
run executes at the model's *default* sampling (finding G9 — `claude-sonnet-5` rejects
`temperature` outright), and divergence under default sampling shows up in the first handful of
prompts if it shows up at all.

The judge probe covers both arms of the pair `F_BIAS` consumes rather than one arm at twice the
queries. Same call cost, same number of distinct prompts, and it exercises the two arms whose
comparison B1 *is*.

The answer calls are not a probe: the judge prompts need an answer to judge, and `run_probe`
returns verdicts rather than transcripts. One fresh call per needed (query, arm) is the smaller
honest cost, and it is counted here rather than hidden.

Determinism is a property of the sampler, not the corpus (PF-6), so Track A's verdict governs
Track B — stated as an assumption, with that reason, and restated in the results document.

Nothing here scores an arm. The probe answers one question — do repeats agree byte for byte —
and its answer selects the branch §2's targeted fallback specifies.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from v18.arms import ARMS, FIXED_K, build_arm, retrieve_fixed_k
from v18.cost import project
from v18.instruments import split_reference_sentences
from v18.judge_prompts import (ANSWER_CORRECTNESS_PROMPT, ANSWER_RELEVANCY_PROMPT,
                               ANSWER_RELEVANCY_STRICTNESS, CONTEXT_PRECISION_PROMPT,
                               CONTEXT_RECALL_PROMPT, FAITHFULNESS_STATEMENTS_PROMPT,
                               FAITHFULNESS_VERDICTS_PROMPT, JUDGE_SYSTEM, render)
from v18.probe import PROBE_CALL_BUDGET, PROBE_REPEATS, ProbeClient, run_probe

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "v18" / "results_gate0"

from src import config as C  # noqa: E402
from src.chunkers.base import ChunkContext  # noqa: E402
from src.datasets import load_track_dataset  # noqa: E402
from src.index.embed import Embedder  # noqa: E402
from src.llm.client import LLMClient, build_llm  # noqa: E402
from src.run import split_dev_test  # noqa: E402
from src.v17.reading import gold_text, render_prompt  # noqa: E402  (frozen at e19dd35)

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

#: §2 generator and §3 judge. **This is not the harness default and must never be inherited.**
#: `config/default.yaml` sets `llm.model: claude-opus-4-8`, and `config/tracks/A.yaml` carries no
#: `llm_model` override ("Track A stays Opus/cached"). That default is CORRECT for building the
#: arms — the formatter's cached output must reproduce v1.6 byte for byte — and WRONG for v1.8's
#: generation and judging, which §2/§3 pin to `claude-sonnet-5` on both tracks.
#:
#: The first probe run conflated the two roles through a single config and measured determinism
#: on `claude-opus-4-8` (finding G11). `probe_config()` separates them, and `ProbeClient`'s
#: `requested_model` is asserted below so an inherited default fails loudly rather than producing
#: a confident number about the wrong model.
V18_CALL_MODEL = "claude-sonnet-5"


def probe_config(tcfg: dict) -> dict:
    """A copy of the run config with the generation/judging model pinned to §2's choice."""
    return C.deep_merge(tcfg, {"llm": {"model": V18_CALL_MODEL}})

#: §2 probe scope. Held as constants so the budget assertion below reads off the real values.
GEN_QUERIES = 20
JUDGE_QUERIES = 7
JUDGE_ARMS = ("F768", "U768")
CONTEXT_SEPARATOR = "\n\n"


def _numbered(items: list[str]) -> str:
    return "\n".join(f"{i}. {t}" for i, t in enumerate(items, 1))


def judge_prompts_for(question: str, reference: str, contexts: list[str],
                      answer: str) -> list[tuple[str, str]]:
    """The twelve judge prompts for one (query, arm), in the order `CALLS_PER_QUERY_ARM` counts.

    Built from the frozen templates only — this function chooses no wording. The two-stage
    metrics (faithfulness) use a placeholder statement list for the *verdicts* prompt, because
    the probe measures reply stability for a fixed prompt and must not depend on the first
    stage's reply to construct the second (which would confound sampler variance with
    prompt variance).
    """
    joined = CONTEXT_SEPARATOR.join(contexts)
    sentences = split_reference_sentences(reference)
    placeholder_statements = [answer.strip() or "(no claim)"]

    prompts = [
        *[(JUDGE_SYSTEM, render(CONTEXT_PRECISION_PROMPT, question=question,
                                reference=reference, context=ctx)) for ctx in contexts],
        (JUDGE_SYSTEM, render(CONTEXT_RECALL_PROMPT, question=question, context=joined,
                              sentences=_numbered(sentences))),
        (JUDGE_SYSTEM, render(FAITHFULNESS_STATEMENTS_PROMPT, question=question, answer=answer)),
        (JUDGE_SYSTEM, render(FAITHFULNESS_VERDICTS_PROMPT, context=joined,
                              statements=_numbered(placeholder_statements))),
        *[(JUDGE_SYSTEM, render(ANSWER_RELEVANCY_PROMPT, answer=answer))
          for _ in range(ANSWER_RELEVANCY_STRICTNESS)],
        (JUDGE_SYSTEM, render(ANSWER_CORRECTNESS_PROMPT, question=question, answer=answer,
                              reference=reference)),
    ]
    assert len(prompts) == FIXED_K + 1 + 2 + ANSWER_RELEVANCY_STRICTNESS + 1 == 12
    return prompts


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-generation", action="store_true",
                    help="the generation probe already returned a verdict; do not re-spend it")
    ap.add_argument("--judge-queries", type=int, default=JUDGE_QUERIES)
    ap.add_argument("--judge-arms", default=",".join(JUDGE_ARMS))
    args = ap.parse_args(argv)
    judge_queries = args.judge_queries
    judge_arms = tuple(a for a in args.judge_arms.split(",") if a)

    log = lambda m: print(m, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)

    gen_planned = 0 if args.skip_generation else GEN_QUERIES * len(ARMS) * PROBE_REPEATS
    planned = (gen_planned
               + judge_queries * len(judge_arms)                            # answers to judge
               + judge_queries * len(judge_arms) * 12 * PROBE_REPEATS)      # judge probe
    assert planned <= PROBE_CALL_BUDGET, (
        f"planned probe spend {planned} exceeds the {PROBE_CALL_BUDGET}-call bound (PF-1)")
    log(f"v1.8 determinism probe · Track A dev only · planned {planned} calls "
        f"(bound {PROBE_CALL_BUDGET})\n")

    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    cfg["llm"]["provider"] = "anthropic"
    cfg["embedding"]["model"] = EMBEDDING_MODEL
    traw = C.load_track("A")
    tm = traw.get("params", {}).get("llm_model")
    tcfg = C.deep_merge(cfg, {"llm": {"model": tm}}) if tm else cfg

    # Two model roles, deliberately different (see V18_CALL_MODEL). `tcfg` builds the arms at
    # the track default so they reproduce v1.6; `pcfg` makes every generation/judging call at
    # §2's pinned model.
    pcfg = probe_config(tcfg)
    assert pcfg["llm"]["model"] == V18_CALL_MODEL, "probe config lost its model pin"
    log(f"  arm-construction model: {tcfg['llm']['model']} (track default, reproduces v1.6)")
    log(f"  generation/judging model: {pcfg['llm']['model']} (§2/§3 pin)")

    ds = load_track_dataset(traw, tcfg["seed"])
    dev_frac = traw.get("params", {}).get("dev_fraction")
    dev_frac = dev_frac if dev_frac is not None else tcfg.get("sweep", {}).get("dev_fraction", 0.2)
    dev_q, _test_q = split_dev_test(ds, dev_frac, tcfg["seed"])
    assert len(dev_q) >= GEN_QUERIES, f"Track A dev has {len(dev_q)} queries, need {GEN_QUERIES}"
    dev_q = dev_q[:GEN_QUERIES]
    doc_text = {d.doc_id: d.text for d in ds.documents}
    log(f"  Track A dev: using {len(dev_q)} of {dev_frac:.0%} split; no test query is touched")

    embedder = Embedder(tcfg, cache_root=tcfg["_cache_root"])
    build_llm_client = build_llm(tcfg)
    ctx_full = ChunkContext(embedder=embedder, llm=build_llm_client, config=tcfg)
    ctx_det = ChunkContext(embedder=embedder, llm=LLMClient(provider="none"), config=tcfg)

    retrieved: dict[str, list[dict]] = {}
    for arm in ARMS:
        units, _rungs, _diag = build_arm(arm, ds, ctx_full, ctx_det)
        retrieved[arm] = retrieve_fixed_k(units, dev_q, embedder, tcfg, FIXED_K)
        log(f"  {arm:6} dev contexts built ({len(units)} units)")
    assert build_llm_client.calls == 0, (
        f"SPEND STOP: arm construction made {build_llm_client.calls} fresh calls")

    # ---------------------------------------------------------------- generation probe
    gen_prompts: list[tuple[str, str]] = []
    index: list[tuple[str, str]] = []
    for arm in ARMS:
        for rec, q in zip(retrieved[arm], dev_q):
            package = CONTEXT_SEPARATOR.join(rec["contexts"])
            gen_prompts.append(("", render_prompt(package, q.text)))
            index.append((arm, q.query_id))

    gen = None
    if args.skip_generation:
        log("\n  generation probe: SKIPPED (verdict already obtained; not re-spent)")
    else:
        gen_client = ProbeClient(pcfg)
        try:
            log(f"\n  generation probe: {len(gen_prompts)} prompts x {PROBE_REPEATS} repeats")
            gen = run_probe(gen_prompts, gen_client, PROBE_REPEATS)
        finally:
            gen_client.dispose()
        assert gen["requested_model"] == V18_CALL_MODEL, (
            f"G11 GUARD: generation probe ran on {gen['requested_model']!r}, not "
            f"{V18_CALL_MODEL!r}. The verdict describes the wrong model.")
        log(f"    byte_identical={gen['byte_identical']} fresh={gen['fresh_calls']} "
            f"divergent={gen['n_divergent']}/{gen['prompts']}")

        # §A2 — persist at the moment it exists, not at the end. The first run of this script
        # wrote only after the judge probe, so when that stage died on a billing error it
        # discarded a COMPLETED generation probe worth 180 calls. A stage that has produced its
        # answer must not be hostage to a later stage's failure.
        (OUT / "probe_generation.json").write_text(
            json.dumps({"stage": "GENERATION_PROBE", "track": "A (dev only)",
                        "result": gen,
                        "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                       indent=2), encoding="utf-8")
        log(f"    persisted -> {OUT / 'probe_generation.json'}")

    # The judge probe needs an answer to judge. `run_probe` returns verdicts, not transcripts,
    # so one fresh call per needed (query, arm) supplies them — counted in the budget above.
    answers: dict[tuple[str, str], str] = {}
    judge_pairs = [(arm, rec, q) for arm in judge_arms
                   for rec, q in list(zip(retrieved[arm], dev_q))[:judge_queries]]

    ans_client = ProbeClient(pcfg, budget=planned)
    try:
        for arm, rec, q in judge_pairs:
            package = CONTEXT_SEPARATOR.join(rec["contexts"])
            answers[(arm, q.query_id)] = ans_client.complete(render_prompt(package, q.text))
        answer_calls = ans_client.fresh_calls
    finally:
        ans_client.dispose()
    log(f"  answers for the judge probe: {answer_calls} calls")

    # ---------------------------------------------------------------- judge probe
    jp: list[tuple[str, str]] = []
    for arm, rec, q in judge_pairs:
        reference = gold_text(doc_text[q.gold_spans[0].doc_id], q.gold_spans)
        jp += judge_prompts_for(q.text, reference, rec["contexts"],
                                answers[(arm, q.query_id)])

    remaining = planned - answer_calls
    judge_client = ProbeClient(pcfg, budget=remaining)
    try:
        log(f"\n  judge probe: {len(jp)} prompts x {PROBE_REPEATS} repeats "
            f"(budget remaining {remaining})")
        judge = run_probe(jp, judge_client, PROBE_REPEATS)
    finally:
        judge_client.dispose()
    assert judge["requested_model"] == V18_CALL_MODEL, (
        f"G11 GUARD: judge probe ran on {judge['requested_model']!r}, not {V18_CALL_MODEL!r}. "
        f"The verdict describes the wrong model.")
    log(f"    byte_identical={judge['byte_identical']} fresh={judge['fresh_calls']} "
        f"divergent={judge['n_divergent']}/{judge['prompts']}")
    (OUT / "probe_judge.json").write_text(
        json.dumps({"stage": "JUDGE_PROBE", "track": "A (dev only)",
                    "result": judge, "answer_generation_calls": answer_calls,
                    "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                   indent=2), encoding="utf-8")
    log(f"    persisted -> {OUT / 'probe_judge.json'}")

    # ---------------------------------------------------------------- branch + projection
    n_by_track = {"track_A": 176, "track_B": 150}
    projection = project(n_by_track, n_arms=len(ARMS))
    gen_identical = gen["byte_identical"] if gen else None
    branch = ("single_run" if gen_identical and judge["byte_identical"]
              else "targeted_repeats")

    total_spent = (gen["fresh_calls"] if gen else 0) + answer_calls + judge["fresh_calls"]
    out = {
        "stage": "PROBE", "track": "A (dev only)",
        "planned_calls": planned, "bound": PROBE_CALL_BUDGET, "actual_calls": total_spent,
        "generation_probe": gen or "SKIPPED — verdict from probe_generation.json / run log",
        "judge_probe": judge,
        "judge_scope": {"queries": judge_queries, "arms": list(judge_arms),
                        "_note": "reduced under PF-1; see module docstring"},
        "answer_generation_calls": answer_calls,
        "requested_model": judge["requested_model"],
        "_served_model_note": judge["_served_model_note"],
        "selected_branch": branch,
        "projection_single_run": projection["branch_single_run"],
        "cross_track_assumption": (
            "Track A's verdict governs Track B: nondeterminism at fixed parameters is a "
            "property of the sampler, not the corpus (PF-6). Track B has no dev split."),
        "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (OUT / "probe_results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    log(f"\n  branch selected: {branch}")
    log(f"  probe spend: {total_spent}/{PROBE_CALL_BUDGET}")
    log(f"wrote {OUT / 'probe_results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
