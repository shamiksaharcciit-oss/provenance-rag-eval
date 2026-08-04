"""v1.8 — the data collection run, in Batch API stages (PF-12 §1).

    python -m v18.run generate     # Batch G: submit + collect all generation
    python -m v18.run judge        # Batch J: submit + collect all judging (needs G)

Stage order is forced by data dependency only: judging needs answers, so Batch J cannot be
built until Batch G is collected. Nothing else about the order is a choice.

**No peeking between stages (PF-12 §7).** Between G and J this module performs mechanical
checks only — row counts, model constancy, resubmission triage. It does not score, summarise,
or print any per-arm signal, and neither should anyone reading its output. Token-F1 is computed
in the `judge` stage because that is where it is *needed* (to build B1), not withheld as
ceremony; the results document is assembled once, after J.

Two model roles, never conflated (PF-11):

* arms are built at the **track default** — Opus, cached, reproducing v1.6 byte for byte;
* every generation and judging call is made at **`V18_CALL_MODEL`**, asserted per call.

That distinction is the whole of G11: the Gate 0 probe inherited one config for both and spent
254 calls measuring the wrong model.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

from v18.arms import ARMS, FIXED_K, build_arm, retrieve_fixed_k
from v18.batch import BatchRunner, build_requests, custom_id, parse_custom_id
from v18.client import V18_CALL_MODEL, V18Client
from v18.judge_build import build_j1, build_j2
from v18.ledger import SpendLedger

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "v18" / "results_run"

from src import config as C  # noqa: E402
from src.chunkers.base import ChunkContext  # noqa: E402
from src.datasets import load_track_dataset  # noqa: E402
from src.index.embed import Embedder  # noqa: E402
from src.llm.client import LLMClient, build_llm  # noqa: E402
from src.run import split_dev_test  # noqa: E402
from src.v17.reading import render_prompt  # noqa: E402  (frozen at e19dd35)

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TRACKS = ("A", "B")
CONTEXT_SEPARATOR = "\n\n"

#: PF-3 — repeats protect the tested family only: the pair B1 consumes.
REPEAT_TRACK = "A"
REPEAT_ARMS = ("F768", "U768")
N_REPEATS = 3

#: Rough per-call cost for the affordability check only. Not the guard, not a projection of
#: record — the call ceiling is the frozen gate (§6).
USD_PER_CALL_BATCH_ESTIMATE = 0.0018


# --------------------------------------------------------------- PF-15 id migration


#: Batch G was submitted under PF-13's seven-field grammar; PF-15 added the `a`/`s` coordinates.
#: G14 §5 keeps those 1,682 rows valid, so their ids are re-keyed rather than re-spent.
_PF13_GEN_ID = re.compile(
    r"^v18-g-(?P<track>[AB])-(?P<arm>u256|u768|f768)-q(?P<idx>\d{3})-na-r(?P<rep>\d)$")


def migrate_generation_id(old: str) -> str:
    """`...-na-r{n}` -> `...-na-a{n}-s0`. A pure relabelling: same cell, same answer index.

    The raw batch rows on disk are NOT rewritten — they are the record, and they keep the ids
    the API actually saw. This migrates the derived answer index only, and asserts the mapping
    is total and injective before anything downstream consumes it.
    """
    m = _PF13_GEN_ID.match(old)
    if not m:
        return old                      # already eight-field
    return (f"v18-g-{m['track']}-{m['arm']}-q{m['idx']}-na-a{m['rep']}-s0")


def migrate_answers(answers: dict) -> dict:
    """Re-key a whole answers map, refusing anything that would collide or lose a row."""
    out = {migrate_generation_id(k): v for k, v in answers.items()}
    assert len(out) == len(answers), (
        f"generation-id migration was not injective: {len(answers)} -> {len(out)}")
    for k in out:
        parse_custom_id(k)              # must parse under the current grammar
    return out


def reps_for(track: str, arm: str) -> int:
    """3 for the pair `F_BIAS` consumes, 1 everywhere else (PF-3)."""
    return N_REPEATS if (track == REPEAT_TRACK and arm in REPEAT_ARMS) else 1


def _load(track: str):
    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    cfg["llm"]["provider"] = "anthropic"
    cfg["embedding"]["model"] = EMBEDDING_MODEL
    traw = C.load_track(track)
    tm = traw.get("params", {}).get("llm_model")
    tcfg = C.deep_merge(cfg, {"llm": {"model": tm}}) if tm else cfg
    ds = load_track_dataset(traw, tcfg["seed"])
    dev_frac = traw.get("params", {}).get("dev_fraction")
    dev_frac = dev_frac if dev_frac is not None else tcfg.get("sweep", {}).get("dev_fraction", 0.2)
    _dev, test_q = split_dev_test(ds, dev_frac, tcfg["seed"])
    return tcfg, ds, test_q


def build_inventories(log) -> dict:
    """Arms and k=5 contexts for both tracks, at the TRACK DEFAULT model. Zero fresh calls."""
    out = {}
    for track in TRACKS:
        tcfg, ds, test_q = _load(track)
        embedder = Embedder(tcfg, cache_root=tcfg["_cache_root"])
        arm_llm = build_llm(tcfg)
        ctx_full = ChunkContext(embedder=embedder, llm=arm_llm, config=tcfg)
        ctx_det = ChunkContext(embedder=embedder, llm=LLMClient(provider="none"), config=tcfg)
        log(f"  track {track}: arm-construction model {tcfg['llm']['model']} "
            f"(track default; reproduces v1.6)")
        per_arm = {}
        for arm in ARMS:
            units, _rungs, _diag = build_arm(arm, ds, ctx_full, ctx_det)
            per_arm[arm] = retrieve_fixed_k(units, test_q, embedder, tcfg, FIXED_K)
            log(f"    {arm:6} {len(units):5} units -> {len(per_arm[arm])} queries at k={FIXED_K}")
        assert arm_llm.calls == 0, (
            f"SPEND STOP: arm construction made {arm_llm.calls} fresh calls; arms must come "
            f"from cache so they reproduce v1.6")
        out[track] = {"queries": test_q, "contexts": per_arm}
    return out


def generation_spec(inventories: dict) -> list[dict]:
    """Every generation request, with PF-3's targeted repeats. 1,682 by construction."""
    spec = []
    for track in TRACKS:
        inv = inventories[track]
        for arm in ARMS:
            for rec, q in zip(inv["contexts"][arm], inv["queries"]):
                package = CONTEXT_SEPARATOR.join(rec["contexts"])
                prompt = render_prompt(package, q.text)      # v1.7's frozen prompt, by citation
                for rep in range(reps_for(track, arm)):
                    spec.append({"custom_id": custom_id("generate", track, arm, q.query_id, None, rep),
                                 "prompt": prompt, "system": ""})
    return spec


