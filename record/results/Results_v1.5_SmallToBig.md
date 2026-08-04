# Results — v1.5 Small-to-big / parent-child retrieval (M7)

**Date:** 28 July 2026 · **Pre-registration:** `preregistration_v15.json`
(frozen 2026-07-28T16:07:33Z, after terminal review, before any run).
**Plan:** `Experiment_Plan_v1.5_SmallToBig.md`
**Artifacts:** `results_v15_merged/` (authoritative statistics), `results_v15_A/`, `results_v15_B/`,
`results_v15_B_C4_128/`, `results_v15_B_C0_256/`, `results_v15_B_C2_256/`, `results_v15_B_C4_256/`
**Bundle:** `rag_formatter_v1.5_smalltobig_REJECT_HARM.zip` (MANIFEST.txt carries per-file SHA-256)
**Supersedes:** v1.4 (frozen 10:50:48Z, SUPERSEDED BEFORE RUN — never executed).

---

## Verdict: REJECT_HARM

Ranking units by **best-child score** instead of **whole-unit score** produced a **statistically
significant reduction** in recall@5 on a primary condition. Under the frozen rules:

> `REJECT_HARM`: significant **negative** effect on any primary condition on **either** track.
> `branch_precedence`: REJECT_HARM takes precedence over **every** other branch, **including a
> full ADOPT sweep**; a harm finding is reported as harm, never as a null and never offset by
> gains elsewhere.

**C0 @128 on Track A: −0.0966, 95% CI [−0.1648, −0.0341], K = 35 discordant (9 up / 26 down),
p_exact = 5.9881e-03, p(Holm) = 3.5929e-02.** Significant under Holm over six, under Holm over three,
and under Bonferroni — the harm does not depend on how the family is drawn.

C0 is a primary condition, so the verdict was determined by Track A alone. Track B was run in
full regardless — see §3 for why.

### The verdict overrides a full ADOPT sweep, and that is the point of contention

Track B returned **significant gains on all six cells** (+0.060 to +0.160, all six significant
after Holm by exact enumeration), with a
significant-positive set of **{C0, C2, C4} at both child sizes**. Read on its own, the frozen
outcome table gives **ADOPT**.

ADOPT additionally requires H7a clean — no significant harm on Track A — and it is not.
So the precedence clause applies as written:

**A single significant harm on Track A overrides six significant gains on Track B.**

I wrote that clause to stop a harm being laundered by gains elsewhere, and I am honouring it
because it was frozen before any data and rewriting a decision rule after seeing which way it
cuts is the failure this apparatus exists to prevent.

But the label alone is misleading, so the finding is stated plainly here:

> **Small-to-big produces large, robust gains on the primary track and harm on the secondary —
> and the split falls exactly where the pre-registration predicted, before any data existed.**

§2's bound was +0.148…+0.210 for Track A with the plan stating outright that Track A *cannot
express a success criterion*, against +0.600…+0.647 for Track B. Track A produced one
significant harm and five nulls. Track B produced six significant gains. The mechanism is
**conditional on first-stage headroom**, which is a substantive result, not a failed test.

### A design question this raises about my own criteria

`REJECT_HARM` covers "either track". Track A is designated a **no-harm check** — a guard, not a
hypothesis-bearing arm. Letting that guard veto the primary track's result was not the intent
when the clause was written; the intent was to stop *within-track* offsetting.

**Recorded as a finding about the criteria, not as a change to them.** A future amendment should
decide explicitly whether a harm on a track pre-declared incapable of expressing success should
carry veto power over the primary, or should instead force `ADOPT_SCOPED` with the harm stated
in the verdict text. That decision must be made before data, like every other.

Unlike v1.3, the criteria **did** contain the branch this outcome needed. That branch exists
because v1.3's did not.

---

## 0. p-values are exact, not sampled

The pre-registered test is a sign-flip permutation on per-query differences. On paired binary
outcomes that null is **exactly enumerable**: only the `K` discordant pairs contribute, and
enumeration is over `2^K`. Every cell here has `K ≤ 35`, so all twelve enumerate in
milliseconds. This is the same test the pre-registration specifies, computed without sampling
error — not a substitute, and no amendment is needed. `src/stats/tests.py::exact_signflip_p`,
recomputed by `scripts/merge_v15.py`; the 10k Monte-Carlo estimates are kept beside it as
`p_mc_10k`.

