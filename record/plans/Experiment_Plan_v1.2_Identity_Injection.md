# Experiment Plan v1.2 — Document-Identity Injection

**Owner:** Shamik Saha · **Version:** 1.2 · **Date:** July 2026
**Builds on:** v1.1 (`run-20260724-135411`, verdict PARTIAL). Reuses the harness, corpus, models, seed conventions.
**Audience:** the coding agent in `rag-formatter-eval/`.
**Single question under test:** does adding *document-identity injection* to the formatter significantly improve retrieval on multi-document corpora — judged on data the idea has never seen?

---

## 0. Critical context — why this run has extra fairness rules

The identity-injection idea was **derived by mining Track B's failures** (the 50/150 universal misses that retrieved the wrong document). Track B's existing 150 queries are therefore **contaminated as evidence** — validating on them would be test-set leakage. This plan treats the old split as a labeled development set and decides ONLY on a fresh, held-out split. Do not weaken this.

## 1. The formatter change (the only behavior change in this run)

Add one operation to the pass, `identity_injection`, applied per section during formatting:

- **What it does:** where a section's subject is implicit, make the document's identity explicit in the section's opening — e.g., "The retry policy is 3 attempts" → "**The Marlin planner's** retry policy is 3 attempts." Extends reference resolution from pronoun level to document level.
- **Identity source constraint (guardrail extension):** the injected identity phrase must be **drawn verbatim from the document itself** — its title, or an entity named in its headings/first paragraph. The pass may never invent, paraphrase, or infer an identity that does not literally appear there. New automated check: every injected identity token must exist in the source document's title/headings; violations are `blocked`, counted, and reported (target: 0, same standard as preserved-terms).
- **Frequency bound:** at most one identity stamp per section (opening sentence), skipped where the section already names the subject. Over-stamping is the readability risk — see H5c.
- All existing operations, prompts, and the verbatim-vocabulary guardrail remain byte-identical except for the added operation. Version the prompts module: `PROMPTS_VERSION = "v1.2-identity"` (the v1.1 prompts stay frozen under their existing version for the baselines).
- Provenance: injected tokens map to the title/heading range they were drawn from; the section's `source_ranges` are otherwise unchanged.

## 2. Conditions (keep the set minimal)

| ID | Pipeline | Role |
|----|----------|------|
| C0 | original + naive | floor (cache replay) |
| C2 | original + contextual | strong baseline (cache replay) |
| C4 | formatted (v1.1 pass) + naive | incumbent champion (cache replay) |
| **C4i** | **formatted with identity injection + naive** | **treatment** |

C4i vs C4 isolates the new operation exactly — no separate ablation needed. Do not add other conditions; power is precious.

## 3. Data and fairness rules

1. **Track B2 (decision data):** a fresh sample of 150 QASPER queries, drawn with a NEW seed, with an explicit exclusion list of all 150 v1.1 `query_id`s (assert zero overlap in a test). Same corpus documents are fine — only queries were mined. Same gold-mapping procedure.
2. **Query tagging for the subgroup hypothesis:** tag every B2 query `identity_poor` or `identity_rich` — whether the query text contains vocabulary identifying its gold document (title tokens / unique entities; implement as deterministic token overlap between query text and gold doc title+abstract, threshold documented; no LLM judgment, so the tag is reproducible). Tag BEFORE any retrieval runs.
3. **Old B-150:** may be run and reported, permanently labeled `development set (contaminated — improvement derived from its failures)`. It plays no part in the decision.
4. **Track A regression check:** replay A from cache for C0/C2/C4; run C4i on A. Purpose: confirm no regression (C4i within CI of C4). Not a decision input, a safety check.
5. **One-shot rule:** if H5 fails on B2, do NOT iterate the feature and re-test on B2 — B2 is then contaminated too, and any next attempt needs a B3 split. Record this rule in the pre-registration.
6. **Pre-registration v1.2** frozen and hashed BEFORE any B2 metric is computed, containing the hypotheses below, the decision rules of §5, the one-shot rule, and the exclusion-list hash.

## 4. Hypotheses (freeze verbatim)

