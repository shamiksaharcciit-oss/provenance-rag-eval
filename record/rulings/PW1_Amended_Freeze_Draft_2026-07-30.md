# PW-1 — amended freeze draft + check of `Check_PW1_Status_and_Freeze_2026-07-30.md`

**Compiled 2026-07-30. Not stamped.** No arm has been run; no p-value, delta, or classification
exists under any of these definitions. The pre-outcome window is still open.

Your §6 asked for the amended §4 for a final read. It is §4 below. §§1–3 are the check you did
not ask for but which every one of your items had to survive, and three of them did not.

---

## 1. Your blocking items — all three accepted, one with a consequence you did not see

### 1.1 §2.1, the missing fourth scoring — accepted, and it is the strongest item in your check

You are right, and the reason is stronger than "a level is absent". **S2 (own + absorbed, no
inheritance) is the ruler the paper describes.** The paper defends carrying absorbed ranges
explicitly, as de-duplication credit, and says nothing about inheritance anywhere. So the only
scoring that implements the printed methods was the one scoring PW-1 did not have.

The conflation you identify is real and now quantified. Under the corrected figures (§2.1 below),
absorption is 3.27% of Track A's sentence surface but intersects the gold of **63.6% of Track A's
queries**, and Track A carries two of the three applicable cells in the size-matched family. `r`
under S3 would have mixed the documented channel with the undocumented one on the track that
dominates the family. Adopted as the S0–S3 ladder with S2 primary.

### 1.2 §2.2, the omitted composition family — accepted, and it forces §3.2 open

Accepted: the promoted family is **C4-vs-C0 on Track A, both stacks**, as a second primary family,
alongside the size-matched control family.

Your rationale cites Track B C4 at "0.420 vs 0.387". Those are the paper's numbers and they are
**not** in the repo's working directories — see §3.1. They are in the archive, and they do support
your conclusion, so the correction holds; I note the sourcing only because your own §3.7 flags the
same numbers as unlocatable.

**But the promotion interacts fatally with §3.2, and your mootness check missed it** because you
checked §3.2 only against the size-matched family. Here is the promoted family:

| cell | Δ | 95% CI | p_raw | p_holm (own published family) | sig by CI | sig by p_raw | sig by Holm |
|---|---|---|---|---|---|---|---|
| C4−C0, Track A, MiniLM | +0.0568 | [+0.0170, +0.1023] | 0.0205 | **0.10249** | yes | yes | **no** |
| C4−C0, Track A, bge | +0.0455 | [**+0.0000**, +0.0909] | 0.0931 | **0.27927** | **no** (touches 0) | no | no |

**Under Holm, both cells are NOT APPLICABLE and the promoted primary family is empty.** Under raw
p or under CI, exactly one cell is applicable. So the undefined term in branch 1 does not merely
fail to bind — it decides whether the family you are adding exists at all.

For the record, since it bears on how the promotion is framed: the MiniLM Track A composition
cell **does not survive Holm in its own published family** (p_holm 0.10249). Calling it "the
significant composition claim" is right on the raw statistic and wrong on the corrected one. The
promotion is still correct — PW-1 should stress-test what the paper claims — but it should be
frozen knowing the family is *n = 1 applicable cell*, not two.

My recommendation is in §4 under `branch_1_significance`: **gate on significance as the paper
claims it** (raw / CI, which agree on all six cells here), because branch 1 asks "is there a claim
to separate?", and gating on a criterion the paper does not use would make PW-1 test something the
paper does not assert. Your call; it is written so you can invert it with one line.

### 1.3 §2.3, PW1-F1 under-scoped — accepted in full

All three extensions adopted, and the methods point is worse than you stated. The passage says
every unit "carries the character ranges of the original document it derives from". For a
re-chunked formatted unit the ranges are not merely wider than its text — **97.35% of the excess
on Track A and 99.83% on Track B is inheritance**, i.e. ranges of text in *sibling* segments the
unit does not derive from at all. Your (c), the reproducibility framing, is the consequential one
and is now the finding's third clause.

---

## 2. Your non-blocking items

### 2.1 §3.1 — you were right that the figures disagree, and the cause was worse than "computed differently"

