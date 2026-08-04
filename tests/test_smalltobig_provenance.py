"""Small-to-big provenance — v1.4 rules, RETAINED FOR THE v1.5 SECONDARY ARM ONLY.

SCOPE UNDER v1.5: the primary path scores the DELIVERED PARENT, which is a baseline `Unit`
carrying `source_ranges` legitimately, because the parent inventory is pinned set-identical to
the baseline inventory and there is therefore no wider parent to reach for. These tests govern
the C4 marked-section SECONDARY arm, where parents are NOT baseline units and dilution is still
live. See `tests/test_smalltobig_parent_ranking.py` for the v1.5 primary-path guards.

Original v1.4 rationale, still valid within that scope:

The prereg mandates: hits are scored on the CHILD's source_ranges, never the parent's, and a
test must assert that widening the parent leaves every recall number unchanged.

A widening-parent invariance test is unusually easy to write in a form that can only ever
pass. If the parent is simply never plumbed into the scoring call, widening it is a no-op *by
construction* rather than *by design*, and the test confirms nothing — while a later refactor
that starts passing parent ranges through sails straight past it. That is the same species of
non-evidence as a cross-check run against a corpus that produces no edits.

So this module contains a NEGATIVE CONTROL: `_score_on_parent_ranges` deliberately scores the
parent, and `test_invariance_test_actually_bites` asserts that the invariance check FAILS
against it. If that test ever passes trivially, the guard has stopped guarding.
"""
from __future__ import annotations

import pytest

from src.chunkers.base import Unit
from src.datasets.base import GoldSpan, Query
from src.score.provenance import hit_flags
from src.smalltobig.chunker import build_children
from src.smalltobig.units import ParentContext, parents_for

DOC = "d0"


def _parent_units() -> list[Unit]:
    """Two 'parent' units of raw text, each a contiguous span of the original document."""
    a = "alpha beta gamma delta epsilon zeta eta theta " * 4          # ~180 chars
    b = "iota kappa lambda mu nu xi omicron pi rho sigma tau " * 4
    return [
        Unit(unit_id="C0:d0:0", text=a.strip(), doc_id=DOC, source_ranges=[(0, len(a.strip()))]),
        Unit(unit_id="C0:d0:1", text=b.strip(), doc_id=DOC,
             source_ranges=[(1000, 1000 + len(b.strip()))]),
    ]


def _query(start: int, end: int) -> Query:
    return Query(query_id="q1", text="alpha", gold_spans=[GoldSpan(DOC, start, end)],
                 answer="a", qtype="factual")


def _score_on_parent_ranges(children: list[Unit], parent_index, q: Query) -> list[int]:
    """DELIBERATELY BROKEN. The defect the type split exists to prevent.

    Replaces each retrieved child's provenance with its parent's span, then scores. This is
    what the metric would silently become if someone 'helpfully' returned parent provenance
    so the generator's context matched the scored unit.
    """
    faked = []
    for c in children:
        p = parent_index[c.meta["parent_id"]]
        faked.append(Unit(unit_id=c.unit_id, text=c.text, doc_id=c.doc_id,
                          source_ranges=[list(p.char_span)], meta=c.meta))
    return hit_flags(faked, q, variant="any", min_overlap=1, containment=0.5)


# --------------------------------------------------------------------------
# 1. The guarantee: parents cannot physically reach the scoring path
# --------------------------------------------------------------------------

def test_parent_has_no_source_ranges_attribute():
    """Type-level enforcement, not convention: ParentContext simply has no source_ranges."""
    p = ParentContext(parent_id="p", text="t", doc_id=DOC, char_span=(0, 10))
    assert not hasattr(p, "source_ranges")


