# Results — v1.6, the segment-size / retrieval-budget confound

**Date:** 31 July 2026 · **Freeze:** `preregistration_v16.json`, commit `1b01f9b`,
2026-07-31T10:06:54Z · **Addendum 01:** `74d741e`, +8.2 min · **Plan:**
`Experiment_Plan_v1.6_SegmentSize.md` · **Gate 0:** `v16_Gate0_Findings_2026-07-31.md`, three
rounds · **Artifacts:** `results_v16_A_minilm/`, `results_v16_A_bge/`, `results_v16_B_minilm/`

**Freeze → first arm value → primary cell complete: 34 minutes.** Addendum 01 sits inside that
interval and is visible as doing so.

v1.6 **stands beside** v1.1. It amends no published number and does not reopen PW-1.

---

## Verdict: KILL

> **KILL** — `D_edit` not statistically distinguishable from zero on `recall@budget(1920)` in
> cell A-MiniLM.

`D_edit(768)` = **0/176**, `p_holm` 1.000. `D_edit(384)` = **+7/176**, `p_holm` 0.615. Neither
clears. ADOPT requires significance in A-MiniLM; ADOPT_SCOPED requires one of five closed,
pre-named scopes and nothing is significant anywhere; REJECT_HARM requires a significant
negative. **KILL is the only branch satisfied.**

### Six estimates, six nulls

The non-decision-bearing cells cannot change the branch — fixed in writing before either
existed — but they change what the null *means*.

| cell | m = 384 | m = 768 |
|---|---|---|
| **A-MiniLM** (decision-bearing) | +7/176, p_holm 0.615 | **0/176**, p_holm 1.000 |
| A-bge | −1/176, p_holm 1.000 | +2/176, p_holm 1.000 |
| B-MiniLM | −2/150, p_holm 1.000 | −2/150, p_holm 1.000 |

As rates: +0.0398, 0, −0.0057, +0.0114, −0.0133, −0.0133. They straddle zero in both directions
with a mean near +0.003 — about half a query in 176. Estimates behaving like draws from a
zero-centred distribution is what an absent effect looks like.

So the supported sentence is not merely *we did not detect an effect* but:

> **The effect is not present at any size, embedder or corpus this experiment can reach.**

**The six are not independent and are not combined.** The two Track A cells share a corpus and
a query set; the two sizes within a cell share everything. Pooling, meta-analysing or reporting
a combined interval would be a second procedure for a quantity that already has one (§A5b). The
description above carries the weight; a summary statistic would only be attackable.

---

## 1. Predictions, scored against sealed text

**A gap in the pre-registration, surfaced rather than resolved silently.** **None of the seven
sealed predictions names a cell.** The decision rules name `A-MiniLM` throughout, and the other
two cells are declared non-decision-bearing, so the predictions are scored **on A-MiniLM** —
but that is an **inference from the decision rules, not the sealed text**, and it is labelled
**HYPOTHESIS** under A1g. A reader who scores them differently is not contradicting the freeze.
The conservative reading was chosen deliberately: the alternative — scoring across all cells —
would enlarge scope to collect results, which is the failure this apparatus exists to prevent.

| ID | Sealed prediction | Result on A-MiniLM | Verdict |
|---|---|---|---|
| **P1** | `D_size(768)` large and positive, ≥ +0.10 on recall@5 | +38/176 = **+0.2159** | **HOLDS** |
| **P2** | `D_size(768)` shrinks substantially under `recall@budget` | +38/176 → **+23/176** | **HOLDS** |
| **P3** | `D_seam(768)` small, \|·\| ≤ +0.05, CI includes zero | +1/176 = +0.0057, CI [−0.0170, +0.0284] | **HOLDS** |
| **P4** | `D_edit(768)` positive but small under budget, ≤ +0.05, may not exclude zero | **0/176**, CI [−0.0455, +0.0455] | **HOLDS**, at the boundary of its own wording |
| **P5** | UNCUT ordering across 128…768 flatter under budget than under recall@5 | recall@5 spans 82→138 = 56 queries; budget spans 99→132 = 33 | **HOLDS** |
| **P6** | `D_reseam(768)` small and non-negative under budget | +4/176 = +0.0227, not significantly negative, and does not exceed \|`D_text`\| | **HOLDS** (blind) |
| **P7** | `D_text(768)` carries the majority of `D_edit(768)`, **conditional on `D_edit(768)` being distinguishable from zero** | `D_edit(768)` is **not** distinguishable from zero | **CONDITIONAL NOT MET — not evaluated** |

**P7 is not "not falsified."** Its condition failed, so it was never tested. Recording it as
survived would be a false credit.

**P4 held, and it deserves a sentence rather than a tick.** It was written as the uncomfortable
one — *positive but small, may not exclude zero* — and the outcome was exactly zero. A
prediction that anticipated its own claim's weakness, and was right, is worth more to a reader
than five that anticipated strength.

