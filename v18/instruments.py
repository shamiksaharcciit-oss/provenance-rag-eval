"""v1.8 — the three instruments (plan §3), and the composites `F_BIAS` is defined over (§4).

The design principle here is that **no metric function calls a model.** Every scorer in this
module is a pure function of already-collected judge replies (I1) or of text (I2). That is what
makes the whole of I1 testable at Gate 0 with zero spend: the judge is an input, not a
dependency. `runner.py` is the only place that would issue a call, and it does not run before a
Gate 0 ruling.

I2 is imported, never re-implemented. `token_f1` and `normalise` come from `src.v17.reading`,
canonical at `e19dd35` — §3's "by citation" made true by construction. A transcribed copy would
be a second procedure for one quantity (A5b) and would drift the moment either file was touched;
it would also quietly relocate the freeze, since the v18 copy would not be the frozen object.

I3 contributes no function. It is v1.6's published record, quoted with commit hashes and never
recomputed (§3), so there is deliberately nothing here to compute it with.
"""
from __future__ import annotations

import json
import re

# I2, by citation — canonical at e19dd35. Do not shadow, wrap or "improve" these.
from src.v17.reading import normalise, token_f1  # noqa: F401  (re-exported by intent)
from src.textutil import sentence_spans
from v18.judge_prompts import ANSWER_CORRECTNESS_WEIGHTS

# --------------------------------------------------------------------------------- parsing


class JudgeReplyError(ValueError):
    """A judge reply that could not be parsed as the prompt demanded.

    Raised rather than defaulted. A default here would be a number invented by the harness and
    then reported as the judge's opinion, which is the same failure as a fallback that replaces
    a legitimate zero (v1.7 Gate 0, F5) — only worse, because it would be attributed to a model.
    """


def _trailing_object(text: str) -> tuple[str, str]:
    """Return `(prefix, candidate)` where `candidate` is the last balanced `{...}` region.

    Scans backwards from the final `}` to its matching `{`, so a JSON object containing nested
    braces is recovered whole. Raises if no balanced region exists.
    """
    end = text.rfind("}")
    if end == -1:
        raise JudgeReplyError(f"no JSON object in reply: {text!r}")
    depth = 0
    for i in range(end, -1, -1):
        if text[i] == "}":
            depth += 1
        elif text[i] == "{":
            depth -= 1
            if depth == 0:
                return text[:i], text[i:end + 1]
    raise JudgeReplyError(f"unbalanced braces in reply: {text!r}")


def parse_json_object(reply: str, expected_keys=None) -> dict:
    """Accept exactly one trailing, complete, well-formed JSON object (PF-16).

    **Amended post-freeze by ruling** — `Decisions_v18_G15_2026-08-01.md` §1 — after 101 of
    15,960 judge replies (0.63%) came back as prose reasoning followed by valid JSON, in
    violation of the prompt's "one line of JSON and nothing else". The rule is total, uniform
    and content-blind: it applies identically to all 15,960 replies and conditions on nothing
    about their verdicts.

    **On a conforming reply the trailing object IS the reply**, so this is the identity there;
    `test_v18_instruments.py` pins that against the pre-amendment behaviour, and no
    already-parseable cell can change value.

    Everything the original strictness protected survives beneath the rule. What "no repair, no
    regex scavenging" was for was stopping the scorer *constructing* a verdict out of ambiguous
    material — and this constructs nothing. It still refuses hard on:

      * no trailing object at all,
      * more than one candidate trailing object (genuine ambiguity),
      * malformed JSON,
      * a key shape that is not the one the call expects.

    Taking the judge's final object as the judge's answer is faithful to what the metric means.
    Refusing it because the judge also thought out loud would convert an instruction violation
    by the judge into data loss for the experiment.
    """
    text = reply.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()

    try:
        obj = json.loads(text)                      # conforming reply: the identity path
    except json.JSONDecodeError:
        prefix, candidate = _trailing_object(text)
        if prefix.rstrip().endswith("}"):
            raise JudgeReplyError(
                f"two candidate trailing objects; ambiguous, refusing: {reply!r}") from None
        try:
            obj = json.loads(candidate)
        except json.JSONDecodeError as e:
            raise JudgeReplyError(f"not JSON: {reply!r}") from e

    if not isinstance(obj, dict):
        raise JudgeReplyError(f"JSON but not an object: {reply!r}")
    if expected_keys is not None and set(obj) != set(expected_keys):
        raise JudgeReplyError(
            f"key shape {sorted(obj)} is not the expected {sorted(expected_keys)}: {reply!r}")
    return obj


def _verdict_list(reply: str, key: str, expected: int) -> list[int]:
    obj = parse_json_object(reply)
    if key not in obj:
        raise JudgeReplyError(f"missing {key!r} in {reply!r}")
    raw = obj[key]
    if not isinstance(raw, list):
        raise JudgeReplyError(f"{key!r} is not a list in {reply!r}")
    if len(raw) != expected:
        raise JudgeReplyError(f"{key!r} has {len(raw)} verdicts, expected {expected}")
    out = []
    for v in raw:
        if v not in (0, 1, True, False):
            raise JudgeReplyError(f"non-binary verdict {v!r} in {reply!r}")
        out.append(int(v))
    return out


