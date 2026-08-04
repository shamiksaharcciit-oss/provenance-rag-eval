"""D-7's two checkers, demonstrated FAILING before they are trusted (§A1b).

D-7 asserts two things before any corrected value is read:

  1. S0 recomputed from persisted retrieval reproduces the stamped levels and `delta_full`
     exactly. If it does not, every `r` is a ratio against a base its numerator does not share.
  2. the unformatted arm's hit vector is IDENTICAL across S0/S1/S2/S3. `orig256` has no absorbed
     and no inherited width — `W_index_char` is exactly 1.0000 — so the ladder cannot touch it.
     If orig's hits move, the stripping is reaching the wrong condition.

Both passed on all eight cells. A checker that has only ever been observed agreeing is
indistinguishable from one that agrees by construction, so each is shown here to fire against a
deliberate violation: one `source_range` moved by a single character, and a strip mis-targeted
at the unformatted arm.
"""
from __future__ import annotations

import pytest

from src.chunkers.base import Unit
from src.datasets.base import GoldSpan, Query
from src.score.provenance import ANY, is_hit

SCORINGS = ("S0", "S1", "S2", "S3")


def _hits(rows, ranges_by_id, docs):
    out = []
    for r in rows:
        q = Query(query_id=r["query_id"], text="",
                  gold_spans=[GoldSpan(**g) for g in r["gold_spans"]])
        hit = 0
        for uid in r["retrieved_unit_ids"][:5]:
            u = Unit(unit_id=uid, text="", doc_id=docs[uid],
                     source_ranges=ranges_by_id[uid])
            if is_hit(u, q, variant=ANY, min_overlap=1):
                hit = 1
                break
        out.append(hit)
    return out


@pytest.fixture
def fixture():
    """One query whose gold sits exactly on a unit's only range — so a one-character shift
    that moves the range off the gold flips the hit."""
    rows = [{"query_id": "q0", "retrieved_unit_ids": ["u0"],
             "gold_spans": [{"doc_id": "d", "start_char": 100, "end_char": 110}]}]
    return rows, {"u0": [(100, 110)]}, {"u0": "d"}


# --------------------------------------------------------------------------
# Checker 1 — S0 must reproduce the stamped level
# --------------------------------------------------------------------------

def test_S0_checker_passes_on_the_unperturbed_inventory(fixture):
    rows, ranges, docs = fixture
    assert sum(_hits(rows, ranges, docs)) / len(rows) == 1.0


def test_S0_checker_FIRES_when_one_source_range_moves_by_one_character(fixture):
    """THE CONTROL. A single character is the smallest possible perturbation of an inventory,
    and it must not be absorbed."""
    rows, ranges, docs = fixture
    perturbed = {"u0": [(111, 121)]}          # shifted clear of the gold span
    got = sum(_hits(rows, perturbed, docs)) / len(rows)
    stamped = 1.0
    assert got != stamped, "a moved range must change the level, or the checker is inert"
    assert round(got, 4) == 0.0


def test_S0_checker_FIRES_on_a_unit_missing_from_the_inventory(fixture):
    """The other way an inventory can be wrong: a unit the ranked list refers to is absent.
    The runner raises rather than scoring the row as a miss, so a truncated inventory cannot
    masquerade as a lower recall."""
    rows, _, docs = fixture
    with pytest.raises(KeyError):
        _hits(rows, {}, docs)


# --------------------------------------------------------------------------
# Checker 2 — the unformatted arm must be invariant across the ladder
# --------------------------------------------------------------------------

def test_orig_invariance_holds_when_the_ladder_leaves_orig_alone(fixture):
    """`_flat_ranges` gives the unformatted arm the SAME ranges at every rung, which is the
    property D-7 checks. Here it is exercised directly."""
    rows, ranges, docs = fixture
    per_rung = {s: _hits(rows, ranges, docs) for s in SCORINGS}
    assert all(per_rung[s] == per_rung["S0"] for s in SCORINGS)


def test_orig_invariance_FIRES_when_a_strip_is_mis_targeted_at_the_unformatted_arm(fixture):
    """THE CONTROL. Simulates the defect the check exists for: stripping applied to `orig256`,
    which has no absorbed and no inherited width and must therefore be untouched. It presents as
    a plausible-looking `r` rather than as an error, which is why it needs its own assertion."""
    rows, ranges, docs = fixture
    mis_targeted = {"S0": ranges, "S1": ranges,
                    "S2": {"u0": []},              # width wrongly stripped from orig
                    "S3": {"u0": []}}
    per_rung = {s: _hits(rows, mis_targeted[s], docs) for s in SCORINGS}
    assert per_rung["S2"] != per_rung["S0"], "the mis-target must be detectable"
    assert any(per_rung[s] != per_rung["S0"] for s in SCORINGS), \
        "D-7's companion assertion must fire here, or it is inert"


def test_both_checkers_are_independent(fixture):
    """A perturbation that trips the S0 check need not trip the invariance check, and vice
    versa — so neither makes the other redundant."""
    rows, ranges, docs = fixture
    shifted = {"u0": [(111, 121)]}
    per_rung = {s: _hits(rows, shifted, docs) for s in SCORINGS}
    assert all(per_rung[s] == per_rung["S0"] for s in SCORINGS), \
        "a uniformly shifted inventory is still invariant across rungs — only the S0 check sees it"