---

## 2. Where the advantage actually comes from

At m = 768 on the primary cell, `D_total` is **+24/176**. Its decomposition:

| term | m = 384 | m = 768 | what it is |
|---|---|---|---|
| `D_size` | +4/176 | **+23/176** | the cutter's size dial alone, no editing |
| `D_ws` | **0/176** | **0/176** | the `_emit` whitespace artifact |
| `D_seam` | +2/176 | +1/176 | seam placement, whitespace-matched, no editing |
| **`D_edit`** | **+7/176** | **0/176** | **the treatment** |
| `D_total` | +13/176 | +24/176 | |

**Of the +24 queries, +23 come from the size dial. Seam placement contributes +1. Editing
contributes 0.** The programme has been attributing to an editing pass an advantage that is
almost entirely the cutter's setting.

Both identities hold on integer numerators — **wiring checks, not validity checks**. They catch
a transposed variable; they are not evidence that the decomposition means anything.

### The null is not inertness, and the discordant counts are why

`D_edit(768)` is a net **0** built from **n01 = 8** and **n10 = 8**. The editing pass changes
the retrieval outcome on **sixteen queries** — it changes them in both directions equally.

"No effect" implies the pass does nothing. What the data show is that it does something
**arbitrary with respect to retrieval**, which for a practitioner is the worse of the two
findings: variance without expected gain. That distinction is invisible in the net, and would
have been invisible in this programme's published results, which have never reported discordant
pairs.

---

## 3. `recall@5` versus a matched retrieval budget

The most transferable result in the run, and independent of the formatter and of this
programme's thesis.

`recall@5` gives every arm five *units*. A 768-token unit hands the scorer three times the text
of a 256-token unit, so the metric rewards larger chunks for reasons that have nothing to do
with retrieval quality. `recall@budget(1920)` gives every arm the same amount of *text*.

The size effect (768 vs 256) under each:

| cell | recall@5 | recall@budget | change |
|---|---|---|---|
| A-MiniLM | +38/176 | **+23/176** | −15 queries |
| A-bge | +32/176 | **+14/176** | −18 queries |
| B-MiniLM | +5/150 | **−15/150** | −20 queries, **sign reversed** |

> **On every cell measured, correcting for retrieval budget reduced the apparent chunk-size
> effect. The reduction ranged from partial to complete sign reversal.**

That is stated as a direction that held everywhere rather than a magnitude that held once. An
earlier draft of this document carried a single "≈65%" figure computed from one cell; it is
withdrawn. With A-bge at a larger share and Track B inverting, one headline percentage would
have been a selective quotation of the run's own evidence. No ratio is reported: on Track B the
denominator is +5/150, and a ratio to a near-zero denominator is unstable by construction.

**And the other half, just as plainly: +23 survives on the primary cell.** At matched retrieval
budget, cutting at 768 still beats cutting at 256 by 23 queries, from 34 discordant favourable
against 11 unfavourable. The size effect is not merely an artifact. **Bigger segments genuinely
retrieve better on Track A**, and that is now the programme's best-evidenced empirical claim.

---

## 4. Observations — exploratory, not claims

### 4.1 Track B inverts the size effect

**Track B is exploratory, `dev_fraction` 0.0, non-decision-bearing, a single corpus of 150
queries** — and on it, under a matched retrieval budget, **smaller chunks retrieve better**:
`D_size(768)` = **−15/150**, built from **n01 = 8 against n10 = 23**, 31 informative queries. A
broad consistent tilt, not a handful.

Under `recall@5` the same contrast reads **+5/150**. So on real academic prose the published
metric did not merely overstate the size effect — it reported the **wrong sign**.

**Not an apparatus fault:** `U256` reproduces the published Track B `original_256` exactly at
**53/150 = 0.3533**.

**No test is computed.** `D_size` on Track B sits in **no declared Holm family** — the freeze
puts A-bge and B-MiniLM in none. A p-value exists in the run artifact because the script
computes every contrast uniformly; it is **not reported or interpreted here**, because reaching
for a test once a number came out interesting is what the one-shot rule exists to prevent.

**No mechanism.** There is a coherent story — dense localised answer spans in real prose, large
chunks diluting them, a fixed budget buying more distinct spans when units are small. It is a
**HYPOTHESIS** (A1g), untested, and it is not offered as explanation. What would test it: a
gold-span-density measurement per corpus, pre-registered, on a track this experiment has not
spent.

**This says nothing about the formatter, and must not be used to revisit PW-1.** It is a
statement about a metric and a chunk size.

### 4.2 On bge, the complete formatter is worse than the naive cutter

Two published bge values, reproduced exactly by this run:

