"""v1.7 E1 — span integrity at matched budget (plan §2.2).

Two binary per-query metrics over the units retrieved at budget:

    integrity_full(q)   = 1 iff every char of every gold span is covered by the UNION of
                          source_ranges over the retrieved set.
    integrity_single(q) = 1 iff SOME SINGLE retrieved unit covers every char of every gold span.

`integrity_full` is the weaker property and is implied by `integrity_single`; the module asserts
that implication on every query it scores, because a construction where single holds and full
does not is a coverage bug, not a finding.

Coverage runs through `src.score.provenance.covered_chars`, the same primitive the published
recall uses, so provenance is read one way in this programme and not two (A5b). That function
unions a unit's ranges before counting, so overlapping ranges never double-count a gold char, and
it returns 0 when the doc_ids differ — which is what makes a cross-document gold span
unsatisfiable for `integrity_single` rather than accidentally satisfiable.

DECLARED READINGS, fixed here before any v17 value exists, because each is a place the plan's
prose admits more than one implementation:

  * Multi-span gold. `integrity_single` requires ONE unit covering ALL spans of the query, not
    one unit per span (plan §2.2, explicit). With gold spans in different documents no unit can
    satisfy it, so such a query scores 0. Measured at Gate 0: ZERO queries in either track have
    multi-document gold, so this reading costs nothing on the corpus as it stands. It is stated
    anyway, because the metric must be defined on inputs the corpus does not happen to contain.
  * Zero-length gold spans are vacuously covered. Measured at Gate 0: none exist in either track.
    Stated for the same reason. `count_degenerate_spans` reports them so the assumption is
    checked against the data rather than trusted.
  * The provenance rung is a PARAMETER, never a default. Callers pass the ranges. This module
    does not know or care whether they are S2, S3 or anything else, so it cannot silently score
    the wrong rung.
"""
from __future__ import annotations

from src.chunkers.base import Unit
from src.datasets.base import GoldSpan
from src.textutil import merge_ranges

Range = tuple[int, int]
#: (doc_id, source_ranges) for one unit, at whichever provenance rung the caller chose.
RangedUnit = tuple[str, list[Range]]


def _covers_all(doc_id: str, ranges: list[Range], gold: list[GoldSpan]) -> bool:
    """Do `ranges` (all within `doc_id`) cover every char of every span in `gold`?"""
    from src.score.provenance import covered_chars

    probe = Unit(unit_id="_probe", text="", doc_id=doc_id, source_ranges=merge_ranges(list(ranges)))
    for g in gold:
        need = g.end_char - g.start_char
        if need <= 0:
            continue  # degenerate span: vacuously covered, see module docstring
        if g.doc_id != doc_id:
            return False
        if covered_chars(probe, g) < need:
            return False
    return True


def integrity_full(units: list[RangedUnit], gold: list[GoldSpan]) -> int:
    """1 iff the union of the retrieved units' ranges covers all gold. Binary."""
    by_doc: dict[str, list[Range]] = {}
    for doc_id, ranges in units:
        by_doc.setdefault(doc_id, []).extend(ranges)
    for g in gold:
        need = g.end_char - g.start_char
        if need <= 0:
            continue
        if not _covers_all(g.doc_id, by_doc.get(g.doc_id, []), [g]):
            return 0
    return 1


def integrity_single(units: list[RangedUnit], gold: list[GoldSpan]) -> int:
    """1 iff SOME ONE unit covers all gold. Binary."""
    for doc_id, ranges in units:
        if _covers_all(doc_id, ranges, gold):
            return 1
    return 0


def score_query(units: list[RangedUnit], gold: list[GoldSpan]) -> dict:
    """Both metrics for one query, with the implication asserted.

    `integrity_single` implies `integrity_full`: a unit covering all gold is part of the union
    that `integrity_full` takes. If that ever fails the two are reading provenance differently
    and no number computed from either means anything.
    """
    single = integrity_single(units, gold)
    full = integrity_full(units, gold)
    assert not (single and not full), (
        "integrity_single=1 with integrity_full=0 — a single unit covers all gold but the union "
        "of all units, which contains it, does not. Coverage is being read two ways.")
    return {"integrity_single": single, "integrity_full": full}


def feasible_single(inventory: list[RangedUnit], gold: list[GoldSpan]) -> int:
    """1 iff ANY unit in the WHOLE arm inventory could satisfy `integrity_single`.

    The feasibility ceiling of plan §2.5. Reported descriptively and NEVER used to adjust a
    score: a query that no unit in the inventory can satisfy still scores 0, per §2.2.
    """
    return integrity_single(inventory, gold)


def count_degenerate_spans(gold: list[GoldSpan]) -> int:
    """Zero- or negative-length gold spans, which `_covers_all` treats as vacuously covered."""
    return sum(1 for g in gold if g.end_char - g.start_char <= 0)
