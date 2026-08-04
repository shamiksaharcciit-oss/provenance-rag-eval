# Experiment Plan Amendment v1.3 — Reranker axis (M6)

**Owner:** Shamik Saha · **Date:** 25 July 2026 · **Amends:** v1.1 (base plan), unaffected by v1.2.
**Status at time of writing:** pre-registered. No reranked run has been executed.

---

## 1. Purpose

Add a reranking stage to the retrieval pipeline and measure whether it improves retrieval
**independently of the formatter condition**. First item on the retrieval-stack roadmap
recorded in `note_formatter_improvements.md`: *"Reranker first (cheap, both tracks) →
small-to-big/parent-child → query decomposition → document routing."*

Chosen now because it has no dependency on any open formatter question. Track C is blocked on
two open design items from the v1.2 REJECT (the term-drift regression, and a redesigned
identity rule), so running it would produce a REJECT for a design reason, not an
infrastructure one. The suggestion-mode feedback loop needs Forge diff-panel instrumentation
that does not exist.

## 2. What changes, and what does not

**Added.** A cross-encoder reranking stage between first-stage retrieval and the top-k cut.

**Explicitly unchanged.** Chunking, all conditions C0–C5 and the C3-* ablations, prompts
(`eval-run-20260724-135411`), the embedding model, the scoring rule, the dev/test splits, the
statistics machinery. With `rerank.enabled: false` — the default — every pre-v1.3 number
reproduces exactly, because the reranked ranking is an *added* key alongside `dense` and
`hybrid` rather than a replacement for either.

**Not a new condition.** The reranker is an **orthogonal axis**, not "C6". Mixing it into the
condition list would confound a query-side change with corpus-side ones and make the
composition story unreadable. Every condition is scored twice — with and without reranking —
from the *same* retrieval call on the *same* queries, so all comparisons are paired.

## 3. Design

- **Backend:** cross-encoder, `cross-encoder/ms-marco-MiniLM-L-6-v2`, pinned by revision and
  recorded into `results.json` alongside the embedding model (§11).
- **What is reranked:** the fused (RRF hybrid) **candidate pool**, `index.candidate_pool = 50`,
  reordered, *then* cut to top-k.
  This is load-bearing. Reranking only the top-k could never change recall@k, since no unit
  below the cut could enter it. Reranking the pool is what makes the metric able to move.
- **Ties:** stable sort, so candidates the model cannot separate retain their fused order
  rather than being shuffled arbitrarily.
- **Ranking key:** `hybrid_rerank`, sitting beside `dense` and `hybrid` in `metrics`.

### Invariants — confirmed, not assumed
1. **Provenance survives.** A reranker may only *permute*. `assert_permutation` runs in-band on
   every call and raises `ProvenanceViolation` on any change to the unit set, its text, or its
   `source_ranges`. Hits are scored against original document character ranges (§6), so a
   reranker that rewrote a unit would silently invalidate every metric.
2. **Reranking reorders, it does not resize.** No `Unit` is constructed, so unit token
   statistics and the v1.1 common-size control are untouched. `tests/test_rerank.py` asserts
   `compute_chunk_stats` is invariant under reranking rather than taking it on trust.
3. **Off is a true no-op.** Verified by the `noop` backend test and by a full Track A smoke run
   with the axis disabled.

## 4. Pre-registered hypotheses

**H6 (main effect).** Adding the reranker improves recall@5 (hybrid, `any` overlap variant)
relative to the same condition without it, independent of formatter condition.
Per condition X: `X+rerank` vs `X`, paired over queries.

**H6a (interaction — the question that matters).** Does the reranker's gain *stack* with the
formatter's, or does it close some of the same gap?
Difference-in-differences: `(C3+rerank − C3) − (C0+rerank − C0)`.

- DiD ≈ 0 → additive; the two fixes are **complements**.
- DiD significantly < 0 → sub-additive; the reranker closes part of the same gap the formatter
  closes — they are **substitutes**.
- DiD significantly > 0 → super-additive.

**Reported either way.** A negative DiD is a *useful* result for the composition story already
in the white paper — that some fixes are substitutes, not complements — and must not be
suppressed in favour of whichever direction looks better for the formatter.

**H6b (secondary).** Does reranking alone reach what the formatter buys? `C0+rerank` vs `C3`.
A cheap query-side fix matching a corpus-side one is directly relevant to the composition
argument. Descriptive; carries no pass/fail weight.

## 5. Metrics and statistics

- **Primary metric:** recall@5, hybrid ranking, `any` overlap variant — same primary as v1.1.
- **Secondary, reported:** recall@{1,3,10}, nDCG@k, MRR; strict-containment variant.
- **Tests:** paired bootstrap (10k iters) for the mean difference and 95% CI; paired
  permutation test (10k) for p; Holm correction.
- **Holm families.** H6 main-effect comparisons are corrected as **their own family**, separate
  from the v1.1 H1–H4 pairwise family. They test a different hypothesis, and folding them
  together would retroactively alter the significance of already-published v1.1 results.
- **Tracks:** A and B. Same dev/test splits as v1.1. No new corpus.

## 6. Pass / kill criteria (frozen)

| Verdict | Condition |
|---|---|
| **ADOPT** | H6 significant (paired CI excludes 0 after Holm) on **both** Track A and Track B for the primary metric, on at least the C0 and C3 conditions |
| **ADOPT_SCOPED** | H6 significant on one track only, or on a subset of conditions — report exactly which, and treat the scope as the finding |
| **KILL** | The reranker's gain is not statistically distinguishable from zero on Track A **and** Track B |

**Kill means stop.** If the gain is indistinguishable from zero on the corpora that already
exist, the reranker is not adopted and **no third corpus is sought to chase significance**.
That would repeat precisely the error the one-shot rule exists to prevent, transplanted from
identity injection to a new feature. A null here is a result, and it is reported as one.

**No iterating on a spent decision.** If H6 fails, changing the reranker model or pool size and
re-testing on the same Track A/B test split is not a fresh test. Any retry needs a
pre-registered amendment stating what changed and why, exactly as v1.2 required.

## 7. Cost

No LLM calls — the cross-encoder is a local CPU model. Cost is wall-clock only:
50 candidates × (220 + 150) queries × ~11 conditions ≈ 200k pairs per full two-track run.

## 8. What this does not test

- Rerankers other than the pinned cross-encoder; no model sweep is pre-registered.
- Pool sizes other than 50. The pool is inherited from `index.candidate_pool` so the
  first-stage candidate set is identical with and without reranking.
- Track C (blocked on v1.2's open design items) and any generation-side effect —
  this is a retrieval-metric amendment only.
- Latency as a decision input. It is recorded, not scored.