**`K` is reported for every cell.** It is the sample size the test actually runs on, and a
paired binary p cannot be judged without it — `n = 176` with `K = 8` is not a study of 176.

**What exactness does and does not buy — five points, because the label invites over-reading.**

1. It is the **same null**, not a more powerful test. Sign-flip permutation on paired
   differences is what was frozen; enumeration evaluates it completely instead of by sampling.
   No amendment, and no claim to extra sensitivity.
2. It removes **sampling error only**. Every other source of uncertainty — one corpus, one
   embedder, two child sizes, `recall@5` as the metric — is untouched and undiminished.
3. It changes **one classification**: Track B C2 @128, reported marginal at a sampled
   `p = 0.0524`, is significant at `p_exact = 0.049042`. The two are the same quantity, one of
   them sampled. Nothing else moves.
4. **Precision is now reported to six significant figures, not to fixed decimals.** Track B
   C0 @128's exact p is `8.0466e-07`; at 4 dp it prints as `0.0000` and at 6 dp as `0.000001`.
   An earlier version of this table printed `0.0000009`, which is wrong in the first digit —
   rounding discarded the very value the exactness was computed for.
5. It does not make a **0.001 margin robust**. C2 @128 clears α by 0.001 and is reported that
   way wherever it appears.

---

## 1. Track A — six of six non-positive, one significant

n = 176. Holm across **all six tests** (3 conditions × 2 child sizes) as a single family.

| Cond | size | base | +s2b | Δ | 95% CI | K | +/− | p_exact | p(Holm) | |
|---|---|---|---|---|---|---|---|---|---|---|
| C0 | 128 | 0.7898 | 0.6932 | **−0.0966** | [−0.1648, −0.0341] | 35 | 9/26 | 5.9881e-03 | **3.5929e-02** | **HARM** |
| C2 | 128 | 0.8523 | 0.8182 | −0.0341 | [−0.0739, +0.0057] | 12 | 3/9 | 0.1460 | 0.717 | n.s. |
| C4 | 128 | 0.8352 | 0.7955 | −0.0398 | [−0.0852, +0.0057] | 17 | 5/12 | 0.1435 | 0.717 | n.s. |
| C0 | 256 | 0.7898 | 0.7500 | −0.0398 | [−0.0909, +0.0114] | 21 | 7/14 | 0.1893 | 0.717 | n.s. |
| C2 | 256 | 0.8523 | 0.8125 | −0.0398 | [−0.0852, +0.0057] | 17 | 5/12 | 0.1435 | 0.717 | n.s. |
| C4 | 256 | 0.8352 | 0.8352 | **+0.0000** | [−0.0341, +0.0341] | 8 | 4/4 | 1.000 | 1.000 | n.s. |

**Every baseline reproduces v1.3 exactly** (0.7898 / 0.8523 / 0.8352), in all six cells and
again in all six of Track B's. The parent arm is provably untouched, so the only thing differing
between arms is the ranking function — which is what §4 promised, what makes the comparison
interpretable, and the strongest correctness evidence in this run.

The harm is robust to how the family is drawn: significant under Holm over six, under Holm over
three, and under Bonferroni.

### Two readings

**Harm scales with how far the child departs from the ranked unit.** The single significant
cell is the most aggressive subdivision tested (5.5 children per 768-token parent). Everything
at 256 is n.s. That is a coherent mechanism, not scattered noise: a 128-token child carries too
little context to rank well, and `max` over such children is a worse ranking function than the
whole unit's own embedding.

**C4 @256's +0.0000 is cancellation, not degeneracy.** An earlier draft of this document read
the exact zero as the treatment reproducing the baseline query-for-query — an implementation
check passing. **That was wrong, and it is checkable from the shipped artifacts.** The two
per-query vectors are not identical: **8 of 176 queries change outcome, 4 up and 4 down**
(indices 3, 14, 19, 44, 65, 67, 85, 162), and the sum happens to be zero. The same cell is
**−0.0511 at k = 1**, so it is not neutral away from k = 5 either. Stated as the fact rather
than the interpretation: *changes 8 of 176 queries, 4 up and 4 down, net zero at k=5.*

### C2's k=1 gain is the only positive movement on Track A

| Track A, C2 | k=1 | k=3 | k=5 |
|---|---|---|---|
| @128 | **+0.0966** | −0.0284 | −0.0341 |
| @256 | **+0.0966** | −0.0227 | −0.0398 |

