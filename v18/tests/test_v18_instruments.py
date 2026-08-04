"""§9 — the I1 formulas, hand-checked, and the composite-direction tests.

Every expected value below is worked out by hand in the test itself rather than captured from a
run. A metric test whose expectation came from the code it tests pins the bug as firmly as the
behaviour, which is the failure mode `tests/test_scorer.py` was written to avoid in v1.1 and the
same discipline applies here.

None of these tests calls a model. I1's scorers take judge replies as *inputs*, which is what
makes the whole instrument testable at Gate 0 with zero spend.
"""
from __future__ import annotations

import pytest

from v18.instruments import (ANSWER_METRICS, CONTEXT_METRICS, JudgeReplyError,
                             _verdict_list, answer_composite, answer_correctness,
                             answer_relevancy, context_composite, context_precision,
                             context_recall, faithfulness, normalise, parse_json_object,
                             preference, split_reference_sentences, statement_f1, token_f1)

# ------------------------------------------------------------------------- context precision


def test_context_precision_hand_checked_mixed():
    """verdicts [1,0,1,0,0]: (1/1)*1 + (2/3)*1 = 1.6667 over 2 relevant = 0.8333."""
    assert context_precision([1, 0, 1, 0, 0]) == pytest.approx((1.0 + 2 / 3) / 2)


def test_context_precision_rank_matters():
    """The same single relevant context scores lower the further down it sits."""
    assert context_precision([1, 0, 0, 0, 0]) == pytest.approx(1.0)
    assert context_precision([0, 0, 0, 1, 0]) == pytest.approx(0.25)


def test_context_precision_all_and_none():
    assert context_precision([1, 1, 1, 1, 1]) == pytest.approx(1.0)
    assert context_precision([0, 0, 0, 0, 0]) == 0.0
    assert context_precision([]) == 0.0


# ----------------------------------------------------------------- recall / faithfulness


def test_context_recall_is_the_attributable_fraction():
    assert context_recall([1, 1, 0, 0]) == pytest.approx(0.5)
    assert context_recall([]) == 0.0


def test_faithfulness_is_the_supported_fraction():
    assert faithfulness([1, 1, 1, 0]) == pytest.approx(0.75)


def test_faithfulness_of_a_claimless_answer_is_one_not_nan():
    """A NaN here would silently drop the query from one arm and break the pairing."""
    value = faithfulness([])
    assert value == 1.0
    assert value == value  # not NaN


# ---------------------------------------------------------------------- answer relevancy


def test_answer_relevancy_averages_and_clamps():
    assert answer_relevancy([0.8, 0.6, 0.7]) == pytest.approx(0.7)
    assert answer_relevancy([-0.2, -0.4]) == 0.0
    assert answer_relevancy([]) == 0.0


# -------------------------------------------------------------------- answer correctness


def test_statement_f1_hand_checked():
    """TP=3, FP=1, FN=2 -> 3 / (3 + 0.5*3) = 0.6667."""
    assert statement_f1(3, 1, 2) == pytest.approx(3 / 4.5)
    assert statement_f1(0, 0, 0) == 0.0
    assert statement_f1(2, 0, 0) == pytest.approx(1.0)


def test_answer_correctness_blend_hand_checked():
    """0.75 * 0.6667 + 0.25 * 0.5 = 0.625."""
    assert answer_correctness(3, 1, 2, similarity=0.5) == pytest.approx(0.75 * (3 / 4.5) + 0.125)


def test_answer_correctness_weights_sum_to_one():
    from v18.judge_prompts import ANSWER_CORRECTNESS_WEIGHTS
    assert sum(ANSWER_CORRECTNESS_WEIGHTS) == pytest.approx(1.0)


# ------------------------------------------------------------------------------- parsing


def test_parse_json_object_tolerates_a_fence_only():
    assert parse_json_object('```json\n{"verdict": 1}\n```') == {"verdict": 1}
    assert parse_json_object('  {"verdict": 0}  ') == {"verdict": 0}


@pytest.mark.parametrize("bad", ["the verdict is 1", "[1, 0]", "", "{'verdict': 1}"])
def test_parse_json_object_raises_rather_than_repairs(bad):
    with pytest.raises(JudgeReplyError):
        parse_json_object(bad)


def test_verdict_list_enforces_length_and_binarity():
    assert _verdict_list('{"verdicts": [1, 0, 1]}', "verdicts", 3) == [1, 0, 1]
    with pytest.raises(JudgeReplyError):
        _verdict_list('{"verdicts": [1, 0]}', "verdicts", 3)      # wrong length
    with pytest.raises(JudgeReplyError):
        _verdict_list('{"verdicts": [1, 2, 0]}', "verdicts", 3)   # not binary
    with pytest.raises(JudgeReplyError):
        _verdict_list('{"other": [1]}', "verdicts", 1)            # missing key


def test_no_default_is_invented_for_an_unparseable_reply():
    """The failure mode this guards is v1.7 F5's family: a fallback replacing a real value."""
    with pytest.raises(JudgeReplyError):
        _verdict_list("I could not decide", "verdicts", 2)


# ------------------------------------------------------------------- reference sentences


def test_split_reference_sentences_uses_the_harness_splitter():
    out = split_reference_sentences("The cat sat. The dog barked.")
    assert out == ["The cat sat.", "The dog barked."]


def test_split_reference_without_punctuation_yields_one_unit():
    assert split_reference_sentences("no terminal punctuation here") == [
        "no terminal punctuation here"]


def test_split_empty_reference_yields_nothing():
    assert split_reference_sentences("   ") == []


# ------------------------------------------------------------- §9 composite-direction tests


