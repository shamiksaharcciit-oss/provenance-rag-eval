"""v1.8 PF-16 §1.4 — the hedging table: judge instruction-violations, counted.

The frozen judge prompt says "one line of JSON and nothing else". 101 of 15,960 replies wrote
reasoning first and the JSON after. G15 §1.4 rules that this is **data, not just an apparatus
fault**: a judge that disobeys an explicit format instruction 0.63% of the time, concentrated in
particular metrics, is a finding about judge-based evaluation and goes in the results document
as one.

Descriptive only. Counts by metric and by arm, no test and no mechanism — the A-heavy split is
reported and **not explained** (A1g). Nothing here reads a verdict value; classification is
purely syntactic, on the shape of the reply.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

from v18.batch import parse_custom_id

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "v18" / "results_run"


def classify(reply: str) -> str:
    """`conforming` | `fenced` | `prose_then_json`. Syntactic; no verdict is read."""
    s = reply.strip()
    if s.startswith("```"):
        return "fenced"
    if s.startswith("{") and s.endswith("}"):
        return "conforming"
    return "prose_then_json"


def build() -> dict:
    replies = {}
    for name in ("replies_j1.json", "replies_j2.json"):
        replies.update(json.loads((OUT / name).read_text(encoding="utf-8")))

    by_metric: collections.Counter = collections.Counter()
    by_arm: collections.Counter = collections.Counter()
    by_track: collections.Counter = collections.Counter()
    totals: collections.Counter = collections.Counter()
    hedged_ids: list[str] = []

    for cid, reply in replies.items():
        kind = classify(reply)
        totals[kind] += 1
        if kind != "prose_then_json":
            continue
        p = parse_custom_id(cid)
        by_metric[p["metric"]] += 1
        by_arm[f'{p["track"]}/{p["arm"]}'] += 1
        by_track[p["track"]] += 1
        hedged_ids.append(cid)

    n = sum(totals.values())
    hedged = totals["prose_then_json"]
    return {
        "n_replies": n,
        "n_hedged": hedged,
        "rate": round(hedged / n, 6) if n else 0.0,
        "by_metric": dict(sorted(by_metric.items(), key=lambda kv: -kv[1])),
        "by_track": dict(sorted(by_track.items())),
        "by_track_arm": dict(sorted(by_arm.items())),
        "hedged_custom_ids": sorted(hedged_ids),
        "_note": ("descriptive; no test, no mechanism. The track split is reported and not "
                  "explained (A1g). Classification is syntactic — no verdict value is read."),
    }


def main() -> int:
    rec = build()
    (OUT / "hedging_table.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    print(f"judge instruction-violations: {rec['n_hedged']}/{rec['n_replies']:,} "
          f"({rec['rate'] * 100:.2f}%)")
    print(f"  by metric: {rec['by_metric']}")
    print(f"  by track:  {rec['by_track']}")
    print(f"  by arm:    {rec['by_track_arm']}")
    print(f"wrote {OUT / 'hedging_table.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
