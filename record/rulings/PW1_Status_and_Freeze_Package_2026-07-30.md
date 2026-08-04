# PW-1 — status, full step-0 record, and the freeze package awaiting approval

**Compiled 2026-07-30. Author: agent. For: reviewer.**
**State: PW-1 step 1 complete (commit `78189d5`). No arm has been run.**
No p-value, delta, or classification exists on any arm. Nothing below waits on anything except
your go-ahead on §6.

---

## 1. Where the whole programme stands

| Work | State | Commit |
|---|---|---|
| v1.5 / M7 small-to-big | **REJECT_HARM**, published, bundled | `dbef489`, `a290013` |
| v1.5 corrections (handoff 2026-07-29, items 1–9) | **Closed** | `45b69ed` |
| Four residual bundle items (your §7) | **Closed** | `78189d5` |
| PW-1 step 0a (surface) | **Done, reported** | `18b84f4` |
| PW-1 step 0c + §4.4 retention + PW1-F1 | **Done, reported** | `78189d5` |
| PW-1 freeze file | **Drafted below, not stamped** | — |
| PW-1 NC-A / NC-B, guard 1, arms | **Not started** | — |
| White paper §11 rewrite | **Deferred by §7** | — |
| Redesigned small-to-big experiment | **Not started, per instruction** | — |

Artifacts: `Results_PW1_ProvenanceWidth.md`, `results_pw1/step0.json`,
`src/pw1/tight_provenance.py`, `scripts/pw1_step0_surface.py`, `scripts/pw1_step0c.py`.

---

## 2. The complete step-0 record

### 2.1 The width statistic (§3a), stated precisely

Per corpus, per track: **the union of each unit's `source_ranges` in original-document
characters, summed over units, divided by the units' own size.** Both denominators are given
because the step-0a figure used the second.

| Track A | units | claimed chars | own chars | own tokens | per own **token** | per own **char** | ranges/unit |
|---|---|---|---|---|---|---|---|
| orig256 | 238 | 378,041 | 378,041 | 54,886 | 6.8877 | **1.0000** | 1.00 |
| fmt256 | 235 | 838,499 | 361,707 | 52,517 | 15.9662 | **2.3182** | 51.39 |
| **ratio of ratios** | | | | | **2.3181** | **2.3182** | |

| Track B | units | claimed chars | own chars | own tokens | per own **token** | per own **char** | ranges/unit |
|---|---|---|---|---|---|---|---|
| orig256 | 1,072 | 1,430,795 | 1,430,795 | 267,767 | 5.3434 | **1.0000** | 1.00 |
| fmt256 | 1,074 | 3,369,209 | 1,429,176 | 267,726 | 12.5845 | **2.3574** | 25.49 |
| **ratio of ratios** | | | | | **2.3551** | **2.3574** | |