- **H5 (primary):** C4i recall@5 > C4 on Track B2; paired bootstrap CI excludes 0 after Holm correction over the pairwise family {C4i vs C4, C4i vs C2, C4i vs C0}.
- **H5a (mechanism/subgroup):** the C4i−C4 improvement is concentrated in `identity_poor` queries; effect in `identity_rich` queries is ≈ 0. (This is what distinguishes "the mechanism works as theorized" from "something else moved.")
- **H5b (guardrail):** zero preserved-term failures; zero identity-source violations; hybrid recall tracks dense for C4i (no drift from injected tokens).
- **H5c (readability):** blind readability review on 20 B2 documents, C4i vs original AND C4i vs C4 (three-way): C4i within 0.15 of both on the 1–5 rubric. Repetitive stamping ("The Marlin planner's… The Marlin planner's…") is the failure mode this guards; also report stamps-per-document distribution.
- **Pre-registered expectation:** on Track A (identity-rich synthetic queries), C4i ≈ C4.

## 5. Decision rules (the output exists to trigger exactly one of these)

- **ADOPT:** H5 significant AND H5b clean AND H5c passes → identity injection enters the default pass; update the Confluence CLI/Forge specs' pass definition; becomes part of the next paper revision.
- **ADOPT-SCOPED:** H5 significant only within `identity_poor` subgroup (full-set CI includes 0 but subgroup CI excludes 0, pre-registered test) AND H5b/H5c clean → ship behind a corpus-level flag, on by default for multi-document knowledge bases, documented as such.
- **REJECT:** H5 and subgroup both non-significant, OR any H5b violation > 0 unresolved, OR H5c fails → the operation does not enter the pass; findings archived; any retry requires a redesigned feature and a B3 split.

## 6. Required outputs (the decision bundle)

Return `results_v12/` containing:

1. **`results.json`** — v1.1 schema plus:
   - `"experiment": "v1.2-identity-injection"`, prereg hash, exclusion-list hash, `PROMPTS_VERSION` per condition;
   - per-condition B2 (and A-regression) blocks as before, including dense/hybrid split and fresh/cached cost;
   - `"subgroup"`: recall@5 for C4 and C4i within `identity_poor` (n=…) and `identity_rich` (n=…), each with paired CI on the delta;
   - `"identity_checks"`: {stamps_total, stamps_per_doc_mean/max, source_violations, preserved_term_failures};
   - `"readability3way"`: {original, c4, c4i} means + n;
   - `"verdict"`: {H5, H5a, H5b, H5c, decision: ADOPT | ADOPT_SCOPED | REJECT, notes}.
2. **`per_query.jsonl`** for B2 (same schema, plus the `identity_poor|rich` tag) — enables re-analysis without re-running.
3. **Figures + CSVs:** `b2_recall_by_condition` (with CIs), `subgroup_effect` (C4i−C4 delta in the two subgroups, the headline figure), `stamps_distribution`.
4. **`results.md`** — TL;DR verdict against §5; the four hypothesis outcomes; headline and subgroup tables; guardrail and readability sections; cost; threats (including an explicit statement that the old B-150 was development data); reproduction commands.

The §5 decision must be computable from `results.json` alone — if a human needs to interpret ambiguity to pick ADOPT/REJECT, the run is incomplete.

## 7. Out of scope (do not build in this run)

Damage triage, feedback-loop learning, multi-hop pre-joining, reranker/small-to-big retrieval changes, Track C, any second improvement bundled alongside identity injection. One variable, one verdict.

## 8. Execution order

1. Freeze prereg v1.2 (hypotheses §4, rules §5, one-shot rule, exclusion-list hash).
2. Implement `identity_injection` + identity-source check + tests (blocked-stamp fixtures, provenance mapping, prompt-version separation from v1.1 baselines).
3. Draw B2 with new seed; assert zero overlap; tag identity_poor/rich; commit tags before retrieval.
4. Track A regression (cache replay + C4i).
5. Track B2: all four conditions; stats; readability three-way.
6. Emit decision bundle; fill verdict per §5.

*Everything not specified here inherits v1.1 unchanged: provenance scoring, paired statistics, Holm correction, cost self-checks, idempotency, and the prose rule — no "beats" without a CI that excludes zero.*