def _client(track_cfg: dict) -> V18Client:
    """A client pinned to §2's model — never the track default (PF-11)."""
    guard = track_cfg.get("cost_guard", {})
    c = V18Client(provider="anthropic", model=V18_CALL_MODEL,
                  max_tokens=track_cfg["llm"].get("max_tokens", 1024),
                  cache_dir=Path(track_cfg["_cache_root"]) / "v18_unused",
                  max_llm_calls=guard.get("max_llm_calls", 100_000),
                  max_usd=guard.get("max_usd", 25.0))
    c.assert_configured_model()
    return c


def cmd_generate(args) -> int:
    log = lambda m: print(m, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    log(f"v1.8 Batch G · generation · call model {V18_CALL_MODEL} (§2/§3 pin)\n")

    inventories = build_inventories(log)
    tcfg, _, _ = _load("A")
    client = _client(tcfg)
    ledger = SpendLedger(ROOT / "v18" / "results_gate0" / "spend_ledger.json")

    spec = generation_spec(inventories)
    requests = build_requests(client, spec)
    log(f"\n  generation requests: {len(requests)} "
        f"(base {sum(len(inventories[t]['queries']) for t in TRACKS) * len(ARMS)} + "
        f"targeted repeats)")

    chk = ledger.affordability_check(len(requests), USD_PER_CALL_BATCH_ESTIMATE)
    log(f"  affordability: {chk['projected_total_calls']:,}/{chk['ceiling']:,} calls, "
        f"~${chk['estimated_usd_for_planned']} for this stage · "
        f"within_ceiling={chk['within_ceiling']}")
    if not chk["within_ceiling"]:
        log("  STOP — projected total passes the frozen ceiling (§6).")
        return 1
    if args.dry_run:
        (OUT / "batch_G_requests_preview.json").write_text(
            json.dumps({"n": len(requests), "sample_custom_ids":
                        [r["custom_id"] for r in requests[:10]],
                        "affordability": chk}, indent=2), encoding="utf-8")
        log("  dry run: nothing submitted.")
        return 0

    runner = BatchRunner(client, ledger, OUT / "batches", poll_seconds=args.poll)
    result = runner.run_stage("gen", requests)
    (OUT / "batch_G.json").write_text(json.dumps(
        {k: v for k, v in result.items() if k != "answers"}, indent=2), encoding="utf-8")
    (OUT / "answers_G.json").write_text(json.dumps(result["answers"], indent=2),
                                        encoding="utf-8")
    log(f"\n  Batch G complete: {result['n_answers']}/{result['n_requests']} answers, "
        f"{result['resubmission_rounds_used']} resubmission round(s)")
    log(f"  pin: {result['pin']['served_models']} constant="
        f"{result['pin']['served_model_constant']}")
    log(f"  ledger: {ledger.totals()['calls']:,} calls recorded")
    return 0


def _cells(inventories, answers):
    """One cell per (track, arm, query), carrying everything a judge prompt needs."""
    from src.v17.reading import gold_text
    cells = []
    for track in TRACKS:
        _tcfg, ds, _tq = _load(track)
        doc_text = {d.doc_id: d.text for d in ds.documents}
        inv = inventories[track]
        for arm in ARMS:
            for rec, q in zip(inv["contexts"][arm], inv["queries"]):
                per_answer = {}
                for a in range(reps_for(track, arm)):
                    cid = custom_id("generate", track, arm, q.query_id, None, a, 0)
                    per_answer[a] = answers[cid]
                cells.append({"track": track, "arm": arm, "query_id": q.query_id,
                              "question": q.text,
                              "reference": gold_text(doc_text[q.gold_spans[0].doc_id],
                                                     q.gold_spans),
                              "contexts": rec["contexts"], "answers": per_answer})
    return cells


def _submit(stage, spec, args, log):
    tcfg, _, _ = _load("A")
    client = _client(tcfg)
    ledger = SpendLedger(ROOT / "v18" / "results_gate0" / "spend_ledger.json")
    requests = build_requests(client, spec)
    log(f"\n  {stage} requests: {len(requests):,}")
    chk = ledger.affordability_check(len(requests), USD_PER_CALL_BATCH_ESTIMATE)
    log(f"  affordability: {chk['projected_total_calls']:,}/{chk['ceiling']:,} calls, "
        f"~${chk['estimated_usd_for_planned']} for this stage · "
        f"within_ceiling={chk['within_ceiling']}")
    if not chk["within_ceiling"]:
        log("  STOP — projected total passes the frozen ceiling (§6).")
        return None
    if args.dry_run:
        log("  dry run: nothing submitted.")
        return None
    runner = BatchRunner(client, ledger, OUT / "batches", poll_seconds=args.poll)
    result = runner.run_stage(stage, requests)
    (OUT / f"batch_{stage}.json").write_text(json.dumps(
        {k: v for k, v in result.items() if k != "answers"}, indent=2), encoding="utf-8")
    (OUT / f"replies_{stage}.json").write_text(json.dumps(result["answers"], indent=2),
                                               encoding="utf-8")
    log(f"\n  {stage} complete: {result['n_answers']:,}/{result['n_requests']:,} replies, "
        f"{result['resubmission_rounds_used']} resubmission round(s)")
    log(f"  pin: {result['pin']['served_models']} constant="
        f"{result['pin']['served_model_constant']}")
    log(f"  ledger: {ledger.totals()['calls']:,} calls recorded")
    return result


def cmd_judge1(args) -> int:
    log = lambda m: print(m, flush=True)
    log(f"v1.8 Batch J1 · judging (all but faithfulness verdicts) · {V18_CALL_MODEL}\n")
    inventories = build_inventories(log)
    answers = migrate_answers(json.loads((OUT / "answers_G.json").read_text(encoding="utf-8")))
    log(f"  generation answers loaded and re-keyed to the PF-15 grammar: {len(answers):,}")
    spec = []
    for cell in _cells(inventories, answers):
        spec += build_j1(cell)
    return 0 if _submit("j1", spec, args, log) is not None or args.dry_run else 1


def cmd_judge2(args) -> int:
    log = lambda m: print(m, flush=True)
    log(f"v1.8 Batch J2 · faithfulness verdicts · {V18_CALL_MODEL}\n")
    inventories = build_inventories(log)
    answers = migrate_answers(json.loads((OUT / "answers_G.json").read_text(encoding="utf-8")))
    j1 = json.loads((OUT / "replies_j1.json").read_text(encoding="utf-8"))
    spec = []
    for cell in _cells(inventories, answers):
        extraction = {}
        for a in range(reps_for(cell["track"], cell["arm"])):
            cid = custom_id("judge1", cell["track"], cell["arm"], cell["query_id"],
                            "faithfulness", a, 0)
            extraction[a] = j1[cid]
        spec += build_j2(cell, extraction)
    return 0 if _submit("j2", spec, args, log) is not None or args.dry_run else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("generate", cmd_generate), ("judge1", cmd_judge1), ("judge2", cmd_judge2)):
        sp = sub.add_parser(name)
        sp.add_argument("--dry-run", action="store_true")
        sp.add_argument("--poll", type=int, default=60)
        sp.set_defaults(fn=fn)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
