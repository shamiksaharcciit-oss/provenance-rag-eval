# Results — PW-1, provenance-width separation

**Date:** 31 July 2026 · **Freeze:** `posthoc_PW1_provenance_width.json`, stamped
2026-07-30T14:19:20Z · **Arm declarations:** `posthoc_PW1_ARM_DECLARATIONS.md` (D-1…D-7), pinned
2026-07-30 23:09:16, **37 minutes before the first arm value existed** (23:46:00) ·
**Errata:** E-1…E-5 · **Post-arm findings:** PA-1…PA-5 · **Artifacts:** `results_pw1/` ·
**Step 0 (descriptive):** `Results_PW1_Step0_Descriptive.md`

**This is a POST-HOC analysis, not a chain entry.** The retrieval data it re-scores were observed
before it was designed. Its integrity property is that the subset definitions, the arms, the
metric, the families and the interpretation rule were frozen before any outcome under them was
computed — **not** that the data were unseen. That is weaker than the pre-registration chain's
property and is labelled as such wherever it appears.

---

## 0. What PW-1 measured, in one binary

The white paper's §11 states that formatted units claim more original-document surface per indexed
token than unformatted ones, so at fixed *k* they get more chances to overlap a gold span — and
that **the effect and the artifact are not separable within this harness.** PW-1 is the attempt to
separate them.

A four-rung scoring ladder was frozen: S0 (published), S1 (minus absorbed), **S2 (minus inherited,
primary)**, S3 (minus both). **It collapsed to two rungs.** Absorbed ranges change claimed surface
and never change a hit — `S0 ≡ S1` and `S2 ≡ S3` in outcome on all eight cells (PA-1). So:

> **The whole design reduces to one question: does inherited provenance count as a hit?**

Two consequences follow, and they are why the result is hard to argue with:

- **The primary scoring coincides with the hostile floor.** S2 carries the headline; S3 is the most
  hostile reading anyone can ask for; they agree on every cell. "You chose a harsh correction" has
  no purchase.
- **A lenient reading fails symmetrically**, since `S1 ≡ S0`.

### The practitioner's reading, which is why the correction is the right measurement

Because `S2 ≡ S3`, the primary number is the **strictly-contains** number: the rate at which the
retrieved unit *itself* holds the gold span. That is the quantity a person building a RAG pipeline
cares about — the retrieved chunk goes into a prompt, and a chunk credited with source text it does
not contain will not help the model answer.

So this is not a hostile stress test the method narrowly failed. **It is the measurement that
matches the use case, and the published figure was the generous one.**

### Could this have come out the other way?

Yes, and that matters for reading everything below. The frozen interpretation rule has a SEPARATED
branch reachable at `r ≥ 0.75` with significance retained; the aggregation rule, the CI, its seed,
the Holm scope and the powered predicate were all pinned before the numbers existed. The rule that
produced the unfavourable answer was not chosen after seeing it.

---

## 1. Headlines — three families, reported separately

| Family | Headline | cells | applicable | powered |
|---|---|---|---|---|
| **1 — size-matched control** (naive-256, original vs formatted) | **NOT SEPARATED** | 4 | 3 | 3 |
| **2 — composition** (C4 vs C0, Track A) | **UNDERPOWERED** | 2 | 1 | 0 |
| **secondary** (C4 vs C0, Track B) | **NO APPLICABLE CELLS** | 2 | 0 | 0 |

**applicable** — branch 1 did not fire: `delta_full` is significant under the frozen
`branch_1_significance` (Holm within the declared PW-1 family). Computable from the freeze alone.
**powered** — branch 2 did not fire: the S2 CI does not contain **both** zero and `delta_full`.

**These three do not combine.** Family 1 is a statement about the size-matched control at 256 and
says nothing about C4. Family 2 is a statement about C4 and says nothing about the control. Any
sentence merging them is unsupported by this analysis.

**UNDERPOWERED and NO APPLICABLE CELLS are different states.** Family 2's arm *ran* and could not
discriminate. The secondary family's arm was **never exercised** — no cell reached applicability at
S0. Attempted-and-blocked must never render as never-attempted.

