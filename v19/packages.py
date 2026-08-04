"""v1.9 §1 — matched package construction with the shortfall CAUSE recorded (Gate 0 ruling §5.2).

v1.7's `build_package` already records *that* a package fell short of its budget. The v1.9
ruling requires it also record *why*, and permits exactly one cause: the document ran out.
Any other shortfall is an apparatus fault, because it would mean the builder stopped padding
while material remained — which no rule in §3.1 authorises.

`build_package` lives in `src/v17/packages.py` and §8 forbids editing outside `v19/`, so the
check wraps it here rather than changing it. That also keeps v1.7's frozen artifact frozen.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.chunkers.base import Unit
from src.datasets.base import GoldSpan
from src.v17.packages import Package, build_package

DOCUMENT_EXHAUSTED = "document_exhausted"


class ShortfallCauseUnknown(AssertionError):
    """A package fell short of B2(q) for a reason other than document exhaustion."""


@dataclass
class MatchedPackage:
    arm: str
    package: Package
    b2: int
    shortfall: int
    cause: str | None

    @property
    def is_exact(self) -> bool:
        return self.shortfall == 0


def build_matched(arm: str, units: list[Unit], gold: list[GoldSpan], b2: int) -> MatchedPackage:
    """Build `arm`'s package at B2(q) and classify any shortfall.

    The only permitted cause is document exhaustion, established positively: every unit of the
    gold document that exists in this arm's inventory is already in the package, so there was
    nothing left to pad with.
    """
    p = build_package(units, gold, b2)
    shortfall = b2 - p.tokens
    if shortfall == 0:
        return MatchedPackage(arm=arm, package=p, b2=b2, shortfall=0, cause=None)

    doc_id = p.meta["doc_id"]
    available = [u.unit_id for u in units if u.doc_id == doc_id]
    if set(p.unit_ids) != set(available):
        raise ShortfallCauseUnknown(
            f"{arm}: package is {shortfall} tokens short of B2(q)={b2} but "
            f"{len(available) - len(p.unit_ids)} unit(s) of {doc_id} were left unused. Document "
            f"exhaustion is the only permitted cause; this is an apparatus fault.")
    return MatchedPackage(arm=arm, package=p, b2=b2, shortfall=shortfall,
                          cause=DOCUMENT_EXHAUSTED)


def build_all(inventories: dict[str, list[Unit]], gold: list[GoldSpan], b2: int) -> dict:
    """Every arm's package at one B2(q), with the per-package shortfall record for the manifest."""
    out = {a: build_matched(a, inv, gold, b2) for a, inv in inventories.items()}
    return {"packages": out,
            "all_exact": all(m.is_exact for m in out.values()),
            "shortfalls": {a: {"tokens": m.shortfall, "cause": m.cause}
                           for a, m in out.items() if m.shortfall},
            "tokens": {a: m.package.tokens for a, m in out.items()}}


def gold_delivery_costs(inventories: dict[str, list[Unit]], gold: list[GoldSpan]) -> dict:
    """`T_a(q)` per arm — tokens each arm needs to cover the gold (ruling §2).

    Promoted to a declared descriptive companion: it is the compactness fact stated in the units
    the experiment measures, it is already computed as B2(q)'s input, and it costs nothing.
    Values and attribution only; no test is computed from it.
    """
    from src.v17.packages import gold_token_cost

    costs = {a: gold_token_cost(inv, gold) for a, inv in inventories.items()}
    peak = max(costs.values())
    return {"T_a": costs, "max": peak, "min": min(costs.values()),
            "argmax": sorted(a for a, t in costs.items() if t == peak),
            "_note": "descriptive companion; no test is computed from these (A5b)"}