Chasing this found **two bugs of mine**, not one inconsistency. Neither published absorbed figure
was the formatter's actual absorbed surface.

1. **Step 0a's 12,591 / 2,919 was a rule-based normalization estimate**, not the formatter's
   behaviour. It deduplicated by text-normalizing every sentence; the path that produced the
   published numbers takes the drop set from the model's `drop` list. Close on these corpora, but
   a different quantity, and it was labelled as the absorbed surface.
2. **My first attempt at the actual figure merged ranges across document boundaries**, treating
   two documents' offsets as one coordinate space and collapsing unrelated intervals. It reported
   5,600 on Track A against a true 12,019 — a 2.1× under-count. I caught it only because it
   disagreed with step 0c, which unions per document.

Canonical figures, now agreeing across both independent paths:

| | actual absorbed, corpus union | share of sentence surface | per-chunk sum | rule-based proxy |
|---|---|---|---|---|
| Track A | **12,019** | **3.27%** | 12,454 | 12,591 |
| Track B | **2,887** | **0.20%** | 2,973 | 2,919 |

Per-chunk ≥ corpus union on both tracks now, as boundary double-counting requires. Your
observation that Track A violated that ordering was correct; it violated it because you were
comparing the per-chunk sum against the *rule-based proxy*, which is neither.

**And one framing error of mine that your item exposed:** I had started reporting a corpus-level
union of *excess*. That quantity is meaningless — a sentence that is excess for chunk 1 is own
text for chunk 2, so the union approaches the whole corpus (96.6% on Track A) and measures
nothing. Width is a per-unit property; the decomposition is per chunk, and only `absorbed` has a
meaningful corpus-level union. Both scripts now say so in place.

### 2.2 §3.2 — specified, and it is **not** moot. See §1.2.

Your mootness check is correct as far as it goes: over the size-matched family, Holm gives
0.0004 / 0.0006 / 0.027 / 0.3423 and branch-1 classifications are identical under raw, CI, or
Holm. It binds decisively on the family §2.2 adds. Both facts are recorded in §4.

### 2.3 §3.3 — accepted, and it changes a label's meaning

Adopted verbatim in substance. Stripping *absorbed* ranges is a stress test — the unit does
represent that content. Stripping *inherited* ranges is **correction** — the chunk does not contain
that text at all. So S2 is not a hostile floor, and a NOT SEPARATED result under S2 says the
effect survives having a defect removed, which is a stronger statement than surviving a handicap.
S3 remains the hostile floor because it also strips the defended channel. Written into §4 as
`arm_semantics` so the labels cannot be read the wrong way later.

### 2.4 §3.4 — accepted, with the numbers corrected

Narrowed. But the persisted assets are different from what you describe, and better:

- `results/per_query.jsonl` — **1,760 rows, Track A only** (10 conditions × 176), not 1,408.
  MiniLM, `run-20260724-174208`.
- `results_v13/per_query.jsonl` — 1,956 rows, both tracks, C0–C5, bge, `run-20260726-191447`.
- `rag-formatter-results.zip` — `per_query.jsonl` for `run-20260724-135411`, MiniLM, **both
  tracks**. This is the run the paper reports.

Each row carries `retrieved_unit_ids` (10 deep), `gold_spans`, `hit@k`, and `top_hit_provenance`
— the actual claimed ranges the run scored with. That last field is a free and strong guard: the
rebuild's `claimed` set can be checked against what the published run used, per query, without
re-running anything. The promoted family is therefore scoreable by exact re-score with **no
embedding and no retrieval**, as you said.

### 2.5 §3.5 — closed

`src/index/embed.py`'s docstring claimed content-hash caching under `cache/emb/`; `encode()` never
writes it. Docstring corrected rather than the cache implemented, and the reason is recorded in
place: changing the embedding path while an analysis depends on reproducing published embeddings
is the wrong time to touch it. Implementing it remains a real improvement, deliberately deferred.

### 2.6 §3.6 — accepted, written into §4 as `guard_1_escalation`

### 2.7 §3.7 — **both claims fail against this repository**

This is the one section I cannot adopt. I think you were reading a different working copy: there
is no `harness/` directory here.

