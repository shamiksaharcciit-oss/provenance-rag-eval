"""B3 — NC-A and NC-B, the frozen negative controls for the scoring ladder.

`guard_2_negative_controls` in `posthoc_PW1_provenance_width.json`:

    NC-A  gold falls ONLY inside an absorbed range:
          S0 hit | S1 MISS | S2 HIT | S3 MISS
    NC-B  gold falls ONLY inside an inherited range:
          S0 hit | S1 HIT  | S2 MISS | S3 MISS

NC-B is what separates "the tight arm is implemented" from "asserted". Its S1 expectation is a
HIT: if S1 misses there, S1 is over-stripping and its numbers are wrong. NC-A's S2 expectation is
likewise a HIT — S2 retains absorbed ranges, because that is the de-duplication credit the paper's
methods describe and defend.

Together the two controls pin all four rungs from both directions: every rung is required to hit
on one control and miss on the other, so no rung can be silently equal to another.

The formatter runs on its RULE-BASED path (`provider = none`), which is deterministic and needs
no cache, so these controls do not depend on any recorded LLM output.
"""
from __future__ import annotations

import pytest

from src.chunkers.base import ChunkContext
from src.datasets.base import Document, GoldSpan, Query
from src.llm.client import LLMClient
from src.pw1.tight_provenance import build_tight_units
from src.score.provenance import ANY, is_hit

SCORINGS = ("S0", "S1", "S2", "S3")

# Small sizes so the constructed cases are exact and readable. The controls test the SCORING
# LOGIC, not the production sizes; `test_both_channels_are_non_empty_at_production_sizes` covers
# the production configuration separately.
PARAMS = {"chunk_tokens": 20, "overlap_frac": 0.0, "reference_resolution": False,
          "dedup": True, "right_size": True, "soft_target_tokens": 24,
          "min_unit_tokens": 0}

# NC-B needs SEGMENTS THAT HOLD SEVERAL SENTENCES. The first version of this control used the
# parameters above and found no inheriting chunk at all: at soft_target 24 each ~13-token
# sentence became its own segment, so a chunk overlapping a segment always covered the single
# sentence in it and there were no siblings to inherit. Production has ~5.5 sentences per
# segment (soft_target 384 against ~70-token sentences), which is the shape reproduced here.
NC_B_PARAMS = {**PARAMS, "chunk_tokens": 40, "soft_target_tokens": 60}


def _ctx() -> ChunkContext:
    """Rule-based formatter: deterministic, no network, no cache dependency."""
    return ChunkContext(embedder=None, llm=LLMClient(provider="none"), config={})


def _score(unit_tight, gold: GoldSpan) -> dict:
    q = Query(query_id="q", text="", gold_spans=[gold])
    return {s: is_hit(unit_tight.as_unit(s), q, variant=ANY, min_overlap=1) for s in SCORINGS}


# ==========================================================================
# NC-A — gold lies ONLY inside an absorbed range
# ==========================================================================

def test_NC_A_gold_only_in_an_absorbed_range():
    """A restated sentence is dropped; the canonical one absorbs its original range. Gold is
    placed ONLY on the dropped copy, so the surviving chunk can reach it solely through the
    absorbed range."""
    dup = "The Kestrel indexer listens on port 50051."
    doc_text = f"{dup} Operators override it with an env var. {dup}"
    doc = Document(doc_id="ncA", text=doc_text)

    units = build_tight_units(doc, PARAMS, _ctx())
    assert units, "the control needs at least one chunk"

    second = doc_text.rindex(dup)
    gold = GoldSpan(doc_id="ncA", start_char=second, end_char=second + len(dup))

    carriers = [u for u in units if any(s <= gold.start_char < e for s, e in u.absorbed_own)]
    assert carriers, ("no chunk absorbed the duplicate's range — the control is not wired and "
                      "proves nothing")
    got = _score(carriers[0], gold)
    assert got == {"S0": True, "S1": False, "S2": True, "S3": False}, got


def test_NC_A_S2_hit_is_the_defended_dedup_credit_not_an_accident():
    """S2 must retain absorbed ranges. If S2 reported a miss here it would be over-stripping,
    and every S2 number would be wrong in the conservative direction."""
    dup = "Shard rebuild completes in ninety seconds."
    doc_text = f"{dup} The planner schedules compaction nightly. {dup}"
    doc = Document(doc_id="ncA2", text=doc_text)
    units = build_tight_units(doc, PARAMS, _ctx())
    second = doc_text.rindex(dup)
    gold = GoldSpan(doc_id="ncA2", start_char=second, end_char=second + len(dup))
    carriers = [u for u in units if any(s <= gold.start_char < e for s, e in u.absorbed_own)]
    assert carriers
    assert _score(carriers[0], gold)["S2"] is True


