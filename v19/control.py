"""v1.9 §2 — the context-ablation control, and package construction for it.

PR-0 exists because E2 had no analogue of PE1-4. On Track B especially the generator may answer
real published prose from its own training rather than from the package, in which case F1
measures memory and every contrast is noise around a ceiling.

The control pairs each sampled query with (a) its correct `F768` package and (b) query *i*+1's
package, wrapping around. The mismatch rule is deliberately the simplest one that cannot
accidentally hand a query its own gold: successor-with-wraparound over a fixed, frozen sample.

PACKAGE SELECTION USES OVERLAP, NOT COVERAGE. `build_package` selects units whose
`source_ranges` *overlap* the gold span; it never asks whether they cover every character. That
is why v1.7's whitespace-coverage defect does not reach v1.9 — a formatter unit with
inter-sentence gaps still overlaps, so it is still selected. `tests/test_v19_packages.py` proves
this on a unit whose ranges have a hole exactly where the gold sits, rather than asserting it.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from src.v17.packages import B2_CAP, B2_FLOOR, matched_budget

CONTROL_N = 30
CONTROL_SEED = 1337


@dataclass
class ControlPair:
    query_id: str
    correct_package_of: str      # query_id whose package is the correct one (== query_id)
    mismatched_package_of: str   # query_id whose package is handed over instead


def draw_control_sample(query_ids: list[str], n: int = CONTROL_N,
                        seed: int = CONTROL_SEED) -> list[str]:
    """A fixed sample, drawn once and frozen at Gate 0 (§2).

    Sorted before sampling so the draw depends on the query id set and the seed, never on the
    order the loader happened to produce.
    """
    if len(query_ids) < n:
        raise ValueError(f"cannot draw {n} control queries from {len(query_ids)}")
    rng = random.Random(seed)
    return sorted(rng.sample(sorted(query_ids), n))


def pair_with_successor(sample: list[str]) -> list[ControlPair]:
    """Query *i* receives query *i*+1's package, wrapping around (§2)."""
    if len(sample) < 2:
        raise ValueError("the mismatch rule needs at least two queries")
    out = []
    for i, qid in enumerate(sample):
        other = sample[(i + 1) % len(sample)]
        assert other != qid, "a query would receive its own package; the mismatch is not a mismatch"
        out.append(ControlPair(query_id=qid, correct_package_of=qid, mismatched_package_of=other))
    return out


def b2_for_query(inventories: dict, gold) -> dict:
    """B2(q) across ALL THREE arms (§1), with the escalation attribution.

    `inventories` maps arm id to that arm's unit list. Every arm v1.9 packages must be present:
    an arm left out cannot raise the budget, and a budget that does not clear an arm's gold is
    the defect PF-2 removed.
    """
    mb = matched_budget(inventories, gold, floor=B2_FLOOR, cap=B2_CAP)
    return {"b2": mb.b2, "escalated": mb.escalated, "set_by": mb.set_by, "costs": mb.costs}