Identical at both child sizes. C2's baseline `k=1` is anomalously low (0.4602) against C0's
(0.5625) despite C2 being far better at `k ≥ 3` — the right unit sits at rank 2–3 under
whole-unit scoring, and best-child ranking promotes it to rank 1. That is **dilution-rescue,
visible in the metric where dilution should hurt most, on the track §2 said had no room to
work.** Post-hoc, exploratory, and on a secondary metric — all three — but size-robust and
mechanistic, so it is recorded rather than lost because k=5 went the other way.

### Track A behaved as §2 predicted, before any data existed

§2's bound for Track A was +0.148 to +0.210 and the plan stated outright that Track A **cannot
express a success criterion for this treatment**. It did not. The pre-registered scoping — Track
A as a no-harm check rather than a primary — was correct in advance, not in hindsight.

---

## 2. Track B — the primary track

n = 150. Holm across **all six tests** as a single family, p by exact enumeration, recomputed
from the persisted per-query vectors (`scripts/merge_v15.py`) — the per-invocation Holm values
in the individual condition artifacts are single-test artifacts of running conditions in
isolated processes and are superseded here.

| Cond | size | base | +s2b | Δ | 95% CI | K | +/− | p_exact | p(Holm) | |
|---|---|---|---|---|---|---|---|---|---|---|
| C0 | 128 | 0.3533 | 0.5133 | **+0.1600** | [+0.1000, +0.2200] | 26 | 25/1 | 8.0466e-07 | **4.8280e-06** | **GAIN** |
| C4 | 128 | 0.4000 | 0.5200 | **+0.1200** | [+0.0600, +0.1800] | 22 | 20/2 | 1.2112e-04 | **6.0558e-04** | **GAIN** |
| C4 | 256 | 0.4000 | 0.5000 | **+0.1000** | [+0.0467, +0.1533] | 19 | 17/2 | 7.2861e-04 | **2.9144e-03** | **GAIN** |
| C0 | 256 | 0.3533 | 0.4533 | **+0.1000** | [+0.0400, +0.1600] | 23 | 19/4 | 2.5995e-03 | **7.7984e-03** | **GAIN** |
| C2 | 256 | 0.3867 | 0.4600 | +0.0733 | [+0.0200, +0.1333] | 19 | 15/4 | 0.01921 | **0.0384** | **GAIN** |
| C2 | 128 | 0.3867 | 0.4467 | +0.0600 | [+0.0067, +0.1133] | 17 | 13/4 | 0.049042 | **0.049042** | **GAIN** ⚠ |

**Every baseline reproduces v1.3 exactly** (0.3533 / 0.3867 / 0.4000).

**Six of six positive and six of six significant.** The significant-positive set is
**{C0, C2, C4} at both child sizes** — a full sweep.

### C2 @128 is significant by 0.001, and that margin travels with the claim

The first version of this document reported `p = 0.0524` and labelled the cell **marginal**.
That number was a 10k Monte-Carlo estimate with SE ≈ 0.0022 at this p; the exact enumeration —
17 discordant pairs, 6 428 of 131 072 sign assignments at least as extreme — gives
**p_exact = 0.049042**. It landed on the far side of α by resampling noise alone.

