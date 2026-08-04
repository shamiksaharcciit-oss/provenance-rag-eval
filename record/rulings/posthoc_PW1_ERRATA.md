# PW-1 errata — against `posthoc_PW1_provenance_width.json`

**Opened 2026-07-30, after the stamp (`frozen_utc = 2026-07-30T14:19:20Z`).**
**Beside the freeze, never inside it.** No stamped value is edited. Every entry is additive and
dated. Raised by review in `Check_B1_B2_cffad08_2026-07-30_1.md`.

The one-shot rule means a stamped value stays stamped whether or not a better estimator for it is
preferred later. Editing the stamped numbers to make them more accurate would destroy exactly the
property the freeze exists to establish.

---

## E-1 — §6 declares exact enumeration; the carried `p_raw` values are Monte-Carlo

**Confirmed.** §6 of the sealed text declares *"exact sign-flip enumeration over the 2\*\*K
assignments … `p_mc_10k` retained beside it."* The eight `p_raw` values carried into §5's
branch-1 table were not produced by that procedure. They come from
`src/stats/tests.py::paired_permutation_p` — a 10,000-replicate Monte-Carlo sign-flip with
`(count + 1) / (iters + 1)` smoothing — executed during the July 2026 published runs, months
before `exact_signflip_p` existed.

The review's brute-force is corroborated exactly: it predicted 0.065430 as the nearest feasible
exact p for the secondary bge/Track B cell, and direct recomputation from that cell's per-query
vectors gives **0.06543**.

**What the freeze got wrong is narrower than "the declared method was not executed," and stating
it precisely matters.** §6 governs the statistics PW-1 *computes* — the arms. The `p_raw` values
are **published inputs** that the freeze *fixes* rather than computes, exactly as `delta_full`
does ("The PUBLISHED point estimate for the cell"). The defect is that §5 tabulates them as bare
`p_raw` without labelling their provenance, while §6 sits three sections away declaring a
different procedure. A reader is entitled to assume §6 covers every p in the file. It does not,
and nothing said so.

### The exact table, recorded beside the stamped values

Recomputed with `exact_signflip_p` from per-query vectors, `K` reported as §6 requires.
`results_pw1/exact_p_recomputation.json`.

| Family | Embedder | Track | stamped `p_raw` (MC) | `p_exact` | K | +/− | Holm exact | Holm stamped | branch 1 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | all-MiniLM-L6-v2 | A | 0.00020 | **0.00010** | 47 | 37/10 | 0.00010 | 0.00060 | APPLICABLE |
| 2 | all-MiniLM-L6-v2 | A | 0.02050 | **0.02127** | 16 | 13/3 | 0.04254 | 0.04100 | APPLICABLE |
| 2 | BAAI/bge-base-en-v1.5 | A | 0.09309 | **0.09625** | 18 | 13/5 | 0.09625 | 0.09309 | NOT APPLICABLE |
| sec | all-MiniLM-L6-v2 | B | 0.17868 | **0.17969** | 9 | 7/2 | 0.17969 | 0.17868 | NOT APPLICABLE |
| sec | BAAI/bge-base-en-v1.5 | B | 0.06739 | **0.06543** | 11 | 9/2 | 0.13086 | 0.13478 | NOT APPLICABLE |

**Every branch-1 classification is unchanged under exact p.** Family 1's remaining three cells
(MiniLM/B, bge/A, bge/B) have no persisted per-query vectors and will be recomputed as B4's
re-runs produce them; `common_size_ci.py` now persists `_vectors` for exactly this reason.

**The 2.4 disagreement survives.** Secondary bge/Track B: `p_exact` 0.06543 and Holm 0.13086 both
above α, while the CI still excludes zero. The three-criteria disagreement is a property of the
data, not an artifact of the p-value procedure.

### PROC-1 gains a second failure class

This is a fifth instance for PROC-1 and a **different class** from the other four:
**declaration/implementation divergence** — a declared procedure that does not match the executed
one. The A5b authoring gate walks each field for one-quantity-one-procedure; it would have passed
§6, because §6 names exactly one procedure. It just names one that some of the file's numbers did
not come from. The gate that catches an incomplete rule does not catch this.

**Forward control:** every numeric field in a frozen file states its provenance — computed under
this analysis, or carried from a named prior artifact — and any field declaring a method states
which of the file's numbers it governs.

---

## E-2 — the CI procedure is named nowhere in the freeze

**Confirmed, and it binds.** §5 asserts three criteria agree on all six primary cells and
specifies two: the Holm-corrected test and `branch_1_significance`. The third, "the CI excludes
zero," names a criterion but never the procedure producing the CI.

That would be pedantic if the three always agreed. They do not — the secondary bge/Track B cell is
precisely where the CI says one thing and the test another, **so the CI cannot be the test's
inversion.** It is a second, independent inferential procedure.

**Definition, recorded here:** `src/stats/tests.py::paired_bootstrap_diff` — a **paired bootstrap
percentile interval**, resampling query indices with replacement, `iters = 10000`, `seed = 1337`,
`ci = 0.95`, with `significant_ci` set when the interval excludes zero under the frozen
`boundary_rule` (a bound of exactly 0.0000 does not exclude zero). It is a **second procedure,
not an inversion of the sign-flip test**, which is why the two can disagree.

By the §A5 standard this was a gap sitting inside the document that records PROC-1. No number
changes; this is a documentation completion.

---

## E-3 — `descriptive_companion_cells` carries a stale enumeration

**Confirmed.** §4's general clause covers every NOT APPLICABLE cell — now **four**, after 2.4
specified the secondary family — but the sentence following it still enumerates two: *"family 2's
bge/Track A cell and family 1's MiniLM/Track B cell."* The two secondary cells fall under the
general clause and are named nowhere.

