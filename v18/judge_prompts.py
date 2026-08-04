"""v1.8 I1 — the exact prompts the judge receives (plan §3: "part of the freeze").

RAGAS is not installed in this environment, and §3's implementation rule therefore selects its
second branch: implement the published formulas directly. The reason not to install it is not
convenience. `ragas` pulls a langchain adapter stack into an environment whose pins
(torch 2.13, transformers 5.14, numpy 2.2) are the ones under which v1.6's and v1.7's
recall@budget reproduction checks pass. Perturbing that environment to obtain a metric library
would put the apparatus those checks defend at risk for no measurement gain — the formulas are
public and short. The decision is recorded here rather than left implicit, and §3's own
sentence governs either way: **the metric code frozen at Gate 0 is canonical over any library
documentation.**

Each prompt asks for JSON on one line and nothing else. That is a parsing decision, not a
metric decision: a judge that free-forms its rationale makes the *parser* a second free
parameter, and the parser would then be settled after seeing outputs. `parse_json_object` in
`instruments.py` is strict for the same reason — an unparseable judge reply raises rather than
defaulting, because a default is a value invented by the harness and attributed to the judge.

The five metrics and their published shapes (RAGAS v0.1/0.2 formulations):

  context_precision   per-context usefulness verdicts -> average precision over rank order
  context_recall      reference split into sentences -> attributable-to-context fraction
  faithfulness        answer -> statements -> supported-by-context fraction
  answer_relevancy    answer -> N reverse-engineered questions -> cosine sim to the real one
  answer_correctness  answer vs reference -> TP/FP/FN -> F1, blended with semantic similarity

Call counts per (query, arm) are fixed by these prompts and are what §6's projection counts:
context_precision K=5, context_recall 1, faithfulness 2, answer_relevancy 3, answer_correctness 1
= 12. `cost.py` derives the projection from these constants rather than from a written-down
total, so the projection cannot drift from the prompts.
"""
from __future__ import annotations

#: §3 — the judge model, pinned. Recorded into the manifest at run time, never inherited.
JUDGE_MODEL = "claude-sonnet-5"

#: Answer-relevancy strictness: how many questions are reverse-engineered per answer.
#: RAGAS's published default is 3, issued as 3 independent generations. Kept at the published
#: value; a 1-call variant would save 2 calls per (query, arm) and is costed in `cost.py` as a
#: declared alternative for the ruling, not taken by the agent's discretion (§10).
ANSWER_RELEVANCY_STRICTNESS = 3

#: Fixed retrieval depth for I1's context metrics — the field-standard frame under study (§1).
FIXED_K = 5

JUDGE_SYSTEM = (
    "You are a strict evaluation judge. You reply with one line of JSON and nothing else: no "
    "prose, no markdown fence, no explanation outside the JSON."
)

# --------------------------------------------------------------------------- context precision

CONTEXT_PRECISION_PROMPT = (
    "Given a question, a reference answer, and one retrieved context, decide whether that "
    "context was useful in arriving at the reference answer.\n"
    "\n"
    "Question: {question}\n"
    "Reference answer: {reference}\n"
    "Context: {context}\n"
    "\n"
    'Reply exactly: {"verdict": 1} if it was useful, or {"verdict": 0} if it was not.\n'
)

# ------------------------------------------------------------------------------ context recall

CONTEXT_RECALL_PROMPT = (
    "Given a question, a retrieved context, and a reference answer split into numbered "
    "sentences, decide for each sentence whether it can be attributed to the context.\n"
    "\n"
    "Question: {question}\n"
    "Context: {context}\n"
    "Reference sentences:\n{sentences}\n"
    "\n"
    'Reply exactly: {"verdicts": [1, 0, ...]} with one 1 (attributable) or 0 (not '
    "attributable) per sentence, in the order given.\n"
)

# -------------------------------------------------------------------------------- faithfulness

FAITHFULNESS_STATEMENTS_PROMPT = (
    "Break the answer into its simplest standalone factual statements. Do not add, infer or "
    "omit information.\n"
    "\n"
    "Question: {question}\n"
    "Answer: {answer}\n"
    "\n"
    'Reply exactly: {"statements": ["...", "..."]}. If the answer makes no factual claim, '
    'reply exactly: {"statements": []}.\n'
)

FAITHFULNESS_VERDICTS_PROMPT = (
    "Given a context and a list of numbered statements, decide for each statement whether it "
    "can be directly inferred from the context.\n"
    "\n"
    "Context: {context}\n"
    "Statements:\n{statements}\n"
    "\n"
    'Reply exactly: {"verdicts": [1, 0, ...]} with one 1 (inferable) or 0 (not inferable) per '
    "statement, in the order given.\n"
)

# --------------------------------------------------------------------------- answer relevancy

ANSWER_RELEVANCY_PROMPT = (
    "Given an answer, write the single question that this answer most directly answers. Write "
    "only the question.\n"
    "\n"
    "Answer: {answer}\n"
    "\n"
    'Reply exactly: {"question": "..."}\n'
)

# ------------------------------------------------------------------------- answer correctness

ANSWER_CORRECTNESS_PROMPT = (
    "Compare a candidate answer with a reference answer by classifying statements.\n"
    "\n"
    "Question: {question}\n"
    "Candidate answer: {answer}\n"
    "Reference answer: {reference}\n"
    "\n"
    "TP = statements present in the candidate and supported by the reference.\n"
    "FP = statements present in the candidate but not supported by the reference.\n"
    "FN = statements present in the reference but missing from the candidate.\n"
    "\n"
    'Reply exactly: {"TP": <int>, "FP": <int>, "FN": <int>}\n'
)

#: Weights for answer_correctness = w_f1 * statement-F1 + w_sim * semantic similarity.
#: RAGAS's published default is [0.75, 0.25]. Frozen here; the similarity term uses the local
#: MiniLM encoder, so it costs nothing and involves no judge.
ANSWER_CORRECTNESS_WEIGHTS = (0.75, 0.25)

#: Every prompt in one mapping, so the snapshot test iterates the real objects rather than a
#: hand-maintained list that could fall out of step with the module (identity over assertion).
ALL_PROMPTS = {
    "context_precision": CONTEXT_PRECISION_PROMPT,
    "context_recall": CONTEXT_RECALL_PROMPT,
    "faithfulness_statements": FAITHFULNESS_STATEMENTS_PROMPT,
    "faithfulness_verdicts": FAITHFULNESS_VERDICTS_PROMPT,
    "answer_relevancy": ANSWER_RELEVANCY_PROMPT,
    "answer_correctness": ANSWER_CORRECTNESS_PROMPT,
}

#: Judge calls per (query, arm), derived from the prompts above. §6's projection reads this.
CALLS_PER_QUERY_ARM = {
    "context_precision": FIXED_K,
    "context_recall": 1,
    "faithfulness": 2,
    "answer_relevancy": ANSWER_RELEVANCY_STRICTNESS,
    "answer_correctness": 1,
}


def render(template: str, **fields: str) -> str:
    """Fill a prompt without `str.format`.

    Same reason as v1.7's `render_prompt`: context and answer text contain braces, and
    `str.format` would either raise on them or silently interpolate. Replacement is literal.
    """
    out = template
    for key, value in fields.items():
        out = out.replace("{" + key + "}", value)
    return out
