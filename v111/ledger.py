"""v1.11 ledger — v1.8's `SpendLedger` storage, under v1.11's ceiling.

`v18.ledger.SpendLedger` writes a v1.8 header and enforces `CALL_CEILING = 25_000`, which is
v1.8's number. v1.11's ceiling is **4,000** and §8 makes a breach a STOP, so using v1.8's ledger
unmodified would leave v1.11's ceiling unenforced — a guard that cannot fire is decorative.
`v18/` is read-only, so the ceiling is enforced here instead: the crash-survivable atomic write
and the append-only entry shape are inherited by identity, and only the two v1.11-specific
constants are ours.
"""
from __future__ import annotations

from pathlib import Path

from v18.ledger import CeilingBreached, SpendLedger

V111_CEILING = 4_000
V111_FROZEN_PROJECTION = 2_112      # the plan's call table; the build produces 2,106 (PF-G2)


class V111Ledger(SpendLedger):
    """`SpendLedger` with v1.11's ceiling. Same interface, so `BatchRunner` cannot tell."""

    def __init__(self, path: Path):
        super().__init__(path)
        data = self.read()
        if data.get("experiment") != "v1.11-reading-robustness":
            data.update({"experiment": "v1.11-reading-robustness",
                         "ceiling": V111_CEILING,
                         "frozen_projection": V111_FROZEN_PROJECTION,
                         "_note": ("append-only; actuals from API usage rows, not estimates. "
                                   "Ceiling is v1.11's 4,000, not v1.8's 25,000.")})
            self._write(data)

    def record(self, stage: str, calls: int, input_tokens: int = 0, output_tokens: int = 0,
               batch_id: str | None = None, note: str = "") -> dict:
        """Append, then enforce **v1.11's** ceiling.

        The parent's own check against 25,000 runs first and cannot fire before this one, since
        4,000 < 25,000; this method's raise is therefore the binding one.
        """
        totals = super().record(stage, calls, input_tokens, output_tokens, batch_id, note)
        if totals["calls"] > V111_CEILING:
            raise CeilingBreached(
                f"recorded spend {totals['calls']:,} passed v1.11's {V111_CEILING:,} ceiling "
                f"(§6/§8). STOP — the trim is a ruling, not the agent's discretion.")
        return totals
