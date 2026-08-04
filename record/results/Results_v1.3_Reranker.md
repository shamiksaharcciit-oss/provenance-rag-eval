# Results — v1.3 Reranker axis (M6)

**Date:** 26 July 2026 · **Pre-registration:** `preregistration_v13.json` (frozen
2026-07-25T19:44Z, before any reranked run; addendum 20:44Z, also pre-unblinding).
**Amendment:** `Experiment_Plan_v1.3_Reranker.md` · **Artifacts:** `results_v13/`

## Verdict: H6 NOT SUPPORTED — do not adopt

Reranking the fused candidate pool with `cross-encoder/ms-marco-MiniLM-L-6-v2` **significantly
degraded** retrieval on Track A (4 of 6 conditions) and had **no detectable effect** on
Track B (0 of 6). The reranker is not adopted.

### The frozen criteria do not cleanly cover this outcome — a protocol defect

| Criterion | Requirement | Met? |
|---|---|---|
| ADOPT | significant positive on **both** tracks | No |
| ADOPT_SCOPED | significant positive on one track / subset | No — every significant effect is negative |
| KILL | gain "not statistically distinguishable from zero on Track A **and** Track B" | **Not literally met** — Track B qualifies, Track A is significantly *negative* |

I wrote criteria for *positive-or-null* and never contemplated *harm*. A significant negative
is not "indistinguishable from zero", so the KILL clause does not strictly apply. The
practical decision is unambiguous — **do not adopt** — but the verdict is recorded as
`REJECT (criteria incomplete)` rather than relabelled KILL to imply the protocol anticipated
this. Any future amendment must specify a harm branch.

## H6 main effect — recall@5 (hybrid, `any`), Holm-corrected within C0–C5

| Track | Cond | base | +rerank | Δ | 95% CI | p(Holm) | |
|---|---|---|---|---|---|---|---|
| A | C0 | 0.790 | 0.688 | −0.1023 | [−0.171, −0.034] | 0.019 | **harm** |
| A | C1 | 0.540 | 0.494 | −0.0455 | [−0.108, +0.017] | 0.392 | n.s. |
| A | C2 | 0.852 | 0.648 | −0.2045 | [−0.267, −0.142] | 0.0006 | **harm** |
| A | C3 | 0.773 | 0.744 | −0.0284 | [−0.085, +0.028] | 0.442 | n.s. |
| A | C4 | 0.835 | 0.744 | −0.0909 | [−0.148, −0.040] | 0.007 | **harm** |
| A | C5 | 0.852 | 0.631 | −0.2216 | [−0.290, −0.159] | 0.0006 | **harm** |
| B | C0 | 0.353 | 0.393 | +0.0400 | [−0.013, +0.093] | 1.000 | n.s. |
| B | C1 | 0.360 | 0.400 | +0.0400 | [−0.027, +0.107] | 1.000 | n.s. |
| B | C2 | 0.387 | 0.347 | −0.0400 | [−0.100, +0.020] | 1.000 | n.s. |
| B | C3 | 0.380 | 0.393 | +0.0133 | [−0.040, +0.067] | 1.000 | n.s. |
| B | C4 | 0.400 | 0.420 | +0.0200 | [−0.033, +0.073] | 1.000 | n.s. |
| B | C5 | 0.393 | 0.407 | +0.0133 | [−0.047, +0.073] | 1.000 | n.s. |

Track A n=176, Track B n=150; paired bootstrap and permutation, 10k iterations each.
The apparent +0.040 gains on Track B are ~6 queries and do not survive testing.

## H6a interaction

**Track A: DiD = +0.0739, CI [+0.006, +0.142], p=0.045 — significant.** The formatter reduces
the reranker's harm: C0 loses 0.102 while C3 loses only 0.028 and is not distinguishable from
zero. **Track B: DiD = −0.0267, n.s.**

Treat with caution: p=0.045 with a lower bound of +0.006 is marginal, it is a single
uncorrected test, and it replicates on neither track. Suggestive, not established.

