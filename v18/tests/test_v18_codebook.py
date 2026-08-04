"""PF-13 / G12 — the codebooks, and the acceptance census the ruling made mandatory.

The census is the point of this file. G12 happened because the acceptor's constraint was
half-checked: the 64-character limit was asserted, the alphabet was not, and no id was ever
validated against the pattern the API actually applies. So the requirement is not "test a
sample" or "test the worst case you thought of" — it is **generate every id the run can
possibly emit and validate each one against the real pattern.**

That distinction is the fourth instance of the family this programme keeps meeting: a
specification checked against a mental model of its domain rather than a census of it. A census
that stops at the convenient half is the same failure wearing a census's clothes.
"""
from __future__ import annotations

import re

import pytest

from v18.batch import CUSTOM_ID_PATTERN, custom_id, legal_coordinates, parse_custom_id
from v18.codebook import (ARM_CODES, CODE_TO_ARM, CODE_TO_METRIC, CODE_TO_STAGE, INDEX,
                          METRIC_CODES, STAGE_CODES, TRACKS, assert_bijections, call_plan,
                          codebook_sha256, load_codebook)

#: The API's own pattern, written out here independently of the module under test — a test that
#: imports the value it is checking proves only that the value equals itself.
API_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def test_the_module_pattern_matches_the_api_pattern():
    assert CUSTOM_ID_PATTERN.pattern == API_PATTERN.pattern


# ----------------------------------------------------------------------- the codebooks


@pytest.mark.parametrize("track", TRACKS)
def test_codebook_exists_and_is_internally_consistent(track):
    cb = load_codebook(track)
    assert cb["track"] == track
    assert cb["n"] == len(cb["ids"]) > 0
    assert len(set(cb["ids"])) == cb["n"], "duplicate query ids would alias two rows"


@pytest.mark.parametrize("track,n", [("A", 176), ("B", 150)])
def test_codebook_sizes_match_the_frozen_corpus(track, n):
    assert load_codebook(track)["n"] == n


@pytest.mark.parametrize("track", TRACKS)
def test_codebook_has_a_stable_digest(track):
    """The codebook is half the identity now, so it has to be pinnable in the manifest."""
    assert len(codebook_sha256(track)) == 64


@pytest.mark.parametrize("track", TRACKS)
def test_index_round_trips_for_every_query(track):
    cb = load_codebook(track)
    for i, qid in enumerate(cb["ids"]):
        assert INDEX.index_of(track, qid) == i
        assert INDEX.id_of(track, i) == qid


def test_an_unknown_query_id_is_refused_rather_than_guessed():
    with pytest.raises(KeyError, match="frozen codebook"):
        INDEX.index_of("A", "not-a-real-query-id")


# ------------------------------------------------------------------- the code tables


def test_code_tables_are_bijections():
    assert_bijections()


def test_metric_codes_cover_the_five_metrics_plus_the_metric_free_stage():
    from v18.judge_prompts import CALLS_PER_QUERY_ARM
    assert set(METRIC_CODES) == set(CALLS_PER_QUERY_ARM) | {None}
    assert METRIC_CODES[None] == "na", "generation needs a closed code, not an empty field"
    assert all(len(c) == 2 for c in METRIC_CODES.values())


def test_every_code_is_legal_in_isolation():
    for table in (METRIC_CODES, STAGE_CODES, ARM_CODES):
        for code in table.values():
            assert API_PATTERN.match(code), f"{code!r} is not a legal custom_id fragment"


def test_reverse_tables_invert_the_forward_ones():
    assert all(CODE_TO_METRIC[v] == k for k, v in METRIC_CODES.items())
    assert all(CODE_TO_STAGE[v] == k for k, v in STAGE_CODES.items())
    assert all(CODE_TO_ARM[v] == k for k, v in ARM_CODES.items())


# ------------------------------------- THE ACCEPTANCE CENSUS (G12 §1, derived per PF-15)


def _reps_for(track, arm):
    """The targeted-pair spec, as the request builder uses it (PF-3)."""
    return 3 if (track == "A" and arm in ("F768", "U768")) else 1


def _every_possible_custom_id():
    """Every id the run can emit, generated FROM the derived validity set.

    PF-15: the census iterates `legal_coordinates`, which is itself a function of `call_plan()`
    and the targeted-pair spec — the same objects the request builder consumes. A census
    enumerated in parallel with the builder can drift from it; one derived from the builder's
    own inputs cannot. That is identity-over-assertion applied to the census.
    """
    for stage, track, arm, metric, answer, sub in legal_coordinates(_reps_for):
        for i in range(INDEX.size(track)):
            yield custom_id(stage, track, arm, INDEX.id_of(track, i), metric, answer, sub)
    # generation ids are outside the judge call plan and are censused explicitly
    for track in TRACKS:
        for arm in ARM_CODES:
            for i in range(INDEX.size(track)):
                for a in range(_reps_for(track, arm)):
                    yield custom_id("generate", track, arm, INDEX.id_of(track, i), None, a, 0)