**Claim 1 — "no located artifact set reproduces the paper's Track B condition table."** It
reproduces exactly, in the archive:

> `rag-formatter-results.zip`, `results.json`, `run-20260724-135411`, `all-MiniLM-L6-v2`, Track B:
> **C0 0.3867 · C1 0.3667 · C2 0.3867 · C3 0.3867 · C4 0.4200 · C5 0.4133**

Identical to the printed row. That bundle is the v1.0/v1.1 archive entry — the published run — so
the numbers are where they should be. The four working `results*` directories do not contain a
MiniLM Track B condition run, which is what you found; the archive does, which is what matters.
`ARCHIVE_MANIFEST.md` already lists this bundle as chain entry 1.

**Claim 2 — "`results/results.json` gives C3-nosize 0.733."** No artifact in this repository
reports 0.733 for any ablation. Every located source agrees on **C3-nosize Track A = 0.6989**:
working `results/`, `rag-formatter-results.zip`, and the working snapshot zip. The only 0.7330 in
the repository is in `BUNDLE_MANIFEST.md`, and it is the **v1.4 parent-dilution control** —
parent-scored C2 recall@5, against child-scored 0.4318, the +0.301 inflation figure. A different
quantity from a different experiment.

Nothing here needs tracing before external circulation on that account. If your copy really does
show a divergent `results/`, that is worth resolving separately — but it is not reproducible here.

### 2.8 §3.8 — accepted, and it now opens the freeze file

Adopted as the opening paragraph of §4, with the exposure stated exactly:

