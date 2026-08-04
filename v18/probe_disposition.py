"""v1.8 — the probe's disposition, written by procedure rather than asserted in prose.

Gate 0(b) §3 abandoned the determinism probe by rule and selected the conservative branch
without it. The freeze commit has to carry that decision as a record: the INVALID artifacts'
hashes, the spend range with its cause, and the branch declaration. This module produces it.

Run: `python -m v18.probe_disposition`

Why the spend is a *range*. Four probe attempts ran. The first measured its own cache and was
caught by PF-2's assertion; two died on API credit exhaustion, so what they consumed was set by
the account balance rather than by the plan; the fourth resolved its model from a harness
default and measured `claude-opus-4-8`. Cumulative spend is therefore bounded, not known:
334–1,018 against PF-1's 1,000-call bound. A single invented figure would be worse than the
range it replaced — that is the 589 MB lesson applied to spend, and Gate 0(b) §3 ordered it
recorded "as the honest number: a range, attributed."
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from v18.ledger import FROZEN_PROJECTION, SpendLedger

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "v18" / "results_gate0"

#: The probe artifacts, retained under their INVALID names because `requested_model` inside them
#: is the honest record of what happened. Renamed, never edited.
INVALID_ARTIFACTS = (
    "INVALID_wrong_model__probe_results.json",
    "INVALID_wrong_model__probe_judge.json",
    "INVALID_wrong_model__probe_run_log.txt",
)

SPEND_LOW, SPEND_HIGH = 334, 1_018


def build() -> dict:
    hashes = {}
    for name in INVALID_ARTIFACTS:
        path = OUT / name
        hashes[name] = (hashlib.sha256(path.read_bytes()).hexdigest()
                        if path.exists() else "<absent>")

    ledger = SpendLedger(OUT / "spend_ledger.json")
    if not any(e.get("indeterminate") for e in ledger.read()["entries"]):
        ledger.record_indeterminate(
            "gate0-probe", low=SPEND_LOW, high=SPEND_HIGH,
            cause=("four attempts; two died on API credit exhaustion, so their consumption was "
                   "set by the account balance rather than by the plan. PF-1's 1,000-call bound "
                   "is treated as consumed (Gate 0(b) §3)."))

    return {
        "experiment": "v1.8-instrument-divergence",
        "record": "PROBE_DISPOSITION",
        "outcome": "ABANDONED BY RULE — not re-run, not repaired",
        "ruling": "Decisions_v18_Gate0b_2026-08-01.md §3",
        "attempts": [
            {"n": 1, "outcome": "PF-2 assertion fired: 120 cache hits on 180 calls",
             "cause": "bypass isolated the cache directory but left caching on; repeat 1 wrote "
                      "and repeats 2-3 read it back — G2 reproduced inside the fix for G2"},
            {"n": 2, "outcome": "died on credit exhaustion during generation"},
            {"n": 3, "outcome": "generation completed, judge stage died on credit exhaustion",
             "note": "runner persisted only at the end, discarding 194 calls of finished work; "
                     "per-stage persistence added afterwards"},
            {"n": 4, "outcome": "both stages completed, then found INVALID",
             "cause": "config fell through to the harness default; measured claude-opus-4-8, "
                      "not the pinned claude-sonnet-5 (G11)"},
        ],
        "verdicts_withdrawn": {
            "generation_35_of_60_divergent": "withdrawn with the artifacts — wrong model",
            "judge_0_of_24_divergent": "withdrawn with the artifacts — wrong model",
        },
        "invalid_artifact_sha256": hashes,
        "spend": {"low": SPEND_LOW, "high": SPEND_HIGH, "indeterminate": True,
                  "bound": 1000, "bound_status": "treated as consumed"},
        "branch_selected_by_rule": {
            "determinism": "UNMEASURED, recorded as such",
            "generation_repeats": "3x, Track A F768/U768 only",
            "judge_repeats": "3x answer-level metrics, Track A F768/U768 only",
            "projection_calls": FROZEN_PROJECTION,
            "ceiling": 25_000,
            "why_safe": ("median-of-3 over a deterministic model returns the deterministic "
                         "value, so the conservative branch is valid under either truth"),
            "mandatory_caveat": ("single sample, sampling nondeterminism unquantified, "
                                 "temperature pin unavailable"),
        },
        "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rec = build()
    (OUT / "probe_disposition.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    print(f"probe disposition: {rec['outcome']}")
    for name, digest in rec["invalid_artifact_sha256"].items():
        print(f"  {name}  {digest[:16]}")
    print(f"  spend {rec['spend']['low']}-{rec['spend']['high']} of {rec['spend']['bound']} "
          f"({rec['spend']['bound_status']})")
    print(f"  branch by rule -> {rec['branch_selected_by_rule']['projection_calls']:,} calls "
          f"vs {rec['branch_selected_by_rule']['ceiling']:,} ceiling")
    print(f"wrote {OUT / 'probe_disposition.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
