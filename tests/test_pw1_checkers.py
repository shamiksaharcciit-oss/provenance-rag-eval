"""§A1b applied one level up: the GUARDS' CHECKERS must be demonstrated failing.

Three checker defects in two steps, and in every case the checker was less reliable than the
thing it was checking:

  1. guard 4 scanned only the top 5 and reported a RATE — 138/147, 148/160 — which reads as
     92-94% agreement. The true value was 147/147 and 160/160.
  2. the guard-1 delta check differenced ROUNDED levels and halted on a false failure:
     0.8352 - 0.7898 = 0.0454 against a frozen 0.0455, where the true delta is 8/176 = 1/22.
  3. discovery in case 2 was partly luck — "three of the four cells coincided, so only one
     surfaced it."

A checker that has only ever been observed AGREEING is indistinguishable from a checker that
agrees by construction. So each one here is fed a synthetic cell wrong by exactly ONE query on
the metric's grid, and must halt.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def g1():
    sys.path.insert(0, str(ROOT))
    return _load("pw1_guard1_all", "scripts/pw1_guard1_all.py")


# --------------------------------------------------------------------------
# The delta checker: full precision, rounded exactly once
# --------------------------------------------------------------------------

N_A, N_B = 176, 150


def _delta(hits_c4: int, hits_c0: int, n: int) -> float:
    """The corrected computation: difference the UNROUNDED levels, round once."""
    return round(hits_c4 / n - hits_c0 / n, 4)


def _delta_rounded_first(hits_c4: int, hits_c0: int, n: int) -> float:
    """The defect: round each level, then difference."""
    return round(round(hits_c4 / n, 4) - round(hits_c0 / n, 4), 4)


def test_the_rounding_defect_is_reproduced_exactly():
    """The bge/Track A cell that produced the false halt. If this ever stops differing, the
    regression that motivated the fix has gone and the test is inert."""
    assert _delta(147, 139, N_A) == 0.0455
    assert _delta_rounded_first(147, 139, N_A) == 0.0454
    assert _delta(147, 139, N_A) != _delta_rounded_first(147, 139, N_A)


def test_three_of_four_published_cells_coincided_which_is_why_it_nearly_escaped():
    """Records the near-miss quantitatively: the defect was invisible on 3 of 4 cells."""
    cells = [(148, 138, N_A), (147, 139, N_A), (63, 58, N_B), (60, 53, N_B)]
    differing = [c for c in cells if _delta(*c) != _delta_rounded_first(*c)]
    assert len(differing) == 1, differing


def test_delta_checker_halts_on_a_cell_wrong_by_exactly_one_query():
    """THE CONTROL. One flipped query is 1/176 = 0.0057 on Track A — the smallest possible
    real error. The checker must not absorb it."""
    frozen = _delta(147, 139, N_A)
    assert _delta(148, 139, N_A) != frozen, "one extra hit must move the delta"
    assert _delta(146, 139, N_A) != frozen, "one fewer hit must move the delta"
    assert abs(_delta(148, 139, N_A) - frozen) == pytest.approx(1 / N_A, abs=1e-4)


def test_delta_checker_halts_on_a_one_query_error_on_track_B_too():
    frozen = _delta(60, 53, N_B)
    assert _delta(61, 53, N_B) != frozen
    assert abs(_delta(61, 53, N_B) - frozen) == pytest.approx(1 / N_B, abs=1e-4)


# --------------------------------------------------------------------------
# The guard-4 checker: exact equality, never a rate (template A1d)
# --------------------------------------------------------------------------

class _U:
    def __init__(self, uid, ranges):
        self.unit_id, self.source_ranges = uid, ranges


def test_guard4_returns_full_agreement_when_the_rebuild_matches(g1):
    rows = [{"retrieved_unit_ids": [f"u{i}"], "top_hit_provenance": [[0, 10]]} for i in range(5)]
    by_id = {f"u{i}": _U(f"u{i}", [(0, 10)]) for i in range(5)}
    assert g1.guard4(rows, by_id) == (5, 5)


def test_guard4_detects_a_single_disagreeing_row(g1):
    """One row whose rebuilt ranges differ must drop the count. If the checker reported a rate
    and a caller accepted 4/5 as 'mostly fine', a real rebuild drift would ship."""
    rows = [{"retrieved_unit_ids": [f"u{i}"], "top_hit_provenance": [[0, 10]]} for i in range(5)]
    by_id = {f"u{i}": _U(f"u{i}", [(0, 10)]) for i in range(5)}
    by_id["u3"] = _U("u3", [(0, 11)])            # off by one character
    agreed, checked = g1.guard4(rows, by_id)
    assert (agreed, checked) == (4, 5)
    assert agreed != checked, "the caller's assertion is agreed == checked, and it must fail here"


def test_guard4_scans_the_full_retrieved_list_not_just_the_top_k(g1):
    """The original defect: a row whose match sits at rank 6-10 was structurally unmatchable."""
    rows = [{"retrieved_unit_ids": [f"x{i}" for i in range(5)] + ["deep"],
             "top_hit_provenance": [[100, 200]]}]
    by_id = {f"x{i}": _U(f"x{i}", [(0, 10)]) for i in range(5)}
    by_id["deep"] = _U("deep", [(100, 200)])
    assert g1.guard4(rows, by_id) == (1, 1)


def test_guard4_ignores_rows_with_no_recorded_provenance(g1):
    """Rows without a hit within k=10 carry no `top_hit_provenance` and must not be counted as
    either agreement or disagreement."""
    rows = [{"retrieved_unit_ids": ["u0"], "top_hit_provenance": None},
            {"retrieved_unit_ids": ["u0"], "top_hit_provenance": [[0, 10]]}]
    by_id = {"u0": _U("u0", [(0, 10)])}
    assert g1.guard4(rows, by_id) == (1, 1)


# --------------------------------------------------------------------------
# The re-score checker
# --------------------------------------------------------------------------

def test_rescore_halts_when_a_retrieved_unit_id_is_absent_from_the_rebuild(g1):
    """A missing id means the rebuild is not the corpus that produced the ranked list. The
    checker must surface it rather than silently scoring the row as a miss."""
    rows = [{"query_id": "q", "gold_spans": [{"doc_id": "d", "start_char": 0, "end_char": 5}],
             "retrieved_unit_ids": ["ghost"]}]
    got, missing = g1.rescore(rows, {})
    assert missing == ["ghost"], "a missing unit id must be reported, not absorbed"
    assert got == 0.0


def test_rescore_counts_a_hit_only_once_per_query(g1):
    """Two retrieved units both overlapping gold is still one hit — recall@k, not a tally."""
    from src.chunkers.base import Unit
    rows = [{"query_id": "q", "gold_spans": [{"doc_id": "d", "start_char": 0, "end_char": 5}],
             "retrieved_unit_ids": ["a", "b"]}]
    by_id = {"a": Unit(unit_id="a", text="", doc_id="d", source_ranges=[(0, 5)]),
             "b": Unit(unit_id="b", text="", doc_id="d", source_ranges=[(0, 5)])}
    got, missing = g1.rescore(rows, by_id)
    assert got == 1.0 and not missing