---

## 2. Family 1 — the size-matched control: NOT SEPARATED

**The aggregate governs.** Under the frozen rule the family headline is the least favourable label
among applicable and powered cells: **NOT SEPARATED.**

The three applicable cells were:

| Cell | `delta_full` | S2 delta | S2 95% CI | K | `r` | classification |
|---|---|---|---|---|---|---|
| MiniLM / Track A | +0.1534 = 27/176 | +0.0852 = 15/176 | [+0.0170, +0.1534] | 39 | **15/27 = 0.5556** | PARTIALLY SEPARATED |
| bge / Track A | +0.1477 = 26/176 | +0.0909 = 16/176 | [+0.0227, +0.1648] | 42 | **16/26 = 0.6154** | PARTIALLY SEPARATED |
| bge / Track B | +0.0667 = 10/150 | −0.0133 = −2/150 | [−0.0533, +0.0267] | 10 | **−2/10 = −0.2000** | NOT SEPARATED |

MiniLM / Track B is NOT APPLICABLE (`delta_full` +0.0267, not significant), so it does not enter the
aggregate; its `r` is −6/4 = −1.5000, reported descriptively.

`r` is given as a fraction beside the decimal throughout, because it is exactly a ratio of query
counts. Small-integer fractions are self-checking by inspection, and 4 dp hid the defect recorded in
PA-2 on three of four cells.

### How much of the advantage was inherited provenance

| Cell | advantage removed by stripping inheritance |
|---|---|
| family 1, MiniLM / Track A | 12/27 = **44%** |
| family 1, bge / Track A | 10/26 = **38%** |
| family 2, MiniLM / Track A | 6/10 = **60%** |
| **family 1, bge / Track B** | 12/10 = **120%** — not merely erased but **reversed** |

The last is the single most informative number in the study. On Track B under bge, removing credit
for text the unit does not contain turns a +0.0667 advantage into a −0.0133 deficit.

### The mechanism, named precisely