def test_composites_cover_exactly_the_declared_metric_sets():
    assert CONTEXT_METRICS == ("context_precision", "context_recall")
    assert ANSWER_METRICS == ("faithfulness", "answer_relevancy", "answer_correctness")


def test_context_composite_is_the_mean_and_rises_with_its_members():
    low = {"context_precision": 0.2, "context_recall": 0.4}
    high = {"context_precision": 0.6, "context_recall": 0.8}
    assert context_composite(low) == pytest.approx(0.3)
    assert context_composite(high) == pytest.approx(0.7)
    assert context_composite(high) > context_composite(low), "higher is better"


def test_answer_composite_is_the_mean_and_rises_with_its_members():
    low = {"faithfulness": 0.1, "answer_relevancy": 0.2, "answer_correctness": 0.3}
    high = {"faithfulness": 0.7, "answer_relevancy": 0.8, "answer_correctness": 0.9}
    assert answer_composite(low) == pytest.approx(0.2)
    assert answer_composite(high) == pytest.approx(0.8)
    assert answer_composite(high) > answer_composite(low), "higher is better"


def test_composite_direction_is_not_accidentally_inverted():
    """One member improving, all else equal, must not lower the composite."""
    base = {"faithfulness": 0.5, "answer_relevancy": 0.5, "answer_correctness": 0.5}
    for m in ANSWER_METRICS:
        better = dict(base, **{m: 0.9})
        assert answer_composite(better) > answer_composite(base), m


def test_preference_sign_convention():
    assert preference(0.9, 0.1) == 1     # treatment better
    assert preference(0.1, 0.9) == -1    # control better
    assert preference(0.5, 0.5) == 0     # tie


# --------------------------------------------------------------- I2, exercised by citation


def test_token_f1_is_symmetric_in_the_obvious_case_and_bounded():
    assert token_f1("the cat sat", "the cat sat") == pytest.approx(1.0)
    assert token_f1("", "the cat") == 0.0
    assert 0.0 < token_f1("the cat", "the cat sat on the mat") < 1.0


def test_normalisation_strips_punctuation_by_category():
    """The same word in curly and straight quotes must normalise alike.

    The word is held constant on purpose: comparing two *different* words would pass or fail on
    the words rather than on the quoting, which is the thing under test.
    """
    assert normalise("State-of-the-Art!") == "state of the art"
    assert normalise("“word”") == normalise('"word"') == "word"


# ------------------------------------------- PF-16: the trailing-object rule (G15 §1)


def _legacy_parse(reply):
    """The pre-amendment parser, reproduced so the identity claim is checked against it.

    Asserting the new parser "behaves the same on conforming replies" is only meaningful
    against the actual old behaviour, not against a paraphrase of it.
    """
    import json as _json
    import re as _re
    text = reply.strip()
    if text.startswith("```"):
        text = _re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = _re.sub(r"\s*```$", "", text).strip()
    obj = _json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError("not an object")
    return obj


CONFORMING = [
    '{"verdict": 1}',
    '{"verdicts": [1, 0, 1]}',
    '{"statements": ["a", "b"]}',
    '{"question": "what is it?"}',
    '{"TP": 3, "FP": 1, "FN": 2}',
    '  {"verdict": 0}  ',
    '```json\n{"verdicts": [1]}\n```',
    '{"nested": {"a": 1}}',
]


@pytest.mark.parametrize("reply", CONFORMING)
def test_the_amendment_is_the_identity_on_conforming_replies(reply):
    """G15 §1.1: no already-parseable cell can change value."""
    assert parse_json_object(reply) == _legacy_parse(reply)


def test_prose_then_json_is_recovered():
    """The 101 replies the frozen parser refused: reasoning first, the demanded object last."""
    reply = ('The context does not identify the license clearly, and the ports conflict.\n\n'
             '{"verdicts": [0, 0]}')
    assert parse_json_object(reply) == {"verdicts": [0, 0]}


def test_recovery_handles_braces_inside_the_prose():
    """Backwards brace-matching, so an object is recovered whole rather than by regex."""
    reply = 'I considered the set {a, b} and concluded.\n{"verdict": 1}'
    assert parse_json_object(reply) == {"verdict": 1}


def test_a_nested_object_is_recovered_whole():
    assert parse_json_object('reasoning\n{"a": {"b": 2}}') == {"a": {"b": 2}}


# --- what still refuses hard (G15 §1) ---------------------------------------------------


def test_no_trailing_object_still_refuses():
    with pytest.raises(JudgeReplyError, match="no JSON object"):
        parse_json_object("I decline to answer in JSON.")


def test_two_candidate_trailing_objects_refuse_as_ambiguous():
    """Genuine ambiguity is exactly what the frozen strictness protected."""
    with pytest.raises(JudgeReplyError, match="ambiguous"):
        parse_json_object('reasoning {"verdict": 0} {"verdict": 1}')


def test_malformed_trailing_json_still_refuses():
    with pytest.raises(JudgeReplyError, match="not JSON"):
        parse_json_object('reasoning\n{"verdicts": [1, }')


def test_a_wrong_key_shape_still_refuses():
    with pytest.raises(JudgeReplyError, match="key shape"):
        parse_json_object('{"verdict": 1}', expected_keys={"verdicts"})


def test_the_expected_key_shape_passes():
    assert parse_json_object('{"verdicts": [1]}', expected_keys={"verdicts"}) == {"verdicts": [1]}


def test_a_trailing_non_object_still_refuses():
    with pytest.raises(JudgeReplyError):
        parse_json_object("reasoning then [1, 2, 3]")


def test_no_value_is_coerced_or_scavenged():
    """"No regex scavenging inside objects" survives: a bare number is not a verdict."""
    with pytest.raises(JudgeReplyError):
        parse_json_object("the verdict is 1")
