"""Child / parent types for small-to-big retrieval.

STATUS UNDER v1.5 — READ THIS BEFORE USING `ParentContext`
==========================================================
This module was written for **v1.4**, which scored the CHILD and never the parent. **v1.5
inverts that**: the delivered PARENT is scored, and the parent is a baseline `Unit` carrying
`source_ranges` legitimately (v1.5 §4).

Why the inversion was safe: v1.4 forbade parent-scoring because a wider parent trivially
overlaps more gold. **Dilution requires that widening be available.** Under v1.5 the parent
inventory is set-identical to the baseline unit inventory, so there is no wider parent to
reach for — the inventory is pinned by the baseline's own chunker, and the guard asserting
that set-identity replaces the invariance test.

Consequently:

  * **Primary path (C0/C2/C4):** parents ARE baseline `Unit`s. `ParentContext` is NOT used and
    the type separation retires — it would forbid the frozen design.
  * **Secondary arm (C4 marked-section parents):** those parents are *not* baseline units, so
    dilution is live again and `ParentContext` still applies there.

The type separation therefore survives only where dilution survives. Keeping it on the primary
path would leave a type system forbidding the design the prereg freezes.

The v1.4 parent-dilution measurement stands as the quantified motivation for pinning the
inventory rather than merely testing it: recall@5 inflated by **+0.267 (C0) / +0.301 (C2)** on
Track A when parent ranges were scored against an unpinned inventory
(`scripts/demo_parent_dilution.py`).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.chunkers.base import Unit


@dataclass
class ParentContext:
    """The larger unit returned for generation. NOT scoreable, by construction.

    Deliberately does NOT define `source_ranges`. `hit_flags`/`covered_chars` access that
    attribute, so passing a ParentContext into the scoring path raises AttributeError rather
    than silently inflating recall.

    `char_span` records where the parent sits in the original document for reporting and
    debugging only — it is named differently on purpose, so no scoring code can pick it up by
    duck-typing a `source_ranges` lookup.
    """

    parent_id: str
    text: str
    doc_id: str
    char_span: tuple[int, int]
    n_tokens: int = 0
    meta: dict = field(default_factory=dict)

    def contains_span(self, start: int, end: int) -> bool:
        """Descriptive only (H7c context-sufficiency). Never used for hit scoring."""
        return self.char_span[0] <= start and end <= self.char_span[1]


@dataclass
class ChildParentPair:
    """One indexed child plus the parent it would hand to the generator.

    `child` is a plain `Unit`: it is what gets embedded, retrieved and scored. `parent` rides
    alongside as context and never enters scoring.
    """

    child: Unit
    parent: ParentContext

    @property
    def unit(self) -> Unit:
        return self.child


def parents_for(children: list[Unit], index: dict[str, ParentContext]) -> list[ParentContext]:
    """Distinct parents for a ranked child list, collapsed AFTER top-k (v1.4 §4).

    The caller slices to top-k FIRST, then calls this. Collapsing before top-k would change
    which children survive the cut and therefore the primary metric; collapsing after leaves
    ranking untouched and yields the unique-context set a generator would actually receive.
    Order of first appearance is preserved.
    """
    seen: set[str] = set()
    out: list[ParentContext] = []
    for c in children:
        pid = c.meta.get("parent_id")
        if pid is None or pid in seen:
            continue
        parent = index.get(pid)
        if parent is not None:
            seen.add(pid)
            out.append(parent)
    return out