**This is not cosmetic.** As first printed, the significant-positive set at 128 was {C0, C4},
which `decision_arithmetic.outcome_table_at_128` names explicitly as *"KILL — not a pre-named
family"*. §0's own headline sentence — *"read on its own, the frozen outcome table gives
ADOPT"* — was contradicted by the p-column beneath it. The exact test is what makes that
sentence true. (`results_v15_merged/results.json` had already listed this cell under
`significant_gains`; the exact test resolves that disagreement in the artifact's favour.)

**The margin is 0.001 and is stated wherever the result is.** Significant *by the exact test*,
not robust.

### The criteria contain a genuine ambiguity, recorded not resolved

The frozen `significant_definition` — *"paired CI excludes 0 after Holm"* — names two
procedures, and on this run they disagree on two cells:

| Track B | unadjusted 95% CI | p(Holm) | Bonferroni 99.17% CI (m=6) |
|---|---|---|---|
| C2 @128 | [+0.0067, +0.1133] excludes 0 | 0.049042 < α | **[−0.0133, +0.1333] includes 0** |
| C2 @256 | [+0.0200, +0.1333] excludes 0 | 0.0384 < α | **[0.0000, +0.1467] touches 0** |

The Holm-corrected p governs, because that is the criterion the outcome table is written in
terms of. Nothing turns on it here — **REJECT_HARM holds under every reading**, and Track A's
harm is significant under all three. But a criteria set in which two named procedures can
disagree about the same cell is a defect in the criteria, not a judgement call at analysis
time. **The next amendment must define significance by exactly one procedure.**

### C4 is the consequential number

C4 — formatted corpus under a naive cutter, ignoring the formatter's own markers — is the
paper's central composition finding and its recommended deployment. It gains **+0.1200** at 128
and **+0.1000** at 256, both robustly significant. Whatever the verdict label, small-to-big
helps the configuration the project actually recommends, on real academic prose.

### The C2 pattern

C0 +0.1600, C4 +0.1200, C2 +0.0600 at 128 — the blurb condition gains **least**, roughly half
the others, and the ordering repeats at 256. Consistent with blurbs and best-child ranking being
partial **substitutes**: both supply context to a context-poor unit, so where the blurb already
did that work there is less left to recover. Suggestive, not established — one corpus, and C2 is
also the cell carrying the 0.001 margin above.

**The obvious way this reading could be an artifact was checked and ruled out.** The recorded
`blurb_to_child_ratio` does not scale with child size and *inverts* on Track A (0.5669 → 0.9711
between 128 and 256, where a length-invariant blurb requires roughly a halving). If the blurb
were being attached differently at the two sizes, the substitutes story would be measuring the
harness. It is not: `scripts/check_blurb_ratio.py` rebuilds C2 cache-only and finds the
per-parent blurb **identical at both sizes on all 90 Track A and all 378 Track B parents** —
which is forced by construction, since blurbs are keyed on parents and the parent inventory is
pinned across child sizes.

The anomaly is the **estimator**. `blurb_to_child_ratio` is a mean of ratios, and `1/t` is
convex, so short remainder children dominate it. Widening the ceiling produces fewer, larger
children with a longer short tail — the share under 32 tokens goes 6.8% → 17.2% on Track A
(shortest child: 3 tokens) and 1.6% → 6.0% on Track B, which is exactly why A inverts and B is
nearly flat. The ratio of means, which is what the diagnostic was meant to express, behaves:

| C2, ratio of means | @128 | @256 | scaling |
|---|---|---|---|
| Track A | 0.4510 | 0.2582 | ×0.57 |
| Track B | 0.5013 | 0.2778 | ×0.55 |

Both essentially the ×0.5 the construction predicts. `blurb_dilution()` now reports the ratio of
means, the mean of ratios, and the short-child share that separates them; `blurb_to_child_ratio`
is kept unchanged so the shipped artifacts stay readable, with its defect documented in place.

---

## 3. Why Track B was run after the verdict was already determined

C0 @128 fixed the verdict at REJECT_HARM before Track B began. It was run in full anyway:

1. **Stopping when the answer has turned unfavourable is the behaviour this discipline exists to
   prevent**, even where the stopping rule is technically satisfied.
2. Track B is the **primary** track. A record of H7 without it is incomplete.
3. "REJECT_HARM with Track B strongly positive" and "REJECT_HARM with Track B null" are
   materially different findings. The verdict wording is identical; what it *means* is not.

---

## 4. What this does NOT show

- **Not** "small-to-big does not work." One ranking function (`max` over children), two child
  sizes, one embedder, on corpora whose parents are 768-token units. The generation-side benefit
  — coherent parent context handed to the model — is **asserted, not measured**; this harness has
  no generation metric.
- **Not** a statement about small-to-big as deployed with *retrieval-optimised* child sizes
  against *smaller* parents. Both tested sizes are a small fraction of a 768-token parent.
- The **secondary arm** (C4 marked-section parents) was not run.

## 5. Limitations recorded before the run

Carried from the plan, unchanged by the result:

- **Coverage is near-tautological for C0/C2.** `r@∞` = 1.000 is expected by construction with
  contiguous chunking under `any` overlap. C4 was the informative case, and it too came back
  1.000.
- **Coverage retires less than it appears to.** It is measured against a unit's *claimed*
  ranges, and C4's ranges are wider than its own text (canonical units absorb duplicates'
  ranges). Retired: *no gold span falls outside the union of claimed ranges.* **Not** retired:
  *no gold text was removed by dedup.*