# ------------------------------------------------------------------------- I1: the five metrics


def context_precision(verdicts: list[int]) -> float:
    """Average precision over the ranked contexts (RAGAS's published formulation).

        CP@K = sum_k (Precision@k * v_k) / (number of relevant items in the top K)

    Rank order matters and is the point: a useful context at rank 1 scores higher than the same
    context at rank 5. With no relevant context the metric is 0.0 — a genuine zero, not a
    missing value, because "nothing useful was retrieved" is an outcome the metric can express.
    """
    if not verdicts:
        return 0.0
    total_relevant = sum(verdicts)
    if total_relevant == 0:
        return 0.0
    running, acc = 0, 0.0
    for k, v in enumerate(verdicts, start=1):
        running += v
        if v:
            acc += (running / k)
    return acc / total_relevant


def context_recall(verdicts: list[int]) -> float:
    """Fraction of reference sentences attributable to the retrieved context."""
    if not verdicts:
        return 0.0
    return sum(verdicts) / len(verdicts)


def faithfulness(verdicts: list[int]) -> float:
    """Fraction of the answer's statements that are inferable from the context.

    An answer that makes no factual claim yields no statements. RAGAS returns NaN there; this
    implementation returns 1.0 and records the empty case separately, because a NaN propagating
    into a paired contrast silently drops the query from one arm and breaks the pairing that
    every statistic in this programme depends on. The count of empty-statement answers is
    reported descriptively per arm so the substitution is visible rather than buried.
    """
    if not verdicts:
        return 1.0
    return sum(verdicts) / len(verdicts)


def answer_relevancy(similarities: list[float]) -> float:
    """Mean cosine similarity between reverse-engineered questions and the real question.

    Similarities are computed by the local encoder in `runner.py` and passed in; no judge and no
    network is involved at this point. Clamped to [0, 1]: cosine on normalised embeddings can
    return a small negative, and a negative relevancy is not a quantity the published metric
    defines.
    """
    if not similarities:
        return 0.0
    return max(0.0, min(1.0, sum(similarities) / len(similarities)))


def statement_f1(tp: int, fp: int, fn: int) -> float:
    """TP / (TP + 0.5 * (FP + FN)) — the published answer-correctness F1 term."""
    denom = tp + 0.5 * (fp + fn)
    if denom <= 0:
        return 0.0
    return tp / denom


def answer_correctness(tp: int, fp: int, fn: int, similarity: float,
                       weights: tuple[float, float] = ANSWER_CORRECTNESS_WEIGHTS) -> float:
    """Weighted blend of statement F1 and semantic similarity (published default 0.75/0.25)."""
    w_f1, w_sim = weights
    return w_f1 * statement_f1(tp, fp, fn) + w_sim * max(0.0, min(1.0, similarity))


def split_reference_sentences(reference: str) -> list[str]:
    """Split the gold text into sentences for context_recall.

    Uses the harness's own `sentence_spans` rather than a new splitter, so that "sentence" means
    the same thing here as everywhere else in the programme. A reference with no detectable
    sentence boundary is returned whole rather than as an empty list, so the metric always has
    at least one unit to judge.
    """
    spans = sentence_spans(reference)
    out = [reference[a:b].strip() for a, b in spans]
    out = [s for s in out if s]
    return out or ([reference.strip()] if reference.strip() else [])


# ---------------------------------------------------------------------------------- composites
#
# §4 requires the *direction* of the per-query composites to be declared in the frozen code.
# These two functions are that declaration.

#: The context-level members of I1. B2 is defined over their composite (§4).
CONTEXT_METRICS = ("context_precision", "context_recall")

#: The answer-level members of I1. B1's judge side is defined over their composite (§4).
ANSWER_METRICS = ("faithfulness", "answer_relevancy", "answer_correctness")


def context_composite(scores: dict[str, float]) -> float:
    """Unweighted mean of the context-level metrics. Higher is better."""
    return sum(scores[m] for m in CONTEXT_METRICS) / len(CONTEXT_METRICS)


def answer_composite(scores: dict[str, float]) -> float:
    """Unweighted mean of the answer-level metrics. Higher is better.

    Unweighted because any weighting would be a free parameter with no principled setting, and
    an unprincipled weighting chosen at Gate 0 is still a weighting chosen by the agent. All
    three members are already on [0, 1] and share a direction, so the mean is well defined.
    """
    return sum(scores[m] for m in ANSWER_METRICS) / len(ANSWER_METRICS)


def preference(treatment: float, control: float) -> int:
    """Direction indicator in {-1, 0, +1}: +1 iff `treatment` scores strictly higher.

    This is the sign convention the whole of B1 rests on, so it is one function used by both
    sides of the subtraction rather than two comparisons written out twice. Exact float equality
    is the tie test on purpose: both sides are computed from the same arithmetic on the same
    scales, and an epsilon band would be a threshold chosen without a procedure.
    """
    if treatment > control:
        return 1
    if treatment < control:
        return -1
    return 0
