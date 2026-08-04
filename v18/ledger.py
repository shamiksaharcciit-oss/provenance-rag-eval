"""v1.8 — the persistent spend ledger (Gate 0(b) §4, first order).

The problem it exists for, stated plainly: during Gate 0 the probe's call accounting reset every
time the process restarted, and two attempts died on credit exhaustion, so their consumption was
set by the account balance rather than by the plan. Cumulative spend became **uncomputable** —
somewhere in 334–1,018 against a hard 1,000 bound. A budget you cannot compute is not a budget.

So the ledger is a file, not a counter in memory. Every append is written through to disk
immediately, and every read is from disk, so an interruption at any point loses at most the call
in flight. The 17,642-against-25,000 accounting survives crashes, credit deaths, and machine
loss.

Two properties worth naming:

* **Actuals, not estimates.** `record()` takes the usage figures the API returned. The projection
  in `cost.py` is a projection; this is what was spent.
* **Append-only.** Entries are never rewritten. A ledger that can be edited to agree with a
  report is a report, not a ledger.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

#: §6 — the frozen ceiling on end-to-end test-set calls.
CALL_CEILING = 25_000

#: Gate 0(b) §3 — the frozen projection under both targeted-repeat branches.
FROZEN_PROJECTION = 17_642


class CeilingBreached(RuntimeError):
    """Recorded spend passed §6's ceiling. A STOP, not a trim (Gate 0(b) §3)."""


class SpendLedger:
    """An append-only, crash-survivable record of what v1.8 actually spent."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"experiment": "v1.8-instrument-divergence",
                         "ceiling": CALL_CEILING,
                         "frozen_projection": FROZEN_PROJECTION,
                         "entries": [],
                         "_note": ("append-only; actuals from API usage rows, not estimates "
                                   "(Gate 0(b) §4)")})

    # ------------------------------------------------------------------------- storage

    def _write(self, data: dict) -> None:
        """Atomic replace, so a kill mid-write cannot leave a truncated ledger."""
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    # -------------------------------------------------------------------------- writing

    def record(self, stage: str, calls: int, input_tokens: int = 0, output_tokens: int = 0,
               batch_id: str | None = None, note: str = "") -> dict:
        """Append one entry and return the updated totals. Raises if the ceiling is passed."""
        data = self.read()
        data["entries"].append({
            "stage": stage, "calls": calls,
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "batch_id": batch_id, "note": note,
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
        self._write(data)
        totals = self.totals()
        if totals["calls"] > CALL_CEILING:
            raise CeilingBreached(
                f"recorded spend {totals['calls']:,} passed the {CALL_CEILING:,} ceiling (§6). "
                f"STOP — the trim is a ruling, not the agent's discretion.")
        return totals

    def record_indeterminate(self, stage: str, low: int, high: int, cause: str) -> None:
        """Record a spend RANGE, for spend that genuinely cannot be computed.

        Gate 0(b) §3 orders the probe's 334–1,018 recorded "as the honest number: a range,
        attributed". A single invented figure would be worse than the range it replaced.
        """
        data = self.read()
        data["entries"].append({
            "stage": stage, "calls_low": low, "calls_high": high, "indeterminate": True,
            "cause": cause, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
        self._write(data)

    # -------------------------------------------------------------------------- reading

    def totals(self) -> dict:
        data = self.read()
        determinate = [e for e in data["entries"] if not e.get("indeterminate")]
        indeterminate = [e for e in data["entries"] if e.get("indeterminate")]
        calls = sum(e["calls"] for e in determinate)
        return {
            "calls": calls,
            "input_tokens": sum(e.get("input_tokens", 0) for e in determinate),
            "output_tokens": sum(e.get("output_tokens", 0) for e in determinate),
            "indeterminate_low": sum(e["calls_low"] for e in indeterminate),
            "indeterminate_high": sum(e["calls_high"] for e in indeterminate),
            "ceiling": CALL_CEILING,
            "headroom_against_ceiling": CALL_CEILING - calls,
            "frozen_projection": FROZEN_PROJECTION,
        }

    def affordability_check(self, planned_calls: int, usd_per_call_estimate: float) -> dict:
        """Gate 0(b) §5 — run before each submission, not discovered mid-run a third time."""
        t = self.totals()
        projected_total = t["calls"] + planned_calls
        return {
            "already_spent_calls": t["calls"],
            "planned_calls": planned_calls,
            "projected_total_calls": projected_total,
            "ceiling": CALL_CEILING,
            "within_ceiling": projected_total <= CALL_CEILING,
            "estimated_usd_for_planned": round(planned_calls * usd_per_call_estimate, 2),
            "_note": ("call ceiling is the frozen gate; the USD figure is an estimate for the "
                      "balance check and is not the guard (PF-4: the guard is a tripwire)"),
        }
