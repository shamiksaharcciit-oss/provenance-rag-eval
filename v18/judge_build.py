"""v1.8 PF-15 — construct the J1 and J2 judge request sets. Construction only, never scoring.

**The conduct clause (G14 §3).** Building J2's prompts requires reading J1's faithfulness
extraction outputs, because a verdict prompt needs the statement list the extraction produced.
That reading is *construction*, not peeking: it is confined to statement lists, performed by
this builder, and nothing numeric is derived from it. The boundary the ruling draws is about
what is **derived** from the reads — prompts yes, numbers no.

So this module imports no scorer and no aggregator. It may not compute token-F1, may not turn a
verdict into a metric value, and may not assemble a per-arm signal. `test_v18_judge_build.py`
enforces that by inspecting this module's own source for the forbidden names, because a
conduct rule that lives only in a docstring is a hope rather than a control.

The call plan is not restated here either — `legal_coordinates` derives it from
`CALLS_PER_QUERY_ARM`, and this builder walks that derivation, so the requests and the
acceptance census are two consumers of one source (G14 §1).
"""
from __future__ import annotations

from v18.batch import custom_id
from v18.instruments import parse_json_object, split_reference_sentences
from v18.judge_prompts import (ANSWER_CORRECTNESS_PROMPT, ANSWER_RELEVANCY_PROMPT,
                               CONTEXT_PRECISION_PROMPT, CONTEXT_RECALL_PROMPT,
                               FAITHFULNESS_STATEMENTS_PROMPT, FAITHFULNESS_VERDICTS_PROMPT,
                               JUDGE_SYSTEM, render)

CONTEXT_SEPARATOR = "\n\n"


def _numbered(items: list[str]) -> str:
    return "\n".join(f"{i}. {t}" for i, t in enumerate(items, 1))


def build_j1(cell) -> list[dict]:
    """Every J1 request for one (track, arm, query) cell.

    `cell` supplies: track, arm, query_id, question, reference, contexts, answers (by answer
    index). Context-level metrics carry answer 0 by construction — the retrieved contexts do
    not vary with the generated answer.
    """
    track, arm, qid = cell["track"], cell["arm"], cell["query_id"]
    joined = CONTEXT_SEPARATOR.join(cell["contexts"])
    sentences = split_reference_sentences(cell["reference"])
    out = []

    # context_precision — one call per retrieved context, sub = its rank position
    for sub, ctx in enumerate(cell["contexts"]):
        out.append({
            "custom_id": custom_id("judge1", track, arm, qid, "context_precision", 0, sub),
            "system": JUDGE_SYSTEM,
            "prompt": render(CONTEXT_PRECISION_PROMPT, question=cell["question"],
                             reference=cell["reference"], context=ctx)})

    # context_recall — one call over the whole context
    out.append({
        "custom_id": custom_id("judge1", track, arm, qid, "context_recall", 0, 0),
        "system": JUDGE_SYSTEM,
        "prompt": render(CONTEXT_RECALL_PROMPT, question=cell["question"], context=joined,
                         sentences=_numbered(sentences))})

    # answer-level metrics — once per generated answer
    for a, answer in sorted(cell["answers"].items()):
        out.append({
            "custom_id": custom_id("judge1", track, arm, qid, "faithfulness", a, 0),
            "system": JUDGE_SYSTEM,
            "prompt": render(FAITHFULNESS_STATEMENTS_PROMPT, question=cell["question"],
                             answer=answer)})
        for sub in range(3):        # answer_relevancy strictness, frozen at Gate 0
            out.append({
                "custom_id": custom_id("judge1", track, arm, qid, "answer_relevancy", a, sub),
                "system": JUDGE_SYSTEM,
                "prompt": render(ANSWER_RELEVANCY_PROMPT, answer=answer)})
        out.append({
            "custom_id": custom_id("judge1", track, arm, qid, "answer_correctness", a, 0),
            "system": JUDGE_SYSTEM,
            "prompt": render(ANSWER_CORRECTNESS_PROMPT, question=cell["question"],
                             answer=answer, reference=cell["reference"])})
    return out


def statements_from_reply(reply: str) -> list[str]:
    """Read a statement list out of a J1 extraction reply. Parsing, not scoring.

    An unparseable reply raises rather than defaulting to an empty list: an empty list would
    silently become `faithfulness = 1.0` for that answer, which is a number this module is not
    permitted to invent and the scorer would have no way to distinguish from a real abstention.
    """
    obj = parse_json_object(reply)
    if "statements" not in obj or not isinstance(obj["statements"], list):
        from v18.instruments import JudgeReplyError
        raise JudgeReplyError(f"faithfulness extraction has no statement list: {reply!r}")
    return [str(x) for x in obj["statements"]]


def build_j2(cell, extraction_replies: dict[int, str]) -> list[dict]:
    """Every J2 request for one cell: faithfulness verdicts, one call per generated answer.

    `extraction_replies` maps answer index -> the J1 reply for that answer. This is the read the
    conduct clause permits, and it goes no further than the statement list.
    """
    track, arm, qid = cell["track"], cell["arm"], cell["query_id"]
    joined = CONTEXT_SEPARATOR.join(cell["contexts"])
    out = []
    for a in sorted(extraction_replies):
        statements = statements_from_reply(extraction_replies[a])
        # A claimless answer still needs a verdict call, so the row exists and the scorer sees
        # an explicit empty statement list rather than a missing row.
        listed = statements or ["(the answer makes no factual claim)"]
        out.append({
            "custom_id": custom_id("judge2", track, arm, qid, "faithfulness", a, 0),
            "system": JUDGE_SYSTEM,
            "prompt": render(FAITHFULNESS_VERDICTS_PROMPT, context=joined,
                             statements=_numbered(listed))})
    return out