def test_parentcontext_cannot_be_scored_secondary_arm_guard():
    """Secondary arm only: a ParentContext is unscoreable by construction.

    Under v1.5's PRIMARY path parents are baseline Units and ARE scored — legitimately, since
    the inventory is pinned. This guard applies where parents are not baseline units.
    """
    p = ParentContext(parent_id="p", text="t", doc_id=DOC, char_span=(0, 500))
    with pytest.raises(AttributeError):
        hit_flags([p], _query(0, 5), variant="any", min_overlap=1, containment=0.5)  # type: ignore[list-item]


# --------------------------------------------------------------------------
# 2. Children carry their OWN provenance, strictly inside the parent
# --------------------------------------------------------------------------

def test_children_have_their_own_narrow_ranges():
    children, parents = build_children(_parent_units(), child_tokens=8, condition_id="C0")
    assert len(children) > len(_parent_units())
    for c in children:
        (cs, ce) = c.source_ranges[0]
        p = parents[c.meta["parent_id"]]
        assert p.char_span[0] <= cs < ce <= p.char_span[1], "child escaped its parent's span"
        assert (ce - cs) < (p.char_span[1] - p.char_span[0]), "child not narrower than parent"


# --------------------------------------------------------------------------
# 3. THE NEGATIVE CONTROL — the invariance test must be able to fail
# --------------------------------------------------------------------------

def test_invariance_test_actually_bites():
    """Scoring the parent inflates recall; scoring the child does not.

    Gold sits in the FIRST child of parent 0. Every other child of that parent misses it — but
    all of them share the parent's span, so parent-scoring marks them all as hits.
    """
    children, parents = build_children(_parent_units(), child_tokens=8, condition_id="C0")
    p0 = parents["C0:d0:0"]
    gold = _query(p0.char_span[0] + 1, p0.char_span[0] + 5)

    correct = hit_flags(children, gold, variant="any", min_overlap=1, containment=0.5)
    broken = _score_on_parent_ranges(children, parents, gold)

    assert sum(correct) == 1, "exactly one child genuinely overlaps the gold span"
    assert sum(broken) > sum(correct), (
        "parent-scoring must inflate the hit count — if it does not, this negative control "
        "is not exercising the defect and the invariance test below proves nothing")


def test_widening_the_parent_leaves_recall_unchanged():
    """The invariance the prereg mandates. Meaningful only because the control above bites."""
    children, parents = build_children(_parent_units(), child_tokens=8, condition_id="C0")
    p0 = parents["C0:d0:0"]
    gold = _query(p0.char_span[0] + 1, p0.char_span[0] + 5)
    before = hit_flags(children, gold, variant="any", min_overlap=1, containment=0.5)

    # Widen every parent enormously. Children are untouched.
    for p in parents.values():
        p.char_span = (max(0, p.char_span[0] - 5000), p.char_span[1] + 5000)
        p.text = p.text + " padding" * 200

    after = hit_flags(children, gold, variant="any", min_overlap=1, containment=0.5)
    assert before == after, "recall changed when only the parent changed — provenance leaked"


# --------------------------------------------------------------------------
# 4. Duplicate parents collapse AFTER top-k (v1.4 §4)
# --------------------------------------------------------------------------

def test_duplicate_parents_collapse_after_topk_preserving_order():
    children, parents = build_children(_parent_units(), child_tokens=8, condition_id="C0")
    topk = children[:5]                                  # top-k chosen on child scores alone
    got = parents_for(topk, parents)
    assert len(got) <= len(topk)
    assert len({p.parent_id for p in got}) == len(got), "parents must be distinct"
    assert got[0].parent_id == topk[0].meta["parent_id"], "first-appearance order preserved"


def test_collapsing_does_not_touch_the_child_ranking():
    """Parents are looked up AFTER the cut, so top-k membership cannot depend on them."""
    children, parents = build_children(_parent_units(), child_tokens=8, condition_id="C0")
    topk = children[:5]
    ids_before = [c.unit_id for c in topk]
    parents_for(topk, parents)
    assert [c.unit_id for c in topk] == ids_before