| | published | this run |
|---|---|---|
| `U768` = C0, naive cutter | 0.7898 | **139/176** |
| `F768` = C3, complete formatter | 0.7727 | **136/176** |

Under `recall@5`, on the bge stack, **the complete formatter is three queries worse than the
naive baseline** — in the programme's own published numbers. `D_edit(bge, 768)` at matched
budget is +2/176, so there was never anything there to lose.

A within-stack comparison of two published values, reproduced. **Descriptive: no test, no CI,
no mechanism.** It sharpens what KILL means — the editing pass is not something that works on
one embedder and fails to replicate elsewhere. There is no embedder in this programme's record
on which the complete pass beats the naive baseline once anything is accounted for.

### 4.3 `D_text` and `D_reseam`

The frozen rule is that **a null `D_edit` is not decomposed**. The arms ran, the numbers exist,
and §A2 requires them persisted — so they are **recorded in the run artifacts and not
interpreted here**. No values are printed in this narrative, no test is computed, and no
inference is drawn. Anyone re-scoring the persisted artifact can find them.

---

## 5. Controls and run parameters

**`D_ws` = 0/176, 0/176, 0/150 — exactly zero in all three cells at both sizes.** The `_emit`
whitespace artifact is verified harmless on both embedders and both tracks, so `D_seam` needs no
correction. The control earned its place **by coming back empty**: had it not been run, the
whitespace normalisation Gate 0 G6 discovered would have sat inside `D_seam` unmeasured.

**Retrieval depth 50, not the config's implied 10** (PROC-1). `evaluate()` retrieves at
`max(k_values)` = 10, but a 1920-token budget needs ~16 units at m = 128 and 32 worst-case —
so depth 10 would have truncated the small-unit arms and **understated them**, biasing toward
large units, which is this programme's existing bias and therefore where a silent truncation is
hardest to notice. It would have corrupted `D_size` and P5 specifically. Depth 50 is safe
because `Retriever.retrieve` computes `pool = max(candidate_pool, top_k)`: at `top_k ≤ 50` the
fusion pool is unchanged and the ranking is identical. **Max realised k observed: 16** (A-MiniLM
U128) — so the truncation would have bitten.

**Encoder batches restored across runs, and the line that makes it sound.** v1.6's `U256` arm is
byte-identical to PW-1's `orig256`, so its encoder batches restored from the content-hash
checkpoint cache rather than being recomputed (A-bge, 32 s). This is **not** the forbidden
import of a base term from another run: what was restored is an **intermediate that is a pure
function of byte-identical inputs**, whose determinism is separately verified
(`tests/test_pw1_safe_encode.py`, bit-identity), and the arm value was computed **in this run,
under this environment**. A quantity that entered a decision may never be restored, whatever its
provenance.

**Memory margin, recorded as a margin and not a success.** A-bge ran with **224 MB free**
against the **393 MB** at which bge failed during PW-1 — roughly 40% headroom on a failure point
that is itself a single observation. Thirteen arms, **zero crashes** on the sharded path. It
worked, and the margin was thin. Anyone running this apparatus on a larger corpus or model needs
both numbers, not "zero crashes".

**Cache discipline.** Track B was checked **before** the run: the FULL-family prompt was 60/60
cached, so halt condition 6 did not fire and no fresh LLM spend occurred.

---

## 6. Limitations

**Track A is synthetic.** The decision-bearing cell sits on generated prose. Track B is real
academic prose, is non-decision-bearing, and inverts the size effect.

**One shot.** `D_edit(384)` is +7/176 — the largest single term at that size, and it will read
to someone as *"it works at 384 and we tested the wrong size."* `p_holm` is 0.615. It is noise,
and **re-testing it on this Track A split is not a fresh test**. That question needs a v1.7 on a
different track or a freshly generated corpus, with its own pre-registration. Stated here so
nobody else has to have the idea and be talked out of it.

**`recall@budget` is new.** It is not comparable to any published number and appears beside none
in this document without this sentence.

**The predictions carry no sealed cell scope** (§1). Scoring them on A-MiniLM is an inference
from the decision rules, labelled HYPOTHESIS.

**What v1.6 does not test:** generation quality, readability, the verbatim guardrail, or any
claim about the formatter other than its effect on retrieval at matched budget.

---

## 7. Consequence, frozen in advance

The KILL consequence rule was written before any value existed and is not negotiable now:

> The white paper's claim is amended to *"better segmentation retrieves better; editing is not
> separately demonstrated at matched retrieval budget."* The formatter's human-readability and
> verbatim-guardrail results are unaffected and stay as written.

**No paper edit and no brief edit has been made.** Applying this to v3 requires authorisation
that has not been given. The bge reversal (§4.2) and the Track B inversion (§4.1) both reach
further than the formatter and further than v1.6 — which is a reason to report them precisely,
not a licence to act on them here.