The unformatted arm's per-own-char width is **exactly 1.0000** — §0a's by-construction check
passing. The naive chunker's `source_ranges` *is* the substring's own span
([naive.py:41](src/chunkers/naive.py#L41)).

### 2.2 §3b — the asymmetry hypothesis fails, and structurally

The hypothesis was that chunk-to-segment inheritance is a harness property, so it should inflate
both arms and cancel in a paired comparison. **Ratio of ratios is 2.32 / 2.36, not ~1.0.**

The reason is the pipeline shape, not a bug or a choice:

- **Unformatted arm — one stage.** Chunk the raw document. A chunk's provenance is its own
  character span. Width 1.0000 exactly.
- **Formatted arm — two stages.** Format into segments, then re-chunk the formatted text. A
  256-token chunk inherits the *entire* `source_ranges` of every ~384-token segment it overlaps
  ([formatted.py:86-94](src/chunkers/formatted.py#L86-L94)) — hence 51 ranges on one chunk.

**There is nothing on the unformatted side for the channel to act on.** The threat is asymmetric
by construction. Arm 2b affects only the formatted arm; on the unformatted arm
`tight == claimed` by definition.

### 2.3 Decomposition — the formatter is not the culprit; re-chunking is

| fmt256, summed per chunk | claimed | tight (own sentences) | excess = claimed − tight | of excess, absorbed |
|---|---|---|---|---|
| Track A | 838,499 | 368,066 | **470,433 = 56.1% of claimed** | 12,454 → **2.6%** |
| Track B | 3,369,209 | 1,595,310 | **1,773,899 = 52.7% of claimed** | 2,973 → **0.17%** |

Over **97%** of the excess is inheritance, not absorption.

At the **formatter** level there is no inflation at all: C3 units claim 367,656 chars against
367,729 of own-plus-absorbed sentence surface on Track A — agreeing to under 0.02%. Track B:
1,416,168 against 1,416,240.

*Note on the arithmetic:* per-chunk sums double-count sentences straddling a chunk boundary, which
is why Track A's tight total (368,066) slightly exceeds C3's claimed (367,656). It is the correct
per-unit quantity for a per-unit width statistic; the corpus-level figures are the C3 ones.

### 2.4 Absorption in isolation (step 0a)

| | absorbed surface | share of sentence surface |
|---|---|---|
| Track A | 12,591 chars | **3.42%** |
| Track B | 2,919 chars | **0.21%** |

### 2.5 §4.4 — clean-gold retention under both definitions of `D`

`D` = ranges a unit claims but does not itself cover. A gold span is clean if it does not
intersect `D`; a query is clean if all of its gold spans are.

| clean-query retention | narrow `D` (absorbed only) | wide `D` (absorbed + inherited) |
|---|---|---|
| Track A (of 176) | **64 = 36.4%** — below gate | **2 = 1.1%** — below gate |
| Track B (of 150) | **145 = 96.7%** — passes | **0 = 0.0%** — below gate |

**Under the frozen 60% go/no-go, Arm 1 does not run inferentially on either track.** Track A fails
it even under the narrow definition. Counts and descriptive deltas will be reported; no
inferential claim. The threshold is not being lowered.

### 2.6 PW1-F1, recorded before any arm

The paper's §11 attributes provenance width to absorbed duplicate ranges. **Absorption is
0.21–3.42% of surface; the width is 2.3× and comes from chunk-to-segment inheritance.** The
mechanism named in print is not the mechanism that dominates — and it is not even the right
*stage*: the formatter introduces no width, the re-chunking does.

This holds whatever the arms return. The §11 rewrite waits (§7).

### 2.7 A correction to my own step-0a report

I called absorption "negligible in size" and implied Arm 2a would be near-inert. **That inference
was wrong on Track A.** 3.42% of surface intersects the gold of **63.6%** of Track A's queries. A
channel's share of *surface* does not predict its share of *gold* — on a synthetic corpus built
with deliberate restatements, the restated sentences are exactly the answer-bearing ones. Arm 2a
may move the Track A cells materially. It remains near-inert on Track B (0.21% surface, 3.3% of
queries touched).

This also means your §2.2 rejection of option (c) was right for a reason neither of us had:
stopping at step 0 would have rested on precisely the surface-share inference these counts refute.

### 2.8 Correctness of the rebuild

`src/pw1/tight_provenance.py` re-derives chunk boundaries rather than importing them, and
therefore **asserts against production**: identical chunk count, `unit_id`, text, and claimed
ranges, per document. Passed on **all 45 Track A and all 60 Track B documents, 235 + 1,074
chunks.** Had it not, every number above would be void.

Right-sizing groups sentences and never drops them, so `own ∪ absorbed` is provably the complete
original surface and the stripping arithmetic is sound.

### 2.9 Two harness facts bearing on the arms

- **No ranked lists or per-query vectors are persisted for the size-matched control.**
  `results_v13/results.json` carries `{original_256: 0.608, formatted_256: 0.7557}` and nothing
  more; [common_size_ci.py](scripts/common_size_ci.py) states that `run.py` discards the vectors.
  Guard 1 will therefore be satisfied by **re-running retrieval**, the option §6.1 anticipates —
  not by re-scoring persisted lists.
- **`Embedder.encode()` does not cache.** [embed.py:7](src/index/embed.py#L7) claims "Embeddings
  are cached by content hash under cache/emb/ for idempotency (§11)"; `cache/emb` is created and
  never written, and is empty. Both models are in the local HuggingFace cache, so the arms cost
  local compute only — no downloads, no API calls, no new corpora.

---

## 3. One primary cell is already NOT APPLICABLE, from published numbers alone

The four primary cells and their published full-set values:

| # | Embedder | Track | n | orig256 | fmt256 | `delta_full` | 95% CI | p | significant? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | all-MiniLM-L6-v2 | A | 176 | 0.5682 | 0.7216 | **+0.1534** | [+0.0795, +0.2273] | 0.0002 | yes |
| 2 | all-MiniLM-L6-v2 | B | 150 | 0.3533 | 0.3800 | **+0.0267** | [−0.0133, +0.0667] | 0.3423 | **no** |
| 3 | BAAI/bge-base-en-v1.5 | A | 176 | 0.6080 | 0.7557 | **+0.1477** | [+0.0795, +0.2159] | 0.0001 | yes |
| 4 | BAAI/bge-base-en-v1.5 | B | 150 | 0.3600 | 0.4267 | **+0.0667** | [+0.0200, +0.1133] | 0.0135 | yes |

**Cell 2 lands in §4.2 branch 1 (NOT APPLICABLE) before any arm runs** — `delta_full` is not
significant, so there is no effect to separate. Determinable now, from published numbers, which is
the right time to say it. Its `r` will be reported descriptively and it contributes nothing to the
headline.

So the headline rests on **three** applicable cells: A/MiniLM, A/bge, B/bge. Worth noting that
Track A carries two of the three, and Track A is the track where Arm 2a is *not* inert (§2.7).

---

## 4. The freeze file, drafted and ready to stamp

To be written as `posthoc_PW1_provenance_width.json`. Contents below in full, so you can object to
any clause before it is sealed rather than after.

```
status                  "POST-HOC — data already observed; not a chain entry"
frozen_utc              <real timestamp at stamp time; no 00:00:00Z placeholders>
not_a_chain_entry       true
archive_placement       "ARCHIVE_MANIFEST.md, under a heading separate from the five
                         pre-registrations. NOT added to the chain table."

integrity_property      "The subset definitions, arms, metric, family and interpretation rule are
                         frozen before any outcome under them is computed. NOT that the data were
                         unseen. Weaker than the chain's property and labelled as such."

disclosure              <the §6 paragraph verbatim, including: step 0 was computed under an
                         earlier version of the instructions and changed the arm definitions
                         before any arm ran; step 0a measured absorption at 0.21–3.42%; step 0c
                         measured the larger inheritance channel; Arm 2b was added and made
                         primary in response; no p-value, delta or classification had been
                         computed on any arm at that time>

arms
  arm_2b   PRIMARY      "Each chunk's ranges restricted to the original spans of exactly the
                         sentences its own text covers. Removes absorption AND chunk-to-segment
                         inheritance. Affects the formatted arm only; on the unformatted arm
                         tight == claimed by construction."
  arm_2a   SECONDARY    "Each unit's source_ranges restricted to the range its own retained text
                         occupies. Removes absorption only. Reported in full."
  arm_1    DESCRIPTIVE  "Clean-gold subset. Retention measured at step 0: narrow D 36.4% (A) /
                         96.7% (B); wide D 1.1% (A) / 0.0% (B). Below the frozen 60% gate on
                         both tracks under the governing wide D, and on Track A even under the
                         narrow one. Does NOT run inferentially. Counts and descriptive deltas
                         reported. Threshold not lowered."

primary_cells           4 — {MiniLM, bge} x {Track A, Track B}, 256-token cutter, recall@5
cell_2_prejudged        "MiniLM/Track B is NOT APPLICABLE (branch 1): delta_full p=0.3423,
                         CI includes zero. Determined from published numbers before any arm."
holm_family             "the four primary cells as ONE family, per arm"
statistics              "exact sign-flip enumeration over 2**K; K reported for every cell;
                         p_mc_10k retained beside it; paired deltas with 95% CIs;
                         p to six significant figures"

ratio                   r = delta_tight / delta_full        (Arm 2b point estimate over the
                                                             published full-set point estimate,
                                                             same cell, same metric, sign retained)

interpretation_rule     evaluated in this order, first match wins:
  1 NOT APPLICABLE      delta_full not significant under the published analysis. Report r
                        descriptively, stop, contributes nothing to the headline.
  2 UNDERPOWERED        the Arm 2b 95% CI contains BOTH zero AND delta_full. Report CI and K,
                        make no separation claim for the cell.
  3 NOT SEPARATED       r < 0.25, OR the Arm 2b CI contains zero.
  4 SEPARATED           r >= 0.75 AND the cell remains significant after Holm within the
                        Arm 2b family.
  5 PARTIALLY SEPARATED everything else (in practice 0.25 <= r < 0.75, or r >= 0.75 with
                        significance lost).

thresholds_note         "0.75 and 0.25 are conventional round numbers chosen without reference to
                         any observed value. There is no principled basis on which to prefer 0.7
                         or 0.8, and inventing one after the fact would be worse than admitting
                         the choice is conventional."

aggregation             "The headline classification is the LEAST FAVOURABLE label among primary
                         cells that are applicable and powered, ordered
                         NOT SEPARATED < PARTIALLY SEPARATED < SEPARATED. If no primary cell is
                         both applicable and powered, the headline is UNDERPOWERED. All four
                         cells are reported individually regardless."

secondary               "C4-vs-C0 pipeline comparison on Track B, same treatment, labelled
                         secondary, reported separately."

one_shot_rule           "Run once, reported whatever it says. No tuning of the subset definition,
                         k, or arm after seeing a result."

guards                  1 reproduce published baselines exactly before computing anything new
                        2 NC-A and NC-B, both shipped in tests/
                        3 scripts/ and tests/ ship in the bundle

findings_recorded_pre_arm
  PW1-F1                <§2.6 above, with the 0a and 0c figures attached>
```

---

## 5. Exactly what happens next, in order

**Step 2 — stamp the freeze file.** §4 above, with a real UTC timestamp. Nothing computed.

**Step 3 — NC-A and NC-B.** Both in `tests/test_pw1_range_stripping.py`.

| control | gold span lies only in… | ordinary scoring | Arm 2a | Arm 2b |
|---|---|---|---|---|
| **NC-A** | an absorbed range | hit | **miss** | **miss** |
| **NC-B** | an inherited range — a sentence of the parent segment the chunk's own text does not cover | hit | **hit** | **miss** |

NC-B is the one that separates "the tight arm is implemented" from "the tight arm is asserted".
Its Arm 2a expectation is a *hit*: if 2a reports a miss there, 2a is over-stripping and its
numbers are wrong. If either control misbehaves I stop and report; nothing downstream would mean
anything.

**Step 4 — guard 1 reproduction.** Re-run retrieval under seed 1337, `candidate_pool = 50`,
`k_rrf = 60`, both embedders, both tracks, both corpora, and show all eight published levels
reproduce to the published digit (0.5682 / 0.7216, 0.3533 / 0.3800, 0.6080 / 0.7557, 0.3600 /
0.4267). **If any does not reproduce exactly I stop and report rather than proceeding on a corpus
that is not the published one.** I will state in the results document that reproduction was by
re-run, not by re-scoring persisted lists, and why.

**Step 5 — the arms.** One build, one embedding pass, one retrieval per cell, **three scorings**
(claimed / own-only / tight) off the same ranked lists. The arms then differ *only* in the scorer,
which is a stronger guarantee than three retrieval runs and a third of the compute. Then Arm 2b,
Arm 2a, Arm 1 descriptive.

**Step 6 — report, then bundle.** Results document, freeze file with computed values, code,
per-file SHA-256 manifest, real timestamps.

### Execution precautions, from v1.5's failures

- **Per-cell persistence** (`results.json`, `per_query.jsonl`, `vectors.json` written after every
  cell) and **process isolation per embedder** — template §A2/§A2b. v1.5 lost six completed cells
  to a write-at-end plus a segfault, and the segfaults proved transient rather than deterministic.
- **Exit status checked directly**, not through a pipe into `grep` — template §A1.
- Vectors persisted so Holm can be recomputed across the family from a partial run.
- Compute estimate: 8 corpus embeddings + 2 query sets across 2 models, local only. Track B's
  fmt256 corpus is ~1,074 units. Expect tens of minutes, with segfault-retry overhead.

---

## 6. What I need from you

**Blocking — one thing:**

1. **Go-ahead to stamp §4 as written**, or your edits to it. Everything else is ready; nothing
   proceeds until the file is sealed, because sealing after computing would forfeit the only
   integrity property this analysis has.

**Two clauses I want on the record before sealing, because they are decisions and I do not want to
be the one who made them silently:**

2. **`delta_full` is the *published* value, not the reproduced one.** The ratio's denominator is
   fixed to the number in print (§3 table). Guard 1 requires the reproduction to match it exactly;
   if it does, the two are the same number and nothing turns on the choice. If it does not, I stop
   — so the denominator is never a reproduced-but-different value. Say if you want the reproduced
   value instead.

3. **Arm 2b re-scores the formatted arm only.** On the unformatted arm `tight == claimed` by
   construction (width exactly 1.0000), so there is nothing to strip. `delta_tight` is therefore
   *formatted-tight minus unformatted-as-published*. This is what makes the arm a correction of an
   asymmetry rather than a symmetric handicap — but it should be stated in the freeze file so no
   later reader assumes both arms were re-scored.

**Not blocking, flagged for your visibility:**

4. PW1-F1 sharpens your §2.3: §11 names not just the wrong channel but the wrong **stage** — the
   formatter introduces no width; re-chunking does. The eventual §11 rewrite will need to say
   that, and it is a different sentence from the one you anticipated.

5. §2.7's correction means **Arm 2a is a live measurement on Track A**, not the formality both of
   us expected. If Arm 2a moves Track A materially while Arm 2b moves it further, the two arms
   will decompose the width into its parts, which is more informative than either alone.

**Not being done, per instruction:** no paper edit; no touching of any frozen pre-registration,
published number, or existing bundle; no redesigned small-to-big experiment; no re-run of
embeddings or corpora beyond what guard 1 explicitly requires and §2.9 explains is unavoidable.
