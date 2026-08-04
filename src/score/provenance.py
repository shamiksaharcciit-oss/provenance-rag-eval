"""Provenance-based scoring — THE crux (plan §6). Implement exactly.

A retrieved unit U is a HIT for query q iff any of `U.source_ranges` overlaps any
of `q.gold_spans` for the SAME doc_id, with overlap >= MIN_OVERLAP characters
(default: any overlap > 0). A stricter variant requires >= 50% containment of the
gold span. Both variants are reported (§6.2).
"""
from __future__ import annotations

from src.chunkers.base import Unit
from src.datasets.base import GoldSpan, Query

ANY = "any"
STRICT = "strict"


def _interval_overlap(a: tuple[int, int], b: tuple[int, int]) -> int:
    """Characters shared by half-open intervals [a0,a1) and [b0,b1)."""
    lo = max(a[0], b[0])
    hi = min(a[1], b[1])
    return max(0, hi - lo)


def covered_chars(unit: Unit, gold: GoldSpan) -> int:
    """Number of characters of `gold` covered by the UNION of unit.source_ranges.

    Union (not sum) so overlapping/adjacent source ranges never double-count a
    gold character. Only ranges in the same document are considered.
    """
    if unit.doc_id != gold.doc_id:
        return 0
    g = (gold.start_char, gold.end_char)
    # Collect per-range overlaps with the gold interval, then union them.
    pieces: list[tuple[int, int]] = []
    for r in unit.source_ranges:
        lo = max(r[0], g[0])
        hi = min(r[1], g[1])
        if hi > lo:
            pieces.append((lo, hi))
    if not pieces:
        return 0
    pieces.sort()
    total = 0
    cur_lo, cur_hi = pieces[0]
    for lo, hi in pieces[1:]:
        if lo <= cur_hi:  # overlapping/adjacent -> extend
            cur_hi = max(cur_hi, hi)
        else:
            total += cur_hi - cur_lo
            cur_lo, cur_hi = lo, hi
    total += cur_hi - cur_lo
    return total


def is_hit(
    unit: Unit,
    query: Query,
    variant: str = ANY,
    min_overlap: int = 1,
    containment: float = 0.5,
) -> bool:
    """Does this unit satisfy the hit criterion for the query under `variant`?"""
    for gold in query.gold_spans:
        cov = covered_chars(unit, gold)
        if cov <= 0:
            continue
        if variant == ANY:
            if cov >= max(1, min_overlap):
                return True
        elif variant == STRICT:
            gold_len = gold.end_char - gold.start_char
            if gold_len <= 0:
                continue
            if cov / gold_len >= containment:
                return True
        else:
            raise ValueError(f"unknown overlap variant {variant!r}")
    return False


def hit_flags(
    ranked_units: list[Unit],
    query: Query,
    variant: str = ANY,
    min_overlap: int = 1,
    containment: float = 0.5,
) -> list[int]:
    """Binary hit flag per retrieved unit, in rank order."""
    return [
        1 if is_hit(u, query, variant, min_overlap, containment) else 0
        for u in ranked_units
    ]
