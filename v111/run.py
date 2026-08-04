"""v1.11 — the run. Written after the freeze (`be74c69`), per §6.

All generation through v1.8's batch client, imported read-only with identity asserted. Two
clients, both plan-pinned and asserted at construction: Sonnet for E-A/E-C/E-E, and the Haiku id
enumerated and frozen at Gate 0 for E-B. `response.model` is asserted per stage.

Every package text and every output text is persisted; `v111/persist.py`'s acceptor governs and
is executed before the run is allowed to report.
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

import v18.batch as v18batch  # noqa: E402
from v18.batch import BatchRunner, build_requests, request_set_digest  # noqa: E402
from v18.client import V18Client  # noqa: E402
from v111.ledger import V111Ledger  # noqa: E402  (v1.8 storage, v1.11 ceiling)

FREEZE = "be74c69ef65a6a8174ee04c05715ca0888ab2c08"
OUT = ROOT / "v111" / "results_run"
SONNET = "claude-sonnet-5"
HAIKU = "claude-haiku-4-5-20251001"          # enumerated from the live model list at Gate 0
STAGE_MODEL = {"ea": SONNET, "eb": HAIKU, "ec-v1": SONNET, "ec-v2": SONNET, "ee": SONNET}


def assert_read_only_identity() -> None:
    """§6: the batch client is v1.8's objects, not a copy."""
    import importlib
    assert importlib.import_module("v18.batch") is v18batch
    from v111.ids import CUSTOM_ID_MAX, CUSTOM_ID_PATTERN
    assert CUSTOM_ID_PATTERN is v18batch.CUSTOM_ID_PATTERN
    assert CUSTOM_ID_MAX is v18batch.CUSTOM_ID_MAX


def client_for(model: str, tcfg) -> V18Client:
    g = tcfg.get("cost_guard", {})
    c = V18Client(provider="anthropic", model=model,
                  max_tokens=tcfg.get("llm", {}).get("max_tokens", 1024),
                  cache_dir=Path(tcfg["_cache_root"]) / "llm",
                  max_llm_calls=g.get("max_llm_calls", 100000),
                  max_usd=g.get("max_usd", 60.0))
    c.assert_configured_model(model)      # explicit expected: v18's default is Sonnet, not Haiku
    assert c.model == model
    return c


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all")
    ap.add_argument("--poll-seconds", type=int, default=60)
    args = ap.parse_args(argv)
    assert_read_only_identity()
    OUT.mkdir(parents=True, exist_ok=True)
    log = lambda m: print(m, flush=True)

    from v111.requests_build import build_all_specs, load_track_a
    ds, tcfg, invs, test = load_track_a()
    tcfg.setdefault("_cache_root", str(ROOT / "cache"))
    specs, packages, gaps = build_all_specs(invs, test)
    log(f"v1.11 · freeze {FREEZE[:7]} · {len(specs)} requests · {len(gaps)} construction gaps")

    # persist packages BEFORE submitting: PF-G1 makes them part of the record, not a by-product
    (OUT / "packages.json").write_text(json.dumps(packages, indent=2), encoding="utf-8")
    (OUT / "specs.json").write_text(json.dumps(
        [{k: v for k, v in s.items() if k != "prompt"} for s in specs], indent=2), encoding="utf-8")
    (OUT / "construction_gaps.json").write_text(json.dumps(gaps, indent=2), encoding="utf-8")

    by_stage: dict[str, list[dict]] = {}
    for s in specs:
        by_stage.setdefault(s["stage"], []).append(s)
    stages = sorted(by_stage) if args.stage == "all" else [args.stage]

    manifest = {"experiment": "v1.11", "freeze_commit": FREEZE,
                "batch_client": "v18.batch, imported read-only (identity asserted)",
                "models": STAGE_MODEL, "stages": {}, "construction_gaps": gaps}
    answers: dict[str, str] = {}

    for stage in stages:
        model = STAGE_MODEL[stage]
        cl = client_for(model, tcfg)
        ledger = V111Ledger(OUT / "spend_ledger.json")
        runner = BatchRunner(cl, ledger=ledger, out_dir=OUT, api=None,
                             poll_seconds=args.poll_seconds)
        reqs = build_requests(cl, by_stage[stage])
        log(f"  {stage}: {len(reqs)} requests on {model} "
            f"(digest {request_set_digest(reqs)[:12]})")
        t0 = time.time()
        res = runner.run_stage(stage, reqs)
        answers.update(res["answers"])
        pin = cl.pin_record()
        seen = pin.get("response_model_distinct") or sorted(set(cl.models_seen))
        assert not seen or seen == [model], (
            f"APPARATUS-STOP: stage {stage} response.model {seen} != [{model!r}]")
        manifest["stages"][stage] = {
            "model": model, "n_requests": res["n_requests"], "n_answers": res["n_answers"],
            "resubmission_rounds_used": res["resubmission_rounds_used"],
            "batches": [{k: v for k, v in b.items() if k != "failed_rows"}
                        for b in res["batches"]],
            "failed_rows": [f for b in res["batches"] for f in b.get("failed_rows", [])],
            "pin": pin, "response_model_distinct": seen,
            "cost": cl.cost_summary(), "seconds": round(time.time() - t0, 1)}
        (OUT / f"answers_{stage}.json").write_text(json.dumps(res["answers"], indent=2),
                                                   encoding="utf-8")
        (OUT / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        log(f"    {res['n_answers']}/{res['n_requests']} answered, "
            f"rounds={res['resubmission_rounds_used']}, {cl.cost_summary()['est_usd']}")

    manifest["ledger"] = V111Ledger(OUT / "spend_ledger.json").read()
    (OUT / "answers_all.json").write_text(json.dumps(answers, indent=2), encoding="utf-8")
    manifest["total_answers"] = len(answers)
    manifest["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    log(f"  total {len(answers)} answers; wrote {OUT/'run_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
