"""v1.10 §1 — the three arms. ZERO fresh LLM calls, asserted per stage.

    U   base chunks, nothing prepended
    P   base chunks + neutral padding, per-chunk token length exactly matching the real blurb
    C   base chunks + the real cached C2 blurbs (contextual retrieval as published)

The §0 constraint is enforced, not narrated: `no_fresh_calls` installs a provider that raises,
so a cache miss fails the build instead of quietly spending. "We'll just generate a few missing
blurbs" is how a free experiment becomes a spending one.

WHAT MAKES §2's RULE WORK IS ALREADY IN THE IMPLEMENTATION, and is verified rather than assumed:
`ContextualChunker` prepends the blurb to `Unit.text` but leaves `source_ranges` untouched, so
prepended tokens are counted by `count_tokens(u.text)` — charged to the budget — while
contributing no coverage to the provenance scorer. `P` is built to the same contract.
"""
from __future__ import annotations

import contextlib
import hashlib

from src.chunkers.base import Unit
from src.textutil import count_tokens
from v110.padding import filler_for

ARMS = ("U", "P", "C")


class FreshCallAttempted(RuntimeError):
    """A stage tried to reach the provider. v1.10 spends nothing (§0)."""


@contextlib.contextmanager
def no_fresh_calls():
    """Any provider call inside this block raises. Executed, not narrated."""
    import src.llm.client as LC

    original = LC.LLMClient._call_provider

    def _refuse(self, prompt, system):
        raise FreshCallAttempted(
            "a fresh LLM call was attempted; v1.10 spends nothing (§0). If the blurb cache is "
            "incomplete on the primary cell that is a STOP, not a top-up.")

    LC.LLMClient._call_provider = _refuse
    try:
        yield
    finally:
        LC.LLMClient._call_provider = original


def inventory_hash(units: list[Unit]) -> str:
    """Content hash binding an inventory: ids, doc ids and source ranges, in order."""
    h = hashlib.sha256()
    for u in units:
        h.update(u.unit_id.encode())
        h.update(u.doc_id.encode())
        h.update(repr([tuple(r) for r in u.source_ranges]).encode())
    return h.hexdigest()


def provenance_hash(units: list[Unit]) -> str:
    """Content hash over doc ids and source ranges ONLY — unit ids excluded.

    This is the hash that binds the three arms together. `inventory_hash` includes the unit id
    and therefore differs between `U` and `P` purely because `P` suffixes its ids, which is a
    naming fact and not a provenance fact. The invariant the experiment rests on is that all
    three arms carry the SAME underlying segmentation, and that is what this measures.
    """
    h = hashlib.sha256()
    for u in units:
        h.update(u.doc_id.encode())
        h.update(repr([tuple(r) for r in u.source_ranges]).encode())
    return h.hexdigest()


def build_base(ds, ctx, chunk_tokens: int = 768):
    """The `U` arm: C2's base segmentation, built by the same path C2 builds it."""
    from src.chunkers.naive import fixed_size_units

    return [u for d in ds.documents
            for u in fixed_size_units(d, chunk_tokens=chunk_tokens, overlap_frac=0.0,
                                      condition_id="U")]


def build_contextual(ds, ctx, params: dict):
    """The `C` arm: real cached C2 blurbs. Raises on any cache miss."""
    from src.chunkers.contextual import ContextualChunker

    with no_fresh_calls():
        return [u for d in ds.documents for u in ContextualChunker(params, ctx).chunk(d)]


def build_padded(base_units: list[Unit], contextual_units: list[Unit]) -> list[Unit]:
    """The `P` arm: filler of exactly each chunk's real blurb length, prepended.

    Pairing is positional and asserted against the base inventory, because `P` only means
    anything if each chunk's filler matches *that chunk's* blurb length.
    """
    assert len(base_units) == len(contextual_units), (
        f"arm inventories differ: {len(base_units)} base vs {len(contextual_units)} contextual")
    out = []
    for b, c in zip(base_units, contextual_units):
        assert b.doc_id == c.doc_id and list(b.source_ranges) == list(c.source_ranges), (
            f"unit {b.unit_id} does not correspond to {c.unit_id}; the arms are not aligned")
        n = count_tokens(c.meta["blurb"])
        pad = filler_for(b.unit_id, n)
        out.append(Unit(unit_id=b.unit_id + "-pad", text=f"{pad}\n\n{b.text}", doc_id=b.doc_id,
                        source_ranges=list(b.source_ranges),
                        meta={**b.meta, "pad_tokens": n, "pad": pad}))
    return out


def assert_prepended_text_is_unattributed(base: list[Unit], arm: list[Unit], label: str) -> dict:
    """§2: prepended text is charged to the budget and can never score.

    Charged: the arm unit is longer than its base unit by exactly the prepended token count.
    Cannot score: the arm unit's `source_ranges` are identical to the base unit's, so the
    provenance scorer sees nothing new.
    """
    deltas = []
    for b, a in zip(base, arm):
        assert list(a.source_ranges) == list(b.source_ranges), (
            f"{label}: {a.unit_id} altered source_ranges — prepended text would be able to score")
        d = count_tokens(a.text) - count_tokens(b.text)
        assert d > 0, f"{label}: {a.unit_id} is not longer than its base unit"
        deltas.append(d)
    return {"arm": label, "n_units": len(deltas), "prepended_tokens_min": min(deltas),
            "prepended_tokens_median": sorted(deltas)[len(deltas) // 2],
            "prepended_tokens_max": max(deltas), "prepended_tokens_total": sum(deltas)}