- **C4 "denser parents" remains a hypothesis, and this run weakens it further — but the two
  tracks disagree in sign, and an earlier draft cited only the one that flattered the point.**

  | @128, C0 / C2 / C4 | parents | children | C4 vs C0 |
  |---|---|---|---|
  | Track A (secondary) | 90 / 90 / 90 | 497 / 497 / 485 | **2.4% fewer** children |
  | Track B (**primary**) | 378 / 378 / **379** | 2508 / 2508 / **2528** | **0.8% more** children, one more parent |

  On the primary track the density claim is not merely unsupported, it is **contradicted in
  sign**. Either way the magnitude is under 3% and the conclusion is the same one §5 already
  drew — reference resolution and right-sizing offset what dedup removes, so "denser parents"
  is a hypothesis, not a fact. Citing the primary track strengthens that conclusion rather than
  weakening it, which is why the omission mattered.

## 6. Harness failures during execution (mine)

- **A combined-track run segfaulted on Track B and destroyed six completed Track A conditions**,
  because `run_v15.py` wrote results only at the end — template §A2, the rule I had written after
  the same failure in `run.py` and then reintroduced in new code. Fixed: `results.json`,
  `per_query.jsonl` and `vectors.json` are now written after **every** condition, and tracks run
  in separate processes. All six Track A values reproduced exactly on re-run.
- Having the rule in the template did not prevent it. Applying the template as a **checklist
  against new code**, not only against plans, is the actual remedy.
- **§A2 had no negative control, which is itself a §A1b violation** — and the missing control is
  the same class of error as the incident it would have caught, the third instance of that class
  in this programme. Closed: `tests/test_persistence_survives_kill.py` starts a run, kills it
  uncatchably mid-condition (`TerminateProcess`/`SIGKILL`, not a catchable exception), and
  asserts the completed conditions and their vectors are on disk and parseable. The deliberate
  violation — the write-at-end shape — is run through the identical kill and **must lose
  everything**; without that arm a passing test would prove only that files can be written.

---

## 7. Corrections applied after first publication (29 July 2026)

Recorded rather than silently absorbed. **None changes the verdict**, which is REJECT_HARM
under every procedure considered.

| # | Was | Is | Why it mattered |
|---|---|---|---|
| 1 | p from 10k Monte-Carlo permutation | exact enumeration over `2^K`, all 12 cells, `K` reported | the pre-registered test computed without sampling error; not a substitute test |
| 2 | Track B C2 @128 "marginal ⚠", p = 0.0524 | **GAIN**, p_exact = 0.049042, margin 0.001 stated | the significant set at 128 was {C0, C4} = "KILL, not a pre-named family", contradicting this document's own ADOPT-sweep sentence |
| 3 | C4 @256 "+0.0000 is an implementation check passing" | 8 of 176 queries change, 4 up / 4 down, −0.0511 at k=1 | the claim was false and checkable from the shipped artifacts |
| 4 | density rebuttal citing Track A only (2.4% fewer children) | both tracks; the **primary** disagrees in sign (0.8% more) | the omitted track was the one that mattered, and it strengthens the conclusion |
| 5 | "substitutes" reading resting on an unexamined diagnostic | attachment proven invariant; `blurb_to_child_ratio` shown to be a broken estimator; `blurb_dilution` added | the reading would otherwise have been measuring the harness |
| 6 | §A2 asserted, never demonstrated | kill-mid-run control + write-at-end violation arm | §A1b: a guard never seen failing is not evidence |
| 7 | p printed at fixed decimals; C0@128 shown as 0.0000009 | six significant figures throughout; C0@128 is 8.0466e-07, Holm 4.8280e-06 | the displayed digit was wrong and 6-dp storage rounded the value away entirely |

Item 3 is the one worth dwelling on. The false claim was *flattering* — it read an exact zero as
proof the implementation was correct — and it survived a terminal review because nobody, myself
included, opened the vectors it was a claim about. The correctness evidence that actually exists
is stronger and needed no interpretation: **every one of the twelve baselines reproduces v1.3
exactly.** That is the claim to make.

An `errata` block has been appended to `preregistration_v15.json` recording a stale
`holm_families` clause carried from v1.4 that contradicts the governing
`decision_arithmetic.multiplicity_across_child_size`. The frozen keys are untouched; all
reported values were computed under the governing clause.
