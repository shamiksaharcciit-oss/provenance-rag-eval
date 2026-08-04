# `posthoc_PW1_provenance_width.json` — freeze text for confirmation

**Work order A1: this is the amendment itself, verbatim, not a summary of it.**
**NOT STAMPED.** `frozen_utc` is the only field left open; it is filled with a real UTC timestamp
at stamp time. No arm has been run. No p-value, delta, or classification exists under any
definition below.

Every A-item is folded in. Where a work-order instruction could not be carried out exactly as
written, the text says so in place rather than silently substituting — see `at_risk_guard_1` (A8)
and `PW1-F3` (A3).

---

```
################################################################################
# 0. SCOPE OF THE EXPOSURE  (work order A8 of the previous round; §3.8)
################################################################################

scope_of_exposure
    "Range inheritance requires a two-stage pipeline: format, then re-chunk. It therefore exists
     ONLY in fmt256, C4 and C5. C0/C1/C2 have width exactly 1.0000 by construction — the naive
     chunker's source_ranges IS the substring's own span (naive.py:41). C3, the formatter's own
     marker-cut pipeline, shows no NET inflation at corpus level: claimed 367,656 vs 367,729
     characters of sentence surface (Track A), 1,416,168 vs 1,416,240 (Track B).

     Consequently: parity with contextual retrieval, the margin over semantic chunking, and all
     four ablations are untouched by this finding. This is a bounded methods correction, not a
     threat to the programme."

################################################################################
# 1. IDENTITY AND INTEGRITY
################################################################################

status              "POST-HOC — data already observed; not a chain entry"
frozen_utc          <real UTC timestamp at stamp time; no 00:00:00Z placeholder>
not_a_chain_entry   true
archive_placement   "ARCHIVE_MANIFEST.md, under a heading separate from the five
                     pre-registrations. NOT added to the chain table."

integrity_property
    "The subset definitions, arms, metric, families and interpretation rule are frozen before any
     outcome under them is computed. NOT that the data were unseen. Weaker than the chain's
     property and labelled as such."

pre_stamp_classifications_are_legitimate          # work order A6
    "Six cells are classified under branch 1 in §5 before this file is sealed. This is
     legitimate and not a post-hoc selection: every branch-1 input is a PRE-EXISTING PUBLISHED
     quantity — delta_full, its CI, and its raw p — which this freeze FIXES rather than computes.
     No PW-1-computed quantity enters any branch-1 classification. The only new arithmetic is
     Holm within the declared PW-1 family, which is a deterministic function of the published
     raw p-values and of the family sizes declared in §4, both fixed here before any arm runs."

disclosure
    "This analysis is post-hoc: the retrieval data it re-scores were observed before it was
     designed.

     Step 0 was computed under an earlier version of the instructions and its results changed the
     arm definitions before any arm was run. Step 0a measured the absorption channel at 3.27%
     (Track A) and 0.20% (Track B) of sentence surface; step 0c measured a chunk-to-segment
     inheritance channel accounting for 97.35% / 99.83% of the excess. The originally specified
     arm removed only absorption. The scoring ladder was widened to four levels and S2 made
     primary in response to those measurements.

     Step 0's own figures were themselves corrected three times before the stamp: a rule-based
     dedup proxy had been reported as the formatter's absorbed surface; a helper merged ranges
     across document boundaries and under-counted Track A by 2.1x; and a corpus-level union of
     'excess' was briefly reported, which measures nothing because a sentence that is excess for
     one chunk is own text for the next. All three are fixed, the corrected figures are in §2,
     and the erroneous ones are recorded in PW1-F2 rather than deleted.

     Step 0 quantities are properties of the corpora and the gold set, not of any retrieval
     outcome, and no p-value, delta or classification had been computed on any arm when these
     definitions were settled."

################################################################################
# 2. WIDTH STATISTICS — FOUR NAMED QUANTITIES  (work order A4)
################################################################################

width_statistics_are_four_not_one
    "Any statement of the form 'the width is 2.3x' must name which quantity it refers to. On
     these corpora they range from 2.11 to 3.09. Definitions, all with claimed surface as the
     numerator:

       W_index_char   aggregate: total claimed surface / total own INDEXED characters.
                      THE §3a STATISTIC and the basis of the ratio of ratios.
       W_index_token  aggregate: total claimed surface / total own indexed tokens.
       W_index_mean   the per-UNIT MEAN of (claimed / own chars). A mean of ratios, so it is not
                      the aggregate; reported separately, never conflated with it.
       W_cover        aggregate: total claimed surface / total surface the units actually COVER
                      (their tight ranges). Equals 1/(1 - excess_share) and is the quantity the
                      excess percentages imply."

width_measured
    Track A   orig256:  W_index_char 1.0000  W_index_token 6.8877  W_index_mean 1.0000  W_cover 1.0000
              fmt256:   W_index_char 2.3182  W_index_token 15.9662 W_index_mean 3.0935  W_cover 2.2781
              ranges per fmt256 unit 51.39
    Track B   orig256:  W_index_char 1.0000  W_index_token 5.3434  W_index_mean 1.0000  W_cover 1.0000
              fmt256:   W_index_char 2.3574  W_index_token 12.5845 W_index_mean 2.4793  W_cover 2.1119
              ranges per fmt256 unit 25.49

    "orig256 is exactly 1.0000 on every char-denominated statistic by construction, so each
     ratio of ratios equals the fmt256 value itself."

pw1_f1_refers_to    "W_index_char — 2.3182 (Track A) / 2.3574 (Track B). Where PW1-F1 states a
                     range rather than a single figure it spans W_cover (2.11) to W_index_mean
                     (3.09)."

surface_decomposition
    "Width is a PER-UNIT property, so the decomposition is per chunk:
       Track A  claimed 838,499   tight 368,066   excess 470,433 = 56.10% of claimed
       Track B  claimed 3,369,209 tight 1,595,310 excess 1,773,899 = 52.65% of claimed
     Of that excess, inheritance is 97.35% (Track A) / 99.83% (Track B).

     `excess` has NO meaningful corpus-level union — a sentence that is excess for one chunk is
     own text for the next, so unioning it reaches 96.6% of the corpus and measures nothing.
     `absorbed` IS a corpus-level surface: 12,019 chars = 3.27% of sentence surface (Track A),
     2,887 = 0.20% (Track B), unioned per document."

################################################################################
# 3. THE SCORING LADDER
################################################################################

scoring_S0   "own + absorbed + inherited — CLAIMED. The published scoring. Supplies delta_full."
scoring_S1   "own + inherited — minus-absorbed. SECONDARY, reported in full so the 3.27%/0.20%
              absorption figure carries a result rather than remaining a descriptive."
scoring_S2   "own + absorbed — minus-inherited. **PRIMARY.** Implements the ruler the paper's
              methods describe: absorbed ranges retained as de-duplication credit, inheritance
              removed."
scoring_S3   "own only — minus-both. SECONDARY, the conservative floor."

arm_semantics
    "Stripping ABSORBED ranges is a stress test: the unit genuinely represents that content, so
     S1 and S3 bias against the formatted arm. Stripping INHERITED ranges is CORRECTION: the
     chunk does not contain that text at all. S2 is therefore NOT a hostile floor, and a
     NOT SEPARATED result under S2 means the effect survives removal of a defect — a stronger
     statement than surviving a handicap. Only S3 is a hostile floor."

re_scoring_scope
    "S1/S2/S3 re-score the FORMATTED arm only. The unformatted arm's width is exactly 1.0000, so
     tight == claimed and there is nothing to strip. delta_corrected is therefore
     formatted-corrected minus unformatted-as-published. This is what makes the arms a correction
     of an asymmetry rather than a symmetric handicap."

arm_1_clean_gold
    "DESCRIPTIVE ONLY. Retention measured at step 0: narrow D 36.4% (A) / 96.7% (B); wide D 1.1%
     (A) / 0.0% (B). Below the frozen 60% gate on both tracks under the governing wide D, and on
     Track A even under the narrow one. Does NOT run inferentially. Counts and descriptive deltas
     are reported. The threshold is NOT lowered — it was set before the count was known and that
     is its entire value."

################################################################################
# 4. FAMILIES
################################################################################

family_1_primary
    "Size-matched control: naive-256 on ORIGINAL vs FORMATTED text, recall@5.
     4 cells = {all-MiniLM-L6-v2, BAAI/bge-base-en-v1.5} x {Track A, Track B}.
     Holm over the 4 cells as ONE family, per scoring."

family_2_primary
    "Composition: C4 vs C0 on Track A, recall@5, both stacks. 2 cells.
     Holm over the 2 cells as ONE family, per scoring.
     Promoted because the composition result is the paper's practical headline and family 1 does
     not test it. Scoreable by exact re-score of persisted ranked lists — no embedding, no
     retrieval."

family_secondary
    "C4 vs C0 on Track B, labelled secondary, reported separately."

descriptive_companion_cells          # work order A9
    "Cells that are NOT APPLICABLE under branch 1 are still re-scored and their r and CI reported
     DESCRIPTIVELY, clearly marked as not entering any inferential family and not contributing to
     any headline. This is specified because family 2 has n = 1 applicable cell: with a single
     inferential cell, a corroborating direction on the record is worth having. It applies to
     family 2's bge/Track A cell and family 1's MiniLM/Track B cell."

################################################################################
# 5. BRANCH-1 SIGNIFICANCE, AND THE CELLS IT CLASSIFIES  (work order A2)
################################################################################

branch_1_significance = "Holm within the declared PW-1 family"

branch_1_significance_rationale
    "Applied to BOTH families. The published `p_holm` values must NOT be used: they are Holm over
     each run's own six-member pairwise family
     {C3_vs_C2, C3_vs_C1, C3_vs_C0, C5_vs_C2, C4_vs_C0, C5_vs_C3},
     verified by recomputation — raw 0.02050 x 5 = 0.10250 and 0.09309 x 3 = 0.27927. That is a
     multiplicity imported from outside PW-1 and declared nowhere in it. Family 1's published
     p_holm happens already to be Holm within family 1 (raw 0.0001/0.0002/0.0135/0.3423 x
     (4,3,2,1) reproduces 0.0004/0.0006/0.027/0.3423 exactly); family 2's is not. That
     inconsistency was the real defect, and raw-versus-adjusted was downstream of it."

criterion_is_not_load_bearing
    "Raw p < 0.05, CI-excludes-zero, and Holm-within-family AGREE ON ALL SIX CELLS of both
     families. Verified cell by cell. The criterion is therefore recorded for completeness and
     determines nothing here."

boundary_rule
    "A CI whose bound is exactly 0.0000 does NOT exclude zero. Stated before computing because
     family 2's bge/Track A published CI is [+0.0000, +0.0909]."

branch_1_classifications          # fixed by this freeze; see pre_stamp_classifications_are_legitimate
    family 1:
      MiniLM / Track A   delta_full +0.1534  CI [+0.0795,+0.2273]  p_raw 0.00020  p_holm 0.00060  APPLICABLE
      MiniLM / Track B   delta_full +0.0267  CI [-0.0133,+0.0667]  p_raw 0.34227  p_holm 0.34227  NOT APPLICABLE
      bge    / Track A   delta_full +0.1477  CI [+0.0795,+0.2159]  p_raw 0.00010  p_holm 0.00040  APPLICABLE
      bge    / Track B   delta_full +0.0667  CI [+0.0200,+0.1133]  p_raw 0.01350  p_holm 0.02700  APPLICABLE
    family 2:
      MiniLM / Track A   delta_full +0.0568  CI [+0.0170,+0.1023]  p_raw 0.02050  p_holm 0.04100  APPLICABLE
      bge    / Track A   delta_full +0.0455  CI [+0.0000,+0.0909]  p_raw 0.09309  p_holm 0.09309  NOT APPLICABLE

    "Family 1 has THREE applicable cells. Family 2 has ONE. Frozen in that knowledge."

################################################################################
# 6. STATISTICS
################################################################################

method   "Exact sign-flip enumeration over the 2**K assignments of the K discordant pairs
          (== McNemar exact). K reported for every cell. p_mc_10k retained beside it. Paired
          deltas with 95% CIs. p to six significant figures."
holm     "Per family, per scoring, as defined in §4. Never imported from a published run."

################################################################################
# 7. THE RATIO AND THE INTERPRETATION RULE
################################################################################

ratio        r = delta_S2 / delta_full        (primary; sign retained, so a sign flip gives
                                               r < 0 and lands in NOT SEPARATED)
             r is also reported for S1 and S3 and is descriptive there.

delta_full   "The PUBLISHED point estimate for the cell. NOT a value recomputed in the same pass
              that computes the numerator — that would make r unfalsifiable. Guard 1 requires the
              reproduction to match the published digit; if it does not, the analysis stops."

r_upper_bound_is_a_HALT          # work order A7
    "r <= 1.0 is a HALT, not a reported value, at the same tier as NC-A and NC-B. Removing ranges
     can only turn a hit into a miss, never the reverse, and the unformatted arm has nothing to
     strip, so delta_S2 <= delta_full BY CONSTRUCTION. r > 1 is a defect in the scoring — ranges
     being added rather than removed, or a mismatched cell pairing — not a finding about the
     corpus. Asserted in code: src/pw1/interpret.py::retention_ratio raises RatioExceedsOne, and
     the classifier cannot be used to bypass it. Demonstrated failing in
     tests/test_pw1_interpret.py. A structural invariant checked only by a human reading a table
     is not checked. Float slack is 1e-9 and is not a tolerance for real overshoot."

interpretation_rule    evaluated in this order, FIRST MATCH WINS:
  1 NOT APPLICABLE       delta_full not significant per branch_1_significance. Report r
                         descriptively and stop; contributes nothing to the headline.
  2 UNDERPOWERED         the S2 95% CI contains BOTH zero AND delta_full. Report the CI and K;
                         make no separation claim for the cell.
  3 NOT SEPARATED        r < 0.25, OR the S2 CI contains zero.
  4 SEPARATED            r >= 0.75 AND the cell remains significant after Holm within the S2
                         family.
  5 PARTIALLY SEPARATED  everything else (in practice 0.25 <= r < 0.75, or r >= 0.75 with
                         significance lost).

thresholds_note
    "0.75 and 0.25 are conventional round numbers chosen without reference to any observed value.
     There is no principled basis on which to prefer 0.7 or 0.8, and inventing one after the fact
     would be worse than admitting the choice is conventional."

aggregation
    "Per family: the headline classification is the LEAST FAVOURABLE label among cells that are
     applicable and powered, ordered NOT SEPARATED < PARTIALLY SEPARATED < SEPARATED. If no cell
     in a family is both applicable and powered, that family's headline is UNDERPOWERED. The two
     primary families are reported SEPARATELY and are NEVER merged into a single headline. All
     cells are reported individually regardless. Implemented in src/pw1/interpret.py::aggregate."

one_shot_rule
    "Run once, reported whatever it says. No tuning of the subset definition, k, scoring, or
     family after seeing a result."

################################################################################
# 8. GUARDS AND HALT CONDITIONS
################################################################################

guard_1
    "Reproduce every published level EXACTLY before computing anything new.
     Family 1: 0.5682/0.7216 (MiniLM A), 0.3533/0.3800 (MiniLM B), 0.6080/0.7557 (bge A),
               0.3600/0.4267 (bge B).
     Family 2: C0 0.7841 / C4 0.8409 (MiniLM A), C0 0.7898 / C4 0.8352 (bge A).
     State per family whether reproduction was by re-score of persisted ranked lists or by re-run
     under seed 1337 / candidate_pool 50 / k_rrf 60."

guard_1_order
    "MiniLM / Track A FIRST, alone, before NC-A/NC-B and before anything else. It is the single
     point of failure for both families: family 1's only applicable MiniLM cell and family 2's
     only applicable cell full stop. If it does not reproduce, nothing downstream is worth
     computing."

guard_1_escalation
    "If reproduce-before-compute fails to regenerate a published number, that is a PAPER-LEVEL
     escalation, not a PW-1 blocker. STOP and report. Do NOT attempt repairs inside a frozen
     analysis."

at_risk_guard_1          # work order A8 — recorded so a failure reads as expected, not as a crisis
    "Two items were flagged as at-risk for guard 1. Both were investigated in this repository and
     BOTH RESOLVED; they are recorded here with the resolution attached, because writing the
     unresolved form into a frozen file would put a statement into the record that this repository
     contradicts.

     (1) 'No located artifact set reproduces the paper's published Track B condition table
         (C0 0.387, C1 0.367, C2 0.387, C3 0.387, C4 0.420, C5 0.413).'
         RESOLVED — it reproduces exactly, in the archive rather than in a working directory:
         rag-formatter-results.zip, results.json, run-20260724-135411, all-MiniLM-L6-v2, Track B:
         C0 0.3867 / C1 0.3667 / C2 0.3867 / C3 0.3867 / C4 0.4200 / C5 0.4133.
         That bundle is chain entry 1 in ARCHIVE_MANIFEST.md — the published v1.0/v1.1 run. The
         four working results* directories contain no MiniLM Track B condition run, which is what
         the search found. There is no `harness/` directory in this repository.
         The observation that §2.1's Track B baselines are the bge values, and therefore say
         nothing about whether the MiniLM Track B numbers exist on disk, is correct and accepted.

     (2) 'Two MiniLM Track A runs disagree on the C3-nosize ablation: 0.733 vs 0.6989.'
         NOT REPRODUCIBLE HERE — no artifact in this repository reports 0.733 for any ablation.
         C3-nosize Track A is 0.6989 in all three located sources: working results/,
         rag-formatter-results.zip, and rag_formatter_work_and_results_2026-07-28.zip. The only
         0.7330 present is in BUNDLE_MANIFEST.md and is the v1.4 parent-dilution control's
         parent-scored C2 recall@5 against child-scored 0.4318 — the +0.301 inflation figure, a
         different quantity from a different experiment.

     Neither blocks the stamp. Both remain listed as guard-1 inputs so that if guard 1 does fail
     on either, the failure is read against this record rather than as a new discovery."

guard_2_negative_controls
    "NC-A and NC-B, both shipped in tests/, both extended to cover S2 explicitly because S2 is
     the primary scoring and neither control was originally written with it in view:

       NC-A  gold falls ONLY inside an absorbed range:
             S0 hit | S1 MISS | S2 HIT | S3 MISS
       NC-B  gold falls ONLY inside an inherited range:
             S0 hit | S1 HIT  | S2 MISS | S3 MISS

     NC-B is what separates 'the tight arm is implemented' from 'asserted'. Its S1 expectation is
     a HIT: if S1 misses there, S1 is over-stripping and its numbers are wrong. NC-A's S2
     expectation is likewise a HIT. If either control misbehaves, STOP — nothing downstream would
     mean anything."

guard_3   "scripts/ and tests/ for this analysis ship in the bundle."

guard_4_rebuild_fidelity
    "The rebuild asserts against production per document: identical chunk count, unit_id, text,
     and claimed ranges. Passed on 45 + 60 documents, 235 + 1,074 chunks. Additionally,
     `top_hit_provenance` in the persisted per-query rows records the ranges the published run
     actually scored with, and the rebuild's claimed set is checked against it per query."

halt_conditions          # the complete frozen list
    "1. Either negative control misbehaves (guard 2).
     2. Any published level fails to reproduce (guard 1) -> paper-level escalation.
     3. r > 1.0 for any cell (A7) -> scoring defect.
     4. The rebuild disagrees with production on any document (guard 4).
     In every case: stop, report, attempt no repair inside the frozen analysis."

################################################################################
# 9. FINDINGS RECORDED BEFORE ANY ARM RUNS
################################################################################

PW1-F1          # amended per work order A5
    "(a) WRONG CHANNEL, AND WRONG STAGE. The paper's §11 attributes provenance width to absorbed
     duplicate ranges. The formatter's own merging accounts for 3.27% (Track A) / 0.20%
     (Track B) of sentence surface; chunk-to-segment inheritance accounts for 97.35% / 99.83% of
     the excess, at W_index_char 2.3182 / 2.3574. So the channel named in print is real but
     minor, and the dominant channel is introduced at a different STAGE — the re-chunking of
     formatted text, not the formatting.

     (b) THE METHODS DESCRIPTION DOES NOT MATCH THE IMPLEMENTATION. The methods passage states
     that every unit 'carries the character ranges of the original document it derives from'. A
     re-chunked formatted unit carries ranges of text in SIBLING segments it does not derive from
     — 97.35% of its excess surface on Track A.

     (c) THIS IS A REPRODUCIBILITY GAP, NOT ONLY A THREAT TO VALIDITY. A reader implementing the
     paper's own description of the ruler would not reproduce the published numbers for any
     two-stage condition.

     Holds whatever the arms return. The §11 and methods rewrite waits."

PW1-F2
    "STEP 0's OWN FIGURES WERE WRONG THREE TIMES, all caught before the stamp. A rule-based dedup
     proxy was reported as the formatter's absorbed surface (12,591 vs the actual 12,019 on
     Track A); a helper merged ranges across document boundaries, under-counting Track A by 2.1x
     (5,600 vs 12,019); and a corpus-level union of 'excess' was briefly reported, a quantity that
     measures nothing. The first two were found by chasing a reviewer's observation that two
     reported figures could not both be right; the third by asking what the corrected figure meant.
     Recorded because a corrected number with no record of the correction is indistinguishable
     from a number that was always right."

PW1-F3          # work order A3 — the STRONG form, and from a stronger source than the prose
    "THE PRACTICAL HEADLINE IS NOT SUPPORTED BY THE PAPER'S OWN DECLARED PROCEDURE.

     A3 asked which multiplicity family the paper declares. The white paper file is not present
     in this repository, so the prose could not be inspected. The governing declaration is
     stronger evidence than the prose would have been, and it IS present: the v1.1
     pre-registration, frozen 2026-07-24T13:33:49Z and archived in rag-formatter-results.zip,
     states as `criteria.prose_rule`:

         'any "beats" claim must be backed by a significant pairwise test
          (CI excluding 0 after Holm) — changelog-8'

     and names the comparison explicitly in H4: 'secondary C4 (formatted+naive) > C0 (naive
     alone)'.

     The declared family is the run's six-member pairwise set
     {C3_vs_C2, C3_vs_C1, C3_vs_C0, C5_vs_C2, C4_vs_C0, C5_vs_C3}, and the Holm-adjusted value
     for C4_vs_C0 on Track A is stored in that same published artifact: p_holm = 0.10250 against
     a raw p of 0.02050. **It does not clear 0.05.** So A3's second branch applies: the paper
     reports the condition table as a family and stores Holm-adjusted values for it.

     A SECOND DEFECT, and the third instance of it in this programme: `prose_rule`'s phrase
     'CI excluding 0 after Holm' names TWO procedures, exactly as v1.5's `significant_definition`
     did (Results_v1.5_SmallToBig.md §2; template rule A5). C4-vs-C0 on Track A clears the CI
     half — [+0.0170, +0.1023] excludes zero — and fails the Holm half. Under the conjunctive
     reading the phrase's word 'after' implies, the claim does not clear. A multiplicity-adjusted
     CI for that contrast is computable from persisted per-query data and is deliberately NOT
     computed here, because it is new analysis and the stored adjusted p already settles the
     point.

     This is a fact about the paper, true regardless of what the arms return, and it is recorded
     pre-outcome like PW1-F1 and PW1-F2. It bears directly on how a NOT SEPARATED result on
     family 2 would have to be reported: the cell being stress-tested is one the paper's own
     frozen rule does not license as a 'beats' claim."
```