The channel is chunk-to-segment range inheritance at
[formatted.py:86-94](src/chunkers/formatted.py#L86-L94): a 256-token chunk inherits the **entire**
`source_ranges` of every ~384-token formatter segment it overlaps. It accounts for **97.35%**
(Track A) and **99.83%** (Track B) of excess claimed width, against absorption's 2.65% and 0.17%.
The unformatted arm has no such channel — its width ratio is exactly 1.0000 by construction.

The accurate claim is **not** "the effect shrank under a correction". It is:

> **The measured benefit on the size-matched control was mediated by an indexing behaviour the
> paper does not document.**

---

## 3. Family 2 — composition: UNDERPOWERED

**The frozen qualifier applies to every family-2 label** (`family_2_labels_carry_a_qualifier`): the
contrast being tested is one the v1.1 pre-registration's `prose_rule` does not license as a "beats"
claim (PW1-F3). Family 2 measures whether an **observed** difference depends on inherited ranges; it
cannot establish C4 > C0.

The single applicable cell, MiniLM / Track A: `delta_full` +0.0568 = 10/176, S2 delta +0.0227 =
4/176, S2 CI [−0.0170, +0.0625], `r` = 4/10 = 0.4000. The CI contains **both** zero and
`delta_full`, so branch 2 fires: the arm cannot discriminate between the effect being intact and
being gone.

**C4 > C0 is therefore neither established nor refuted by PW-1.** That is weaker than either
"supported" or "withdrawn", and it is the correct statement. bge / Track A is NOT APPLICABLE
(`delta_full` +0.0455, CI lower bound exactly +0.0000, which under the frozen `boundary_rule` does
not exclude zero); its `r` is −10/8 = −1.2500, descriptive.

## 4. Secondary — C4 vs C0 on Track B: NO APPLICABLE CELLS

Both cells are NOT APPLICABLE at S0, so the correction arm was never exercised. Descriptive `r`:
MiniLM −6/5 = −1.2000, bge 3/7 = 0.4286. No inferential claim.

---

## 5. Guard dispositions — every guard, including the resolved blocks

A guard reading PASS with no account is indistinguishable from one never exercised.

| Guard | Disposition |
|---|---|
| **1 — reproduce before compute** | **PASS 8/8**, every published level to the published digit. Family 2 and secondary by re-score of persisted ranked lists; family 1 by re-run. See below on the encode path. |
| **2 — NC-A / NC-B** | **PASS.** NC-A (gold only in an absorbed range): S0 hit, S1 miss, **S2 hit**, S3 miss. NC-B (gold only in an inherited range): S0 hit, **S1 hit**, S2 miss, S3 miss. Each rung has a distinct (NC-A, NC-B) profile, so none can be silently equal to another. NC-B failed on first construction — at `soft_target 24` every sentence became its own segment, so no chunk inherited anything. It **asserted** rather than skipping, which is why the miswiring surfaced. |
| **3 — ship the code** | `scripts/` and `tests/` for this analysis are in the record. |
| **4 — rebuild fidelity** | **PASS, exact.** Rebuilt claimed ranges match `top_hit_provenance` on **147/147, 160/160, 149/149, 154/154, 61/61, 70/70, 71/71, 76/76** rows. A first version scanned only the top 5 and reported 138/147 and 148/160 — a **bug in the checker**: `top_hit_provenance` is populated for hits within k=10, and 9 and 12 rows have `first_hit_rank > 5`. Generalised as template **A1d**: a guard whose correct behaviour is exact equality asserts equality and halts, never reports a rate. |
| **D-7 — S0 as arm zero** | **PASS 8/8.** Every cell's S0 reproduces the stamped levels and `delta_full` exactly, and the unformatted arm's hit vector is identical across all four rungs. Both checkers demonstrated failing first: one `source_range` moved by a single character, and a strip mis-targeted at the unformatted arm. |
| **A7 — `r ≤ 1.0`** | Held on all 32 rung-cells. Now runs on **every rung that computes `r`**, not only the one consumed (PA-3). |

### Guard 1's encode path — stated, not omitted

Family 1's four cells were re-run, and the encode ran on a **per-batch process-isolated path**
(`src/pw1/safe_encode.py`), which differs from the published runs' monolithic call. **This is not a
declared deviation**, and the reason is positive rather than an absence:

- **By construction** — `encode` sorts inputs by descending `_input_length` and encodes contiguous
  slices at `batch_size`. Replicating that sort and those boundaries gives every batch the same
  *set*; padding is set by a batch's longest member, a property of the set; and a transformer
  forward pass has no reduction across the batch dimension. Process boundaries cannot affect float
  arithmetic.
- **By demonstration** — six tests assert `np.array_equal` against the monolithic path on MiniLM,
  including a tie-split case, a partial batch, and a row-order check.
- **By corroboration** — all four family-1 bge levels then reproduced exactly.

`_can_flatten_inputs()` is False on CPU so `_interleave_sorted_indices` does not apply, and the
module **asserts** that rather than assuming it.

### The block that resolved, and what resolved it

`BLOCKED / ENVIRONMENT` → **RESOLVED**. `BLOCKED / PLATFORM SUSPECT` → **retired, never warranted**.

bge segfaulted (`0xC0000005`) partway through encoding, intermittently, at an increasing rate. The
cause was **memory exhaustion**: 40 `Resource-Exhaustion-Detector` low-virtual-memory events since
2026-07-23, escalating 1 / 1 / 10 / 7 / **16 on 07-30**; 393 MB free of 7,739 MB; `vmmemWSL` holding
~4 GB. **No WHEA and no machine-check entries — hardware ruled out, not merely doubted.**

That explains every observation at once: model-size dependence (bge ~110M params vs MiniLM ~22M),
batch-size dependence (batch 8 succeeded 4/4 where batch 64 failed 8/8), intermittency, the rising
failure rate, and why 2026-07-26 succeeded on the same stack.

**A thermal hypothesis and an environment-regression hypothesis were both raised and both
falsified** — install dates put every package at 2026-07-23, *before* both published runs, so the
stack never changed. Labelled per template **A1g**; the falsified claim is corrected in errata
**E-5**, where a reader chasing it would look, rather than only in a later commit message.

**The fault is fail-stop.** Four successful encodes of identical input were **bit-identical**; an
allocation failure prevents a computation rather than corrupting one. Nothing computed on this
machine is in question on account of it.

**The diagnosis confirmed itself rather than being masked by a workaround:** once memory was freed,
Track B resumed from twelve already-banked checkpoint batches and **no retry fired at all**.

---

## 6. Limitations

**PW-1 does not ask whether inherited provenance is a *valid* attribution, and cannot.** Deciding
that requires a different gold-span protocol — one that scores at segment granularity by design
rather than by inheritance. **This does not modify the headline**, and the burden runs the other
way: a benefit visible only when a unit is credited with text it does not contain is not a retrieval
benefit in the sense a reader will assume.

**Family 2's power was insufficient** to discriminate under correction at n = 176. That is a fact
about the study's size, not about C4.

**Track A is synthetic**, so two of family 1's three applicable cells sit on generated prose. The
third, bge / Track B, is real academic prose — and it is the cell that reversed.

**Absorption's inertness is a property of these corpora**, not a general result. NC-A demonstrates
that absorbed ranges *can* decide a hit; on Track A and Track B they never do.

**The exposure is bounded.** Inheritance requires format-then-re-chunk, so it exists only in fmt256,
C4 and C5. C0/C1/C2 have width exactly 1.0000; C3 shows no inflation. Parity with contextual
retrieval, the margin over semantic chunking, and all four ablations are untouched.

---

## 7. What this hands to the paper

For transcription, not re-derivation. **No paper edit has been made.**

1. **The size-matched control does not separate from the width artifact** under pre-registered
   correction. Family 1 reads NOT SEPARATED.
2. **The inheritance channel is undocumented and must be described.** It carries 97–99.8% of excess
   width and 38–120% of the measured advantage.
3. **PW1-F3's fix is now insufficient rather than pending.** Deleting one adverb does not address a
   headline whose corroborating control has failed.
4. **C4 stands as not-established-not-refuted** — neither supported nor withdrawn.
5. **PW1-F1 and PW1-F2 stand** as recorded: §11 names the wrong channel and the wrong stage, and the
   methods passage does not match the implementation for two-stage conditions — a reproducibility
   gap, not only a threat to validity.

What the paper can still say accurately: the formatter produces measurable retrieval differences;
the practical C4 configuration is not refuted; the size-matched control's advantage is substantially
attributable to inherited provenance rather than to retrieval; and the evaluation was
pre-registered and reported against itself.

That last is not a consolation. **A method paper that reports its own control failing is more useful
to a reader than one that does not, and materially harder to attack.**

---

## 8. Corrections to this document's own numbers

Recorded rather than silently superseded.

**The `r` values first committed at `0eb04d3` — 0.5554, 0.6154, −0.1994, 0.3996 — are superseded**
by 0.5556, 0.6154, −0.2000, 0.4000 (`9022e9a`). They were computed from 4-dp values on both sides of
the ratio; the exact values are ratios of query counts. `stats.r` and `classification.r` disagreed
on all eight cells — two values for one quantity. Fixed by using the D-7-verified full-precision S0
delta as the denominator, with an assertion that the two paths now agree exactly. **No
classification moved.** Full account in **PA-2**.

`bge / Track A` is why `r` is reported as a fraction: 16/26 rounds to 0.6154 and so did the wrong
computation. Only `−2/10` round-tripped distinctively enough to expose the defect — the same
near-miss structure as guard 4's, where three of four cells coincided.

**Errata E-1 is now complete across all eight published cells.** Family 1's three remaining cells
had no persisted per-query vectors when E-1 was written; they do now. Exact p against stamped
Monte-Carlo: 0.00010 / 0.00020, 0.34375 / 0.34227, 0.00007 / 0.00010, 0.01294 / 0.01350, with
K = 47, 10, 42, 14. **Every branch-1 classification is unchanged under exact p.**
