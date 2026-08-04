"""PF-15 — the J1/J2 builders, and the conduct clause enforced as a control rather than a hope.

G14 §3 permits the builder to read J1's extraction outputs, because a verdict prompt needs the
statements the extraction produced, and forbids anything numeric being derived from that read.
A rule of that shape decays silently: nothing breaks if someone later imports a scorer "just to
check something". So the first test inspects this builder's own source for the forbidden names.
"""
from __future__ import annotations

import inspect

import pytest

from v18 import judge_build
from v18.batch import parse_custom_id
from v18.codebook import INDEX
from v18.judge_build import build_j1, build_j2, statements_from_reply


def _cell(track="A", arm="F768", n_answers=3, n_contexts=5):
    return {"track": track, "arm": arm, "query_id": INDEX.id_of(track, 0),
            "question": "what is the thing?", "reference": "The thing is a widget. It is blue.",
            "contexts": [f"ctx{i}" for i in range(n_contexts)],
            "answers": {a: f"answer-{a}" for a in range(n_answers)}}


# ------------------------------------------------- the conduct clause, as a control


FORBIDDEN = ("token_f1", "context_precision(", "context_recall(", "faithfulness(",
             "answer_relevancy(", "answer_correctness(", "statement_f1", "b1_",
             "v18.analysis", "median", "composite")


def test_the_builder_imports_no_scorer_and_computes_no_number():
    """G14 §3: prompts yes, numbers no — checked against the source, not the intention."""
    src = inspect.getsource(judge_build)
    body = "\n".join(line for line in src.splitlines()
                     if not line.strip().startswith("#"))
    for name in FORBIDDEN:
        assert name not in body, (
            f"{name!r} appears in judge_build; the construction path must derive no numbers "
            f"from J1's outputs (G14 §3)")


def test_the_builder_does_not_import_the_analysis_module():
    assert "analysis" not in {m.split(".")[-1] for m in dir(judge_build)}


# ------------------------------------------------------------------------- J1


def test_j1_emits_the_derived_call_plan_for_a_targeted_cell():
    reqs = build_j1(_cell(n_answers=3))
    # 5 context_precision + 1 context_recall + 3 answers x (1 fa + 3 ar + 1 ac) = 21
    assert len(reqs) == 21
    ids = [parse_custom_id(r["custom_id"]) for r in reqs]
    assert sum(1 for i in ids if i["metric"] == "context_precision") == 5
    assert sum(1 for i in ids if i["metric"] == "answer_relevancy") == 9
    assert sum(1 for i in ids if i["metric"] == "faithfulness") == 3
    assert all(i["stage"] == "judge1" for i in ids)


def test_j1_emits_the_smaller_plan_for_a_single_answer_cell():
    reqs = build_j1(_cell(n_answers=1))
    assert len(reqs) == 11          # 5 + 1 + (1 + 3 + 1)


def test_context_precision_calls_are_one_per_context_in_rank_order():
    cell = _cell()
    reqs = build_j1(cell)
    cp = [r for r in reqs if parse_custom_id(r["custom_id"])["metric"] == "context_precision"]
    for sub, r in enumerate(cp):
        assert parse_custom_id(r["custom_id"])["sub"] == sub
        assert cell["contexts"][sub] in r["prompt"]


def test_context_level_calls_carry_answer_zero():
    for r in build_j1(_cell()):
        p = parse_custom_id(r["custom_id"])
        if p["metric"] in ("context_precision", "context_recall"):
            assert p["answer"] == 0


def test_answer_level_calls_reference_their_own_answer():
    for r in build_j1(_cell()):
        p = parse_custom_id(r["custom_id"])
        if p["metric"] in ("answer_relevancy", "answer_correctness", "faithfulness"):
            assert f"answer-{p['answer']}" in r["prompt"]


def test_every_j1_id_is_unique():
    reqs = build_j1(_cell())
    assert len({r["custom_id"] for r in reqs}) == len(reqs)


def test_the_three_answer_relevancy_samples_share_a_prompt_but_not_an_id():
    """Strictness 3 issues the same prompt three times; only the id keeps them apart."""
    reqs = [r for r in build_j1(_cell(n_answers=1))
            if parse_custom_id(r["custom_id"])["metric"] == "answer_relevancy"]
    assert len({r["prompt"] for r in reqs}) == 1
    assert len({r["custom_id"] for r in reqs}) == 3


# ------------------------------------------------------------------------- J2


def test_j2_builds_one_verdict_call_per_answer_from_the_extraction():
    replies = {a: '{"statements": ["the thing is a widget", "it is blue"]}' for a in range(3)}
    reqs = build_j2(_cell(), replies)
    assert len(reqs) == 3
    ids = [parse_custom_id(r["custom_id"]) for r in reqs]
    assert all(i["stage"] == "judge2" and i["metric"] == "faithfulness" for i in ids)
    assert {i["answer"] for i in ids} == {0, 1, 2}
    assert "1. the thing is a widget" in reqs[0]["prompt"]


def test_j2_keeps_a_row_for_a_claimless_answer():
    """No row would leave the scorer unable to tell abstention from a lost request."""
    reqs = build_j2(_cell(n_answers=1), {0: '{"statements": []}'})
    assert len(reqs) == 1
    assert "no factual claim" in reqs[0]["prompt"]


def test_an_unparseable_extraction_raises_rather_than_defaulting():
    """An empty default would silently become faithfulness = 1.0 for that answer."""
    from v18.instruments import JudgeReplyError
    with pytest.raises(JudgeReplyError):
        statements_from_reply("I could not extract statements")
    with pytest.raises(JudgeReplyError, match="statement list"):
        statements_from_reply('{"something_else": 1}')


def test_statements_are_read_verbatim():
    got = statements_from_reply('{"statements": ["a", "b"]}')
    assert got == ["a", "b"]