# ==========================================================================
# NC-B — gold lies ONLY inside an inherited range
# ==========================================================================

def _nc_b_case():
    """A document long enough to form several segments, so some chunk overlaps a segment whose
    sentences it does not all contain."""
    sents = [f"Node {i:02d} reports heartbeat to the coordinator." for i in range(40)]
    doc_text = " ".join(sents)
    doc = Document(doc_id="ncB", text=doc_text)
    units = build_tight_units(doc, NC_B_PARAMS, _ctx())
    for u in units:
        if u.inherited_own:
            # a sibling range this chunk claims but whose text it does not contain
            s, e = u.inherited_own[0]
            if not any(os_ <= s < oe for os_, oe in u.own):
                return u, GoldSpan(doc_id="ncB", start_char=s, end_char=e)
    return None, None


def test_NC_B_gold_only_in_an_inherited_range():
    """THE CONTROL THAT MATTERS. It is the only thing separating 'the tight arm is implemented'
    from 'the tight arm is asserted'."""
    unit, gold = _nc_b_case()
    assert unit is not None, ("no chunk inherited a sibling range — the control is not wired "
                              "and every S2 number would be unverified")
    got = _score(unit, gold)
    assert got == {"S0": True, "S1": True, "S2": False, "S3": False}, got


def test_NC_B_S1_hit_proves_S1_does_not_over_strip():
    """S1 removes absorption only. If it missed on an inherited-range gold, S1 would be
    stripping the channel it is defined to keep, and its numbers would be wrong."""
    unit, gold = _nc_b_case()
    assert unit is not None
    assert _score(unit, gold)["S1"] is True


# ==========================================================================
# The two controls together pin every rung from both directions
# ==========================================================================

def test_every_rung_is_distinguished_by_at_least_one_control():
    """No rung may be silently equal to another: each of the four differs from each other on at
    least one of the two controls."""
    dup = "The Kestrel indexer listens on port 50051."
    a_text = f"{dup} Operators override it with an env var. {dup}"
    a_doc = Document(doc_id="ncA", text=a_text)
    a_units = build_tight_units(a_doc, PARAMS, _ctx())
    second = a_text.rindex(dup)
    a_gold = GoldSpan(doc_id="ncA", start_char=second, end_char=second + len(dup))
    a_unit = next(u for u in a_units
                  if any(s <= a_gold.start_char < e for s, e in u.absorbed_own))
    a = _score(a_unit, a_gold)

    b_unit, b_gold = _nc_b_case()
    assert b_unit is not None
    b = _score(b_unit, b_gold)

    profiles = {s: (a[s], b[s]) for s in SCORINGS}
    assert len(set(profiles.values())) == len(SCORINGS), (
        f"two rungs are indistinguishable across both controls: {profiles}")
    assert profiles == {"S0": (True, True), "S1": (False, True),
                        "S2": (True, False), "S3": (False, False)}, profiles


def test_the_ladder_is_monotone_in_ranges():
    """S3 subset of S1 and S2, both subset of S0. A rung that added ranges would break the
    r <= 1 invariant the A7 halt encodes."""
    unit, _ = _nc_b_case()
    assert unit is not None

    def covered(rs):
        return {c for s, e in rs for c in range(s, e)}

    s0, s1, s2, s3 = (covered(getattr(unit, s)) for s in SCORINGS)
    assert s3 <= s1 <= s0 and s3 <= s2 <= s0
    assert s1 != s0 or s2 != s0, "this chunk exercises neither channel; pick another"


def test_both_channels_are_non_empty_at_production_sizes():
    """The controls use small sizes for exactness. Guard against the production configuration
    having no absorbed or no inherited ranges at all, which would make the arms vacuous.

    Uses the step-0 measurement rather than rebuilding the corpus: absorbed surface is 12,019
    characters on Track A and 2,887 on Track B, and inheritance is 97.35% / 99.83% of the excess.
    """
    import json
    import pathlib
    p = pathlib.Path(__file__).resolve().parents[1] / "results_pw1" / "step0.json"
    if not p.is_file():
        pytest.skip("step 0 artifact not present")
    d = json.loads(p.read_text(encoding="utf-8"))
    for track in ("A", "B"):
        dec = d["tracks"][track]["fmt256_decomposition_per_chunk"]
        assert dec["absorbed"] > 0, f"track {track}: no absorbed ranges — NC-A would be vacuous"
        assert dec["inheritance_share_of_excess"] > 0, \
            f"track {track}: no inherited ranges — NC-B would be vacuous"