**The general clause governs.** All four NOT APPLICABLE cells are re-scored and reported
descriptively: family 1 MiniLM/B, family 2 bge/A, and both secondary cells.

Same edit mechanism as the `pw1_f1_refers_to` drop recorded before the stamp: an addition
elsewhere invalidated a nearby enumeration that nothing pointed at. The structural lesson is the
review's — **prefer the rule to the list of things the rule currently catches.** An enumeration
that restates a general clause has no independent content and can only go stale again.

---

## E-4 — `source_document_sha256` did not name its object

**The hash verifies.** Recomputed against the on-disk file:

```
098bf15c97e809e6df5e81ec372bff3dfce189306e34ecc2087cefed9f16c1a8   <- recorded
098bf15c97e809e6df5e81ec372bff3dfce189306e34ecc2087cefed9f16c1a8   <- sha256 of the .md on disk
```

The review's diagnosis was right without being able to confirm it: their staged copy of the `.md`
was stale, so they could only test the `freeze_text_verbatim` block. Their computed
`1a975f94…` for that block matches mine exactly. The ~3.1 KB gap is the markdown wrapper —
title, preamble, the fenced-block delimiters and the work-order checklist — which the verbatim
extraction correctly drops.

**Two objects, both now named:**

| Object | SHA-256 |
|---|---|
| `posthoc_PW1_freeze_TEXT_FOR_CONFIRMATION.md`, 40,081 bytes, as committed at `cffad08`, CRLF as in the working tree, including the markdown wrapper and checklist | `098bf15c97e809e6df5e81ec372bff3dfce189306e34ecc2087cefed9f16c1a8` |
| `freeze_text_verbatim` field of the stamped JSON, 36,939 bytes UTF-8, 568 lines, LF, no trailing newline — **the authoritative object** | `1a975f94f2c9528ba8678a46fe6097c21ded467a721fddaa7342053b82ce4bc4` |

The review's principle stands and is the reason this entry exists: *a hash you cannot
independently recompute is not an integrity check, it is a number.*

---

## E-5 — a falsified claim about the environment, corrected where it was made

**The claim:** "the published bge numbers came from a materially different environment," written
into the commit message of `4addd64` as a finding, and repeated in the `BLOCKED / ENVIRONMENT`
record.

**It is false.** Install-date forensics on `site-packages` show every relevant package dating to
**2026-07-23, 17:52–18:01** — torch 2.13.0, transformers 5.14.1, sentence-transformers 5.6.1,
tokenizers 0.22.2, numpy 2.2.6, faiss 1.14.3, safetensors 0.8.0, huggingface_hub 1.24.0 — which
is **before both published runs** (MiniLM 2026-07-24, bge 2026-07-26). The stack has not changed.
bge ran to completion on this exact stack on 07-26 and fails on it today.

**What follows.** The fault is machine state or latent nondeterminism, not a version regression.
Option (c), "restore the pinned environment", is **moot** rather than unavailable — there is no
prior environment to return to. And the fault is now known to be **intermittent**: the same
operation (fresh process, 64 longest texts, batch 64) survived once and then crashed twice on
identical input before succeeding.

**What survives.** The general lesson stands and is unaffected: pin the native stack at every
freeze, before there is a reason to. The published runs recorded python, os, embedder, llm, faiss
and seed, and nothing that could explain a native access violation — so when one appeared there
was nothing to diff. That is why C-2 now records torch, transformers, tokenizers, safetensors,
huggingface_hub, scipy, numpy, faiss, the threading environment variables, and
`torch.__config__.parallel_info()`.

**Recorded here rather than only in a later commit**, because a commit message is unamendable and
does not travel with its correction. Generalised as template rule **A1g**: a claim entering the
durable record is labelled HYPOTHESIS or VERIFIED.

---

## Code changes (pre-arm, not errata — the freeze was right and the code was narrower)

**C-1 — the `r > 1.0` halt now runs on every path that computes `r`.**
`classify_cell` divided inline on the NOT APPLICABLE branch and never reached
`retention_ratio`, so the guard did not run there. The frozen `halt_conditions` says *"r > 1.0 for
**any** cell"*, and with the secondary family specified **four of the eight frozen cells are NOT
APPLICABLE** — half the grid was unguarded. A scoring defect does not become descriptive because
the cell it appears in is descriptive. The freeze was correct; the code under-implemented it, so
the code changed and the freeze did not. Demonstrated failing on the newly-covered path in
`tests/test_pw1_interpret.py::test_halt_fires_on_the_NOT_APPLICABLE_path_too`.

Also unified: `delta_full == 0.0` returned `None` on one path and raised `ZeroDivisionError` on
the other. Both were defensible; having both was not. It now returns `None`, once, in
`retention_ratio`.

**C-2 — guard-1 artifacts pin the environment.** `common_size_ci.py` records Python, platform,
`torch`, `sentence-transformers`, `numpy`, `faiss`, `rank_bm25`, `transformers`, `scipy`, device
and thread count, and persists `_vectors`. A re-run's evidential value depends entirely on the
environment matching the one that produced the published numbers, and *"it reproduced"* without
*"under what"* is not a record — particularly because a recall metric on 176 queries can absorb a
small numerical difference without moving, which is the case where the record matters most.

**C-3 — template rule A1d**, generalised from the guard-4 correction: *a guard whose correct
behaviour is exact equality must assert equality and halt, never report a rate.* The first
guard-4 checker reported 138/147 and 148/160 — 92–94%, which reads as "mostly fine" and would
plausibly have been accepted as a rebuild tolerance. The true value was 147/147 and 160/160. **A
rate absorbs a bug; an exact count cannot.**