Inheritance requires a two-stage pipeline — format, then re-chunk. That is **fmt256, C4, C5 only**.
C0, C1, C2 have width **exactly 1.0000** (`naive.py:41`: the range *is* the substring's own span).
C3, the formatter's own marker-cut pipeline, claims 367,656 characters against 367,729 of sentence
surface on Track A and 1,416,168 against 1,416,240 on Track B — **no inflation**, because a
formatter unit's ranges are its own sentences plus what they absorbed, and nothing else. So parity
with contextual retrieval, the margin over semantic chunking, and all four ablations are untouched.
This is a bounded methods correction, not a threat to the programme.

---

## 3. Corrected step-0 record

Supersedes §2.3 and §2.4 of `PW1_Status_and_Freeze_Package_2026-07-30.md`. Everything else in that
document stands. `results_pw1/step0.json` regenerated.

| | Track A | Track B |
|---|---|---|
| width, orig256, claimed chars per own char | **1.0000** | **1.0000** |
| width, fmt256 | **2.3182** | **2.3574** |
| ratio of ratios | **2.3182** (2.3181 per token) | **2.3574** (2.3551 per token) |
| ranges per fmt256 unit | 51.39 | 25.49 |
| per-chunk claimed / tight / excess | 838,499 / 368,066 / **470,433 (56.10%)** | 3,369,209 / 1,595,310 / **1,773,899 (52.65%)** |
| of that excess: inheritance | **97.35%** | **99.83%** |
| absorbed, corpus union | **12,019 (3.27%)** | **2,887 (0.20%)** |
| C3 claimed vs sentence surface | 367,656 / 367,729 | 1,416,168 / 1,416,240 |
| clean-query retention, narrow `D` | 64/176 = **36.4%** | 145/150 = **96.7%** |
| clean-query retention, wide `D` | 2/176 = **1.1%** | 0/150 = **0.0%** |

Retention figures are unchanged — they were always built from the formatter's actual absorbed
ranges, unioned per document. Arm 1 still does not run inferentially on either track.

§2.7 of the prior document stands with its surface figure corrected to 3.27%: absorption is 3.27%
of Track A's sentence surface and intersects the gold of 63.6% of its queries. The disproportion
is larger than I first reported, not smaller.

---

## 4. AMENDED FREEZE FILE — `posthoc_PW1_provenance_width.json`

For your final read. Not stamped.

```
### opening — scope of the exposure (your §3.8)

scope_of_exposure   "Range inheritance requires a two-stage pipeline: format, then re-chunk. It
                     therefore exists ONLY in fmt256, C4 and C5. C0/C1/C2 have width exactly
                     1.0000 by construction (naive.py:41). C3 — the formatter's own marker-cut
                     pipeline — shows no inflation: claimed 367,656 vs 367,729 chars of sentence
                     surface (Track A), 1,416,168 vs 1,416,240 (Track B). Parity with contextual
                     retrieval, the margin over semantic chunking, and all four ablations are
                     untouched by this finding. This is a bounded methods correction."

### identity

status              "POST-HOC — data already observed; not a chain entry"
frozen_utc          <real UTC timestamp at stamp time — no 00:00:00Z placeholder>
not_a_chain_entry   true
archive_placement   "ARCHIVE_MANIFEST.md, under a heading separate from the five
                     pre-registrations. NOT added to the chain table."

integrity_property  "The subset definitions, arms, metric, families and interpretation rule are
                     frozen before any outcome under them is computed. NOT that the data were
                     unseen. Weaker than the chain's property and labelled as such."

disclosure          "This analysis is post-hoc: the retrieval data it re-scores were observed
                     before it was designed.

                     Step 0 was computed under an earlier version of the instructions and its
                     results changed the arm definitions before any arm was run. Step 0a measured
                     the absorption channel at 3.27% (Track A) and 0.20% (Track B) of sentence
                     surface; step 0c measured a chunk-to-segment inheritance channel at 2.32x /
                     2.36x width, accounting for 97.35% / 99.83% of the excess. The originally
                     specified arm removed only absorption. The scoring ladder was widened to
                     four levels and S2 made primary in response to those measurements.

                     Step 0's own figures were themselves corrected twice before the stamp: a
                     rule-based dedup proxy had been reported as the formatter's absorbed surface,
                     and a helper merged ranges across document boundaries and under-counted
                     Track A by 2.1x. Both are fixed; the corrected figures are above; the
                     erroneous ones are recorded in the results document rather than deleted.

                     Step 0 quantities are properties of the corpora and the gold set, not of any
                     retrieval outcome, and no p-value, delta or classification had been computed
                     on any arm when these definitions were settled."

### the scoring ladder (your §2.1)

scoring_S0          "own + absorbed + inherited — claimed. The published scoring. Supplies
                     delta_full."
scoring_S1          "own + inherited — minus-absorbed. SECONDARY, reported in full so the
                     3.27%/0.20% absorption figure carries a result rather than a descriptive."
scoring_S2          "own + absorbed — minus-inherited. **PRIMARY.** Implements the ruler the
                     paper's methods describe: absorbed ranges retained as de-duplication credit,
                     inheritance removed."
scoring_S3          "own only — minus-both. SECONDARY, the conservative floor."

arm_semantics       "Stripping ABSORBED ranges is a stress test: the unit genuinely represents
                     that content, so S1 and S3 bias against the formatted arm. Stripping
                     INHERITED ranges is CORRECTION: the chunk does not contain that text at all.
                     S2 is therefore not a hostile floor, and a NOT SEPARATED result under S2
                     means the effect survives removal of a defect — a stronger statement than
                     surviving a handicap. Only S3 is a hostile floor."

re_scoring_scope    "S1/S2/S3 re-score the FORMATTED arm only. The unformatted arm's width is
                     exactly 1.0000, so tight == claimed and there is nothing to strip.
                     delta_tight is therefore formatted-corrected minus unformatted-as-published.
                     This is what makes the arms a correction of an asymmetry rather than a
                     symmetric handicap."

arm_1               "Clean-gold subset. DESCRIPTIVE ONLY. Retention measured at step 0: narrow D
                     36.4% (A) / 96.7% (B); wide D 1.1% (A) / 0.0% (B). Below the frozen 60% gate
                     on both tracks under the governing wide D, and on Track A even under the
                     narrow one. Does NOT run inferentially. Counts and descriptive deltas
                     reported. The threshold is not lowered — it was set before the count was
                     known and that is its entire value."

### families (your §2.2)

family_1_primary    "Size-matched control: naive-256 on original vs formatted text, recall@5.
                     4 cells = {all-MiniLM-L6-v2, BAAI/bge-base-en-v1.5} x {Track A, Track B}.
                     Holm over the 4 cells as ONE family, per scoring."
family_2_primary    "Composition: C4 vs C0 on Track A, recall@5, both stacks. 2 cells.
                     Holm over the 2 cells as ONE family, per scoring.
                     Promoted because the composition result is the paper's practical headline and
                     family 1 does not test it. Scoreable by exact re-score of persisted ranked
                     lists — no embedding, no retrieval."
family_secondary    "C4 vs C0 on Track B, labelled secondary, reported separately."

prejudged_cells     "Determined from PUBLISHED numbers before any arm ran, and recorded here so
                     they are not read as post-hoc:
                       family 1, MiniLM/Track B: NOT APPLICABLE. delta_full +0.0267,
                         CI [-0.0133,+0.0667], p 0.3423 — no effect to separate.
                       family 2, bge/Track A: NOT APPLICABLE under every candidate criterion.
                         delta_full +0.0455, CI [+0.0000,+0.0909] — the lower bound is exactly
                         zero, so the CI does not exclude it; p_raw 0.0931.
                     Family 2 therefore has ONE applicable cell (MiniLM/Track A) and family 1 has
                     three. Frozen in the knowledge that family 2 is n=1."

### the significance term (your §3.2, and it is not moot)

branch_1_significance
                    "RECOMMENDED: raw / CI significance as the paper claims it — i.e. the
                     criterion the published tables use. Branch 1 asks whether there is a CLAIM to
                     separate; gating on a criterion the paper does not apply would make PW-1 test
                     something the paper does not assert.

                     Raw-p and CI-excludes-zero agree on all six cells of both families, so the
                     A5 two-procedure defect does not bind here. Holm-within-own-published-family
                     does NOT agree: it would make family 2 EMPTY (p_holm 0.10249 MiniLM/A,
                     0.27927 bge/A) and would gate out the composition claim entirely.

                     Recorded so the choice is visible: the MiniLM/Track A composition cell does
                     NOT survive Holm in its own published family. It is admitted here because the
                     paper claims it, not because it is Holm-significant.

                     Boundary rule, stated before computing: a CI whose bound is exactly 0.0000
                     does NOT exclude zero."

### statistics

method              "Exact sign-flip enumeration over the 2**K assignments of the K discordant
                     pairs (== McNemar exact). K reported for every cell. p_mc_10k retained
                     beside it. Paired deltas with 95% CIs. p to six significant figures."
holm                "Per family, per scoring, as defined above."

### the ratio and the interpretation rule (your §4.1-4.3)

ratio               r = delta_S2 / delta_full        (primary; sign retained, so a sign flip
                                                      gives r < 0 and lands in NOT SEPARATED)
                    r is also reported for S1 and S3 and is descriptive there.
delta_full          "The PUBLISHED point estimate for the cell. Not a value recomputed in the
                     same pass that computes the numerator — that would make r unfalsifiable.
                     Guard 1 requires the reproduction to match the published digit; if it does
                     not, the analysis stops."

interpretation_rule evaluated in this order, first match wins:
  1 NOT APPLICABLE      delta_full not significant per branch_1_significance. Report r
                        descriptively and stop; contributes nothing to the headline.
  2 UNDERPOWERED        the S2 95% CI contains BOTH zero AND delta_full. Report the CI and K;
                        make no separation claim for the cell.
  3 NOT SEPARATED       r < 0.25, OR the S2 CI contains zero.
  4 SEPARATED           r >= 0.75 AND the cell remains significant after Holm within the S2
                        family.
  5 PARTIALLY SEPARATED everything else (in practice 0.25 <= r < 0.75, or r >= 0.75 with
                        significance lost).

thresholds_note     "0.75 and 0.25 are conventional round numbers chosen without reference to any
                     observed value. There is no principled basis on which to prefer 0.7 or 0.8,
                     and inventing one after the fact would be worse than admitting the choice is
                     conventional."

aggregation         "Per family: the headline classification is the LEAST FAVOURABLE label among
                     cells that are applicable and powered, ordered
                     NOT SEPARATED < PARTIALLY SEPARATED < SEPARATED. If no cell in a family is
                     both applicable and powered, that family's headline is UNDERPOWERED. The
                     two primary families are reported separately and are NOT merged into a
                     single headline. All cells are reported individually regardless."

one_shot_rule       "Run once, reported whatever it says. No tuning of the subset definition, k,
                     scoring, or family after seeing a result."

### guards

guard_1             "Reproduce every published level exactly before computing anything new:
                     0.5682/0.7216, 0.3533/0.3800, 0.6080/0.7557, 0.3600/0.4267 (family 1);
                     C0/C4 Track A both stacks (family 2). State whether reproduction was by
                     re-score of persisted ranked lists or by re-run under seed 1337 /
                     candidate_pool 50 / k_rrf 60, per family."
guard_1_escalation  "If reproduce-before-compute fails to regenerate a published number, that is a
                     PAPER-LEVEL escalation, not a PW-1 blocker. STOP and report. Do not attempt
                     repairs inside a frozen analysis."
guard_2             "NC-A and NC-B, both shipped in tests/:
                       NC-A  gold only inside an absorbed range:  S0 hit, S1 miss, S2 HIT,
                             S3 miss.
                       NC-B  gold only inside an inherited range: S0 hit, S1 HIT, S2 miss,
                             S3 miss.
                     NC-B is what separates 'the tight arm is implemented' from 'asserted'. Its
                     S1 expectation is a HIT: if S1 misses there, S1 is over-stripping and its
                     numbers are wrong. Likewise NC-A's S2 expectation is a HIT. If either
                     control misbehaves, STOP — nothing downstream would mean anything."
guard_3             "scripts/ and tests/ for this analysis ship in the bundle."
guard_4             "The rebuild asserts against production per document: identical chunk count,
                     unit_id, text, and claimed ranges. Passed on 45 + 60 documents, 235 + 1,074
                     chunks. Additionally, `top_hit_provenance` in the persisted per-query rows
                     records the ranges the published run actually scored with, and the rebuild's
                     claimed set is checked against it per query."

### findings recorded before any arm

PW1-F1              "(a) WRONG CHANNEL AND WRONG STAGE. The paper's §11 attributes provenance
                     width to absorbed duplicate ranges. Absorption is 3.27% (Track A) / 0.20%
                     (Track B) of sentence surface; width is 2.32x / 2.36x and 97.35% / 99.83% of
                     the excess is chunk-to-segment inheritance. The formatter introduces no width
                     at all — C3 claims 367,656 vs 367,729 chars of sentence surface. The
                     re-chunking stage introduces it.

                     (b) THE METHODS DESCRIPTION DOES NOT MATCH THE IMPLEMENTATION. The methods
                     passage states that every unit 'carries the character ranges of the original
                     document it derives from'. A re-chunked formatted unit carries ranges of text
                     in SIBLING segments it does not derive from — 97.35% of its excess surface on
                     Track A.

                     (c) THIS IS A REPRODUCIBILITY GAP, NOT ONLY A THREAT TO VALIDITY. A reader
                     implementing the paper's own description of the ruler would not reproduce the
                     published numbers for any two-stage condition.

                     Holds whatever the arms return. The §11 and methods rewrite waits."

PW1-F2              "STEP 0's OWN FIGURES WERE WRONG TWICE, both caught before the stamp. A
                     rule-based dedup proxy was reported as the formatter's absorbed surface
                     (12,591 vs the actual 12,019 on Track A), and a helper merged ranges across
                     document boundaries, under-counting Track A by 2.1x (5,600 vs 12,019). Both
                     found by chasing a reviewer's observation that two reported figures could not
                     both be right. Recorded because a corrected number with no record of the
                     correction is indistinguishable from a number that was always right."
```

---

## 5. What I need

1. **Confirm §4, or send edits.** Not stamped until you do.
2. **Confirm or invert `branch_1_significance`** (§1.2). It decides whether family 2 exists. My
   recommendation and its cost are both stated; inverting it is one line and empties family 2.
3. **§2.7 needs no action from me** — but if your copy genuinely shows a divergent `results/` or a
   `harness/` tree, that is worth resolving on your side, because it is not reproducible here.

Unchanged and not being done: no paper edit; no touching of any frozen pre-registration, published
number, or existing bundle; no redesigned small-to-big experiment; no re-run of embeddings or
corpora beyond what guard 1 requires.
