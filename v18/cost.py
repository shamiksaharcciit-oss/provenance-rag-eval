"""v1.8 §6 — the cost projection, derived from the prompts rather than written down beside them.

§6 requires, before any test-set call: exact call counts per stage, the probe results, and the
projected total; and it makes a projection over 25,000 end-to-end calls a STOP at Gate 0.

The projection is computed from `judge_prompts.CALLS_PER_QUERY_ARM` and the measured corpus
sizes, so it cannot drift from the prompts the way a hand-maintained total would. Both
determinism branches are projected, because §2 declares the median fallback *now* and a
projection that costs only the happy branch would understate the design the ruling is being
asked to approve.

Nothing here spends anything. It counts.
"""
from __future__ import annotations

from v18.judge_prompts import ANSWER_RELEVANCY_STRICTNESS, CALLS_PER_QUERY_ARM

#: §6 — the spend gate, in end-to-end LLM calls.
CALL_GATE = 25_000

#: §2 — the determinism probe: 20 dev queries, 3 repeats. Applied to generation and to the
#: judge calls those generations feed, across all three arms, so the probe covers the pipeline
#: actually under test rather than one stage of it.
PROBE_QUERIES = 20
PROBE_REPEATS = 3

#: §2 — the fallback multiplier if the probe is not byte-identical.
MEDIAN_RUNS = 3


def judge_calls_per_query_arm(strictness: int = ANSWER_RELEVANCY_STRICTNESS) -> int:
    """Judge calls for one (query, arm), summed over the five metrics."""
    counts = dict(CALLS_PER_QUERY_ARM)
    counts["answer_relevancy"] = strictness
    return sum(counts.values())


#: Published `claude-sonnet-5` rates, USD per million tokens. The introductory rate runs
#: through 2026-08-31 and therefore covers this experiment's window; both are reported so a
#: ruling that delays the run past that date can read the standard figure without recomputing.
USD_PER_MTOK = {"intro_to_2026_08_31": (2.00, 10.00), "standard": (3.00, 15.00)}

#: `count_tokens` is a regex word/punct counter, not the model's tokenizer. English BPE runs
#: above the word count; 1.3 is the multiplier used here and is DECLARED, not measured — the
#: honest way to tighten it is `messages.count_tokens` against the pinned model, which costs a
#: call and therefore waits for the ruling. Every USD figure below inherits this assumption.
WORD_TO_BPE = 1.3

#: Mean generated-answer length, tokens. Extractive answers against short gold spans; declared.
ANSWER_TOKENS = 100
#: Mean judge reply length, tokens. One line of JSON.
JUDGE_REPLY_TOKENS = 30
#: Per (query, arm), judge prompts carry roughly three passes over the retrieved context:
#: context_precision's K per-unit calls (~one package in total), context_recall's whole context,
#: and faithfulness's verdict call. The answer-only calls are negligible beside these.
CONTEXT_PASSES_PER_QUERY_ARM = 3


def estimate_usd(package_tokens_by_track_arm: dict[str, dict[str, float]],
                 n_by_track: dict[str, int], projection: dict) -> dict:
    """USD estimate from MEASURED package sizes. Secondary to the call-count gate (§6).

    §6's gate is denominated in calls, and those are exact. This is an estimate carrying the
    declared assumptions above, and it is reported as one — but it is worth computing, because
    the harness's own cost guard is denominated in dollars and the projection has to be checked
    against it before a run rather than discovered mid-run.
    """
    gen_words = judge_words = 0.0
    for track, per_arm in package_tokens_by_track_arm.items():
        n = n_by_track[track]
        per_query_all_arms = sum(per_arm.values())
        gen_words += per_query_all_arms * n
        judge_words += CONTEXT_PASSES_PER_QUERY_ARM * per_query_all_arms * n

    probe_share = projection["stages"]["probe_total_dev"] / (
        projection["stages"]["generation_test_set"] + projection["stages"]["judging_test_set"])

    def _usd(in_tok: float, out_tok: float, rates: tuple[float, float]) -> float:
        return in_tok / 1e6 * rates[0] + out_tok / 1e6 * rates[1]

    out = {"assumptions": {"word_to_bpe": WORD_TO_BPE, "answer_tokens": ANSWER_TOKENS,
                           "judge_reply_tokens": JUDGE_REPLY_TOKENS,
                           "context_passes_per_query_arm": CONTEXT_PASSES_PER_QUERY_ARM,
                           "_note": "declared, not measured; see estimate_usd docstring"}}

    for branch, test_multiplier in (("branch_single_run", 1), ("branch_median_x3", MEDIAN_RUNS)):
        in_tok = (gen_words + judge_words) * WORD_TO_BPE * test_multiplier
        in_tok += (gen_words + judge_words) * WORD_TO_BPE * probe_share      # dev probe, run once
        out_tok = (projection["stages"]["generation_test_set"] * test_multiplier * ANSWER_TOKENS
                   + projection["stages"]["judging_test_set"] * test_multiplier
                   * JUDGE_REPLY_TOKENS
                   + projection["stages"]["probe_generation_dev"] * ANSWER_TOKENS
                   + projection["stages"]["probe_judging_dev"] * JUDGE_REPLY_TOKENS)
        row = {"input_tokens_est": round(in_tok), "output_tokens_est": round(out_tok)}
        for label, rates in USD_PER_MTOK.items():
            row[f"usd_{label}"] = round(_usd(in_tok, out_tok, rates), 2)
        # The harness guard prices every provider at Opus rates ($5/$25) — see
        # src/llm/client.py `_USD_PER_INPUT_TOKEN`. It aborts on `est_usd > max_usd`, so the
        # figure that decides whether a run survives is this one, not the Sonnet figure.
        row["usd_as_the_harness_guard_computes_it"] = round(_usd(in_tok, out_tok, (5.0, 25.0)), 2)
        out[branch] = row
    return out


def project(n_by_track: dict[str, int], n_arms: int,
            strictness: int = ANSWER_RELEVANCY_STRICTNESS) -> dict:
    """Full projection for both determinism branches.

    `n_by_track` is the measured test-set size per track, not a number copied from the plan —
    the runner passes what the loader actually returned.
    """
    n_total = sum(n_by_track.values())
    per_qa = judge_calls_per_query_arm(strictness)

    generation = n_total * n_arms
    judging = n_total * n_arms * per_qa

    probe_generation = PROBE_QUERIES * n_arms * PROBE_REPEATS
    probe_judging = PROBE_QUERIES * n_arms * per_qa * PROBE_REPEATS
    probe = probe_generation + probe_judging

    single = generation + judging + probe
    median = MEDIAN_RUNS * (generation + judging) + probe

    return {
        "corpus": {**n_by_track, "n_total": n_total, "n_arms": n_arms},
        "judge_calls_per_query_arm": per_qa,
        "judge_calls_breakdown": {**CALLS_PER_QUERY_ARM, "answer_relevancy": strictness},
        "stages": {
            "generation_test_set": generation,
            "judging_test_set": judging,
            "probe_generation_dev": probe_generation,
            "probe_judging_dev": probe_judging,
            "probe_total_dev": probe,
        },
        "branch_single_run": {
            "total_calls": single,
            "gate": CALL_GATE,
            "within_gate": single <= CALL_GATE,
        },
        "branch_median_x3": {
            "total_calls": median,
            "gate": CALL_GATE,
            "within_gate": median <= CALL_GATE,
            "_note": ("§2's declared fallback if the probe is not byte-identical; the multiplier "
                      "applies to the test set only, the dev probe having already run"),
        },
    }