---

## Work-order checklist

| # | Item | State | Commit |
|---|---|---|---|
| A1 | Amended freeze text sent verbatim | **done** — this file | `<this commit>` |
| A2 | `branch_1_significance` set to Holm-within-family; family 2 recomputed to 0.0410 / 0.0931; agreement sentence added | **done** — §5. Verified: raw / CI / Holm-within agree on **all six** cells | `<this commit>` |
| A3 | PW1-F3 recorded | **done, strong form** — §9. Paper file absent; the v1.1 prereg's `prose_rule` is the governing declaration and is archived | `<this commit>` |
| A4 | Width statistic disambiguated | **done** — §2, four named quantities. Spread is wider than the work order knew: `W_index_mean` is **3.0935** on Track A | `<this commit>` |
| A5 | PW1-F1 overstatement corrected | **done** — §9(a); "no width" replaced by 3.27% / 0.20% against 97.35% / 99.83% | `<this commit>` |
| A6 | Pre-stamp classifications justified | **done** — §1 `pre_stamp_classifications_are_legitimate` | `<this commit>` |
| A7 | `r ≤ 1.0` a halt in code | **done** — `src/pw1/interpret.py::retention_ratio` raises `RatioExceedsOne`; 19 tests in `tests/test_pw1_interpret.py`; added to §8 `halt_conditions` | `<this commit>` |
| A8 | Guard-1 at-risk items recorded | **done, with resolutions attached** — §8 `at_risk_guard_1`. Both investigated; item 1 resolved (table is in the archive), item 2 not reproducible here | `<this commit>` |
| A9 | Inapplicable cells re-scored descriptively | **done** — §4 `descriptive_companion_cells`, covering family 2's bge/A and family 1's MiniLM/B | `<this commit>` |

**Not stamped. Awaiting confirmation of the text above.** On confirmation: B1 stamp with a real
timestamp, then B2 guard 1 on MiniLM/Track A alone, then B3 NC-A/NC-B, then B4, B5, B6.