def test_acceptance_census_every_possible_id_satisfies_the_api_pattern():
    """Not a sample. Not the worst case. Every id the run can emit (G12 §1)."""
    n = 0
    for cid in _every_possible_custom_id():
        assert API_PATTERN.match(cid), f"census failure: {cid!r} ({len(cid)} chars)"
        n += 1
    assert n > 15_000, f"census covered only {n} ids"


def test_acceptance_census_every_possible_id_round_trips():
    """Legality is not enough — an id that cannot be decoded cannot identify a row."""
    for cid in _every_possible_custom_id():
        g = parse_custom_id(cid)
        assert custom_id(g["stage"], g["track"], g["arm"], g["query_id"],
                         g["metric"], g["answer"], g["sub"]) == cid


def test_census_reports_the_real_length_envelope():
    lengths = [len(cid) for cid in _every_possible_custom_id()]
    assert max(lengths) <= 64
    assert max(lengths) < 40, (
        f"longest id is {max(lengths)}; the encoding was chosen to leave real headroom under "
        f"the 64 limit, not to sit just inside it")


def test_ids_are_unique_across_the_whole_cross_product():
    ids = list(_every_possible_custom_id())
    assert len(set(ids)) == len(ids), "two distinct rows would share an id"


def test_the_census_reconciles_to_the_derived_judge_call_total():
    """The census and `judge_call_count()` are two routes to the same number (G14 §1)."""
    from v18.analysis import judge_call_count
    judge_ids = sum(INDEX.size(t) for stage, t, *_ in legal_coordinates(_reps_for))
    assert judge_ids == judge_call_count({"A": 176, "B": 150}, _reps_for) == 15_960


def test_the_two_judge_stages_partition_the_judge_calls():
    """j1 + j2 must account for every judge call exactly once — no gap, no overlap."""
    coords = legal_coordinates(_reps_for)
    j1 = sum(INDEX.size(t) for stage, t, *_ in coords if stage == "judge1")
    j2 = sum(INDEX.size(t) for stage, t, *_ in coords if stage == "judge2")
    assert j1 == 14_278 and j2 == 1_682
    assert j1 + j2 == 15_960


def test_only_faithfulness_appears_in_the_second_judge_stage():
    """J2 exists solely because faithfulness's verdicts depend on its extraction."""
    metrics = {m for stage, _t, _a, m, _an, _s in legal_coordinates(_reps_for) if stage == "judge2"}
    assert metrics == {"faithfulness"}


def test_context_metrics_never_carry_a_nonzero_answer_coordinate():
    """Context precision and recall read the retrieved contexts, which are answer-independent."""
    for stage, _t, _a, metric, answer, _s in legal_coordinates(_reps_for):
        if metric in ("context_precision", "context_recall"):
            assert answer == 0, f"{metric} should not vary by answer"


def test_the_sub_coordinate_matches_the_frozen_call_plan():
    from v18.judge_prompts import CALLS_PER_QUERY_ARM
    subs = {}
    for stage, _t, _a, metric, _an, sub in legal_coordinates(_reps_for):
        subs.setdefault(metric, set()).add(sub)
    assert subs["context_precision"] == set(range(CALLS_PER_QUERY_ARM["context_precision"]))
    assert subs["answer_relevancy"] == set(range(CALLS_PER_QUERY_ARM["answer_relevancy"]))
    assert subs["context_recall"] == subs["answer_correctness"] == {0}


# ------------------------------------------------------------------ shape, spot-checked


def test_the_ruling_example_shape_is_produced():
    """G14 §1's worked example: `v18-j1-B-u768-q149-cp-a0-s4`."""
    qid = INDEX.id_of("B", 149)
    assert custom_id("judge1", "B", "U768", qid, "context_precision", 0, 4) == \
        "v18-j1-B-u768-q149-cp-a0-s4"


def test_generation_ids_carry_the_metric_free_code():
    qid = INDEX.id_of("A", 0)
    assert custom_id("generate", "A", "F768", qid, None, 0, 0) == "v18-g-A-f768-q000-na-a0-s0"


def test_the_collision_that_caused_g14_is_now_expressible():
    """Five context-precision calls and nine answer-relevancy calls, all distinct."""
    qid = INDEX.id_of("A", 0)
    cp = {custom_id("judge1", "A", "F768", qid, "context_precision", 0, s) for s in range(5)}
    ar = {custom_id("judge1", "A", "F768", qid, "answer_relevancy", a, s)
          for a in range(3) for s in range(3)}
    assert len(cp) == 5 and len(ar) == 9