H6b (`C0+rerank` vs `C3`) is reported in `results_v13/results.json`; it carries no decision
weight.

## Diagnosis

### 1. A configuration defect I introduced — severe, but NOT the cause

The amendment set `max_length: 512` while conditions index units targeted at 768 tokens.
Measured (`scripts/diagnose_rerank_truncation.py`):

| Track | % units truncated | % of indexed text the cross-encoder never saw |
|---|---|---|
| A | 70–88% (C1: 0.6%) | 33–38% (C1: 0.1%) |
| B | **91–93%** | **40–44%** |

Median unit ~930 tokens against a 512-token window. This is a genuine design error: roughly a
third to a half of the corpus was invisible to the reranker.

**It does not explain the result.** Track B is *more* truncated on every condition and shows
*no* harm; its most truncated condition (C0, 91.7%) is also its most improved (+0.040). Any
account resting on truncation predicts the opposite of what was observed.

### 2. Baseline recall predicts the harm (POST-HOC, EXPLORATORY)

Across all 12 condition-track pairs, the rerank delta correlates strongly and negatively with
the un-reranked baseline: **Pearson r = −0.853, Spearman ρ = −0.888**; within Track A alone
ρ = −0.886.

Every condition with base recall > 0.77 was harmed (four significantly). Every condition
below 0.41 was neutral-to-positive.

This is the standard precondition for reranking: **a reranker only helps if it outranks the
first stage.** Where the RRF hybrid already places gold in the top-5, a weaker cross-encoder
can only shuffle it out; where the first stage is weak, there is headroom and little to lose.

**Not pre-registered. Limitations:** n=12; track is nearly collinear with baseline recall (all
Track A high, all Track B low), so "high baseline" cannot be fully separated from "synthetic
corpus". A hypothesis for a future pre-registered test, not a finding.

### 3. A text-quality effect, isolated by a matched comparison

C3 and C4 on Track A are **truncation-matched**: same unit count (90), same mean length (719),
same truncation (70.0%), text loss 33.5% vs 33.7%. Yet C4 is significantly harmed (−0.091,
p=0.007) and C3 is not (−0.028, n.s.).

Same corpus size, same window loss, different outcome — so something about the formatted text
in C3 makes what *does* fit in the window more useful. This is the same signal as the
significant H6a interaction, reached independently.

## What is NOT concluded

- **Not** "reranking does not work." One model, one window setting, two corpora, on a system
  whose first stage is already strong where the harm appeared.
- **Not** a readability or faithfulness result. Both judges were skipped (no `ANTHROPIC_API_KEY`;
  see `results_v13/BLOCKERS.md`). **The `DECISION: PARTIAL (H3=supported)` line in
  `results_v13/results.md` is therefore not interpretable** — it reads zeroed judge scores.
  Genuine H1–H4 evidence remains the v1.1 run in `results/` (`run-20260724-174208`).

## One-shot discipline

Per §6 of the amendment: re-testing at a longer `max_length`, or with a different reranker,
**on this same Track A/B split is not a fresh test.** Any retry needs a new pre-registered
amendment stating what changed and why. The obvious next design — window ≥ unit size, and a
corpus where first-stage recall leaves headroom — is exactly the kind of change that must be
declared in advance rather than tuned into significance.

## Incidental findings

- **Common-size control reproduced on both tracks:** Track A +0.148 (0.608 → 0.756),
  Track B +0.067 (0.360 → 0.427). Formatted text retrieves better at fixed unit size,
  independent of reranking. Track B is the first time this control has ever produced a
  number — it was silently discarded on Windows before the encoding fix.
- **Exact reproducibility:** all six Track A conditions reproduced to the digit across two
  independent runs (deterministic corpus seed, cached LLM, pinned models, stable tie-break).
- **Cost:** zero LLM spend. Every corpus-building call was a cache hit (Track B C2 alone:
  378 cached, 0 fresh); the reranker is a local CPU model.
