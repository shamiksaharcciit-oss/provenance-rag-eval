# Results v1.8 — INSTRUMENT-DIVERGENCE

**Pre-registration:** `Plan_v18_InstrumentDivergence_2026-08-01.md`, frozen at `a6c5547`
(2026-08-01), with sixteen pre-freeze and by-ruling amendments PF-1…PF-16 listed in its §0.
**Date:** 2 August 2026
**Executing agent:** the second agent (plan §8). Nothing under `v17/` was written or locked.
**Status:** Gate 1 deliverable. Data collection complete; predictions scored against sealed
text on their named cells. **STOP** — no packaging, no sequencing recommendation.

---

## 1. What was run

Three arms — `U256`, `U768`, `F768` — built by importing v1.6's `build_arm`, retrieved at the
field-standard **fixed k = 5** with no budget matching, on Track A (n = 176) and Track B
(n = 150). Generation and judging by `claude-sonnet-5`; arms built at each track's default
formatter model so they reproduce v1.6 byte for byte.

All test-set calls ran through the Message Batches API (PF-12).

| stage | batch id | calls | in / out tokens | rows sha256 |
|---|---|---:|---:|---|
| generation | `msgbatch_018qmUr9PEUmhJer7FpjULiZ` | 1,682 | 10,526,615 / 84,928 | `d51ee286…` |
| judging J1 part0 | `msgbatch_01ECiDmfqYPnUiQNok9VWMJc` | 10,000 | 8,640,251 / 274,492 | `1106e178…` |
| judging J1 part1 | `msgbatch_01MzRUXHmUpuvThHNAuVz2wJ` | 4,278 | 5,859,021 / 78,712 | `8a6bd94a…` |
| judging J2 | `msgbatch_01Qb3ELmtjVYMjxeMqgYfpiF` | 1,682 | 10,729,048 / 29,699 | `9a6c61c7…` |
| **total** | | **17,642** | 35,754,935 / 467,831 | |

**0 failed rows and 0 resubmission rounds** across all four batches. `response.model` was
`claude-sonnet-5` and **constant across all 17,642 rows**; sampling parameters sent: **none**
(PF-9 — the pinned model accepts no `temperature`). Query identity is `custom_id` plus the
frozen codebooks, sha256 `c192ddd0…` (A) and `1397610b…` (B).

**978 cells scored** — 326 queries × 3 arms — with no cell dropped.

## 2. Costs: actual against projection

| | calls |
|---|---:|
| frozen projection (plan §6) | 17,642 |
| **actual, from the ledger** | **17,642** |
| ceiling | 25,000 |

Actual equals projection to the call. The ledger also carries one **indeterminate** entry: the
abandoned Gate 0 probe, **334–1,018 calls** against PF-1's 1,000-call bound, recorded as a range
with its cause because two attempts died on credit exhaustion and their consumption was set by
the account balance rather than by the plan.

## 3. The three instruments

**I3 contributes no new number.** v1.6's matched-budget record is cited, never recomputed:
`Results_v16_SegmentSize.md` (closed since `12483f9`), whose verdict was **KILL** — the
formatter's editing does not improve retrieval at matched budget. No number below revisits it.

### 3.1 I1 — context-level composite (descriptive; no test, no mechanism)

| track | contrast | mean | n01 | n10 | ties |
|---|---|---:|---:|---:|---:|
| A | `F768 − U256` (total) | **+0.28392** | 108 | 26 | 42 |
| A | `U768 − U256` (size) | **+0.28932** | 104 | 19 | 53 |
| A | `F768 − U768` (residual) | **-0.00540** | 33 | 52 | 91 |
| B | `F768 − U256` (total) | +0.04870 | 52 | 25 | 73 |
| B | `U768 − U256` (size) | +0.03805 | 46 | 28 | 76 |
| B | `F768 − U768` (residual) | +0.01065 | 31 | 25 | 94 |

### 3.2 I1 — answer-level composite (descriptive)

| track | contrast | mean | n01 | n10 | ties |
|---|---|---:|---:|---:|---:|
| A | `F768 − U256` | +0.26947 | 151 | 11 | 14 |
| A | `U768 − U256` | +0.15104 | 125 | 34 | 17 |
| A | `F768 − U768` | +0.11843 | 93 | 49 | 34 |
| B | `F768 − U256` | +0.08774 | 92 | 48 | 10 |
| B | `U768 − U256` | -0.01776 | 69 | 66 | 15 |
| B | `F768 − U768` | +0.10549 | 93 | 48 | 9 |

### 3.3 I2 — token-F1 against gold span text (descriptive)

Per query, the median over the judged answers (PF-3/PF-14).

| track | contrast | mean | n01 | n10 | ties |
|---|---|---:|---:|---:|---:|
| A | `F768 − U768` | +0.13460 | 71 | 48 | 57 |
| A | `F768 − U256` | +0.29840 | 127 | 15 | 34 |
| A | `U768 − U256` | +0.16380 | 90 | 21 | 65 |
| B | `F768 − U768` | +0.00915 | 24 | 18 | 108 |
| B | `F768 − U256` | +0.00399 | 26 | 19 | 105 |
| B | `U768 − U256` | -0.00517 | 19 | 20 | 111 |

## 4. `F_BIAS` — the tested family, one member

**B1 (fluency excess), Track A, n = 176.** Per-answer paired (PF-14): per query and per answer
draw, the judge-preference indicator for `F768` over `U768` minus the token-F1 preference
indicator on **the same two answers**; the per-query value is the median of the three per-answer
differences.

| | |
|---|---|
| mean | **+0.142045** |
| 95% CI (paired bootstrap, 10,000 iters, seed 1337) | **[+0.039773, +0.250000]** |
| permutation p | **0.011699** |
| Holm-adjusted p | **0.011699** |
| discordant | 24 favour positive · 11 favour negative · 141 ties |

**`F_BIAS` has exactly one member, so Holm is the identity and `p_holm` is the plain
p-value, not a corrected one.** It is reported as such rather than presented as a correction that
was applied.

**B1 on Track B** (descriptive, direction only; n = 150): mean **+0.260000**, CI
[+0.113333, +0.400000], p 0.001, discordant 75 positive · 33 negative · 42 ties.

## 5. Predictions scored against sealed text, on named cells only

| id | sealed cell | outcome | scored on |
|---|---|---|---|
| **PD-1** | Track A, descriptive | **CONFIRMED** | context composite `F768 − U256` = **+0.28392**, favouring `F768` |
| **PD-2** | both tracks, descriptive [PF-7] | **CONFIRMED** | A: size **+0.28932** ≥ residual **-0.00540**; B: size **+0.03805** ≥ residual **+0.01065**. `pd2_direction_holds` = True on both |
| **PD-3** | Track A, `F_BIAS`'s single member B1 | **CONFIRMED** | B1 mean **+0.142045**, `p_holm` **0.011699** < 0.05, CI excludes zero |
| **PD-4** | Track A, descriptive, **control** | **REFUTED on its first clause; confirmed on its second** | `F768 − U768` token-F1 = **+0.13460**, not ≈ 0; `F768 − U256` = **+0.29840**, positive as anticipated |
| **PD-5** | Track B, direction only | **CONFIRMED** | B1's sign on Track B (**+0.260000**) matches Track A's (**+0.142045**) |

**PD-4 is the control and it did not behave as sealed.** The plan predicted token-F1
`F768 − U768 ≈ 0`, "consistent with the frozen provenance record"; the observed value is
**+0.13460** on Track A with 71 queries favouring `F768` against 48 favouring `U768`. It is
recorded as refuted. No mechanism is offered for it here, and no other line of this document is
adjusted in light of it. Track B's corresponding value is **+0.00915**.

The plan's pre-committed reading (§5) is reproduced without extension: PD-2 and PD-3 confirmed →
the standard frame's favourable report is attributable to size plus judge preference, and **no
formatter claim may be built on I1**.

## 6. Judge instruction-violations (PF-16 §1.4, descriptive)

The frozen judge prompt demands "one line of JSON and nothing else". **101 of 15,960 replies
(0.63%)** wrote reasoning first and the JSON after.

| by metric | n | | by track | n |
|---|---:|---|---|---:|
| `context_recall` | 64 | | A | 99 |
| `context_precision` | 30 | | B | 2 |
| `faithfulness` | 6 | | | |
| `answer_correctness` | 1 | | | |

By track and arm: A/`F768` 40, A/`U768` 38, A/`U256` 21, B/`F768` 1, B/`U256` 1.

Descriptive. **No test and no mechanism** — the A-heavy split is reported and not explained
(A1g). A judge that disobeys an explicit format instruction 0.63% of the time, concentrated in
the two context-level metrics, is recorded as an observation about judge-based evaluation.

## 7. The probe: abandoned by rule

Four attempts produced no valid determinism verdict — the first measured its own response cache
and was caught by its own assertion; two died on API credit exhaustion; the fourth resolved its
model from a harness default and measured `claude-opus-4-8` rather than the pinned model. Ruled
at Gate 0(b) §3: **not re-run, not repaired.** Its "35/60 divergent" and "0/24 divergent"
verdicts are **withdrawn** with their artifacts, retained under `INVALID_*` names with hashes
`b4af4a60…`, `eefac253…`, `c9681703…` — renamed, never edited, because `requested_model` inside
them is the honest record.

**Determinism is therefore unmeasured and recorded as such**, and both targeted-repeat branches
ran by rule. **Every single-run number in this document carries the caveat: single sample,
sampling nondeterminism unquantified, temperature pin unavailable.**

## 8. Limitations

1. **Non-blind.** v1.6's null and the bias hypothesis were known to everyone involved. Every
   prediction above is HYPOTHESIS under A1g.
2. **Single judge**, and the judge is the same model as the generator. Self-preference applies
   equally to both arms of each contrast, so it does not bias a within-query difference — but
   single-judge dependence is a limitation, not a footnote.
3. **Fixed k = 5 by design.** At fixed k the 768-token arms carry ~2.7× the tokens of `U256`
   (measured: A 3451/3415 vs 1260). That confound is the object of study, not a defect.
4. **No temperature pin.** `claude-sonnet-5` rejects `temperature` outright, so no
   parameter-based determinism claim exists anywhere in v1.8 (PF-9).
5. **Determinism unmeasured** — see §7.
6. **I1 is a reimplementation of RAGAS-class formulas, not RAGAS** (PF-8). `ragas` was not
   installed, and installing it would have perturbed the pinned environment under which v1.6's
   and v1.7's reproduction checks pass. This qualifies the plan's "exactly as the field would
   evaluate it".
7. **Judge and generation variance are not separately identified (PF-14 §3).** Under per-answer
   pairing each judged answer is a fresh generation sample *and* a fresh judgement sample, so the
   repeats cover the joint draw. Separating them serves no frozen prediction and would breach the
   ceiling.
8. **The parser was amended post-freeze** (PF-16, ruled in `Decisions_v18_G15_2026-08-01.md`),
   after the 101 failure *locations* were known and **before any score existed**. The amendment
   is a total, uniform, content-blind syntactic rule conditioning on no verdict; it is the
   identity on conforming replies, verified against the real data — 15,859 rows parse identically
   under the pre-amendment and amended parsers, 0 differ, 101 parse only under the amendment.
   Re-issue remained available as a fallback for replies the amended parser still refused; there
   were none, so it was not used.
9. **Incidental exposure.** During the scoring STOP that produced G15, the failure log printed
   the judge's prose for ten cells and the agent read them while triaging. Nothing was aggregated
   and no metric was computed from them. The cells are: `A/U256` × `A-026-krait-router::mh`,
   `A-042-ridge-broker::mh`, `A-035-onyx-indexer::f5`, `A-028-mica-gateway::mh`,
   `A-026-krait-router::f2`, `A-012-ridge-indexer::f1`, `A-039-zephyr-gateway::mh`,
   `A-009-zephyr-ledger::mh`, `A-012-ridge-indexer::mh`, `A-003-ember-scheduler::mh`. Scoring
   was subsequently run as a fresh process without manual log reading.
10. **The abandoned probe's bill.** A dev-set probe with the real prompts would likely have
    surfaced the hedging shape before 17,642 calls were spent, and PF-16 would have been a
    pre-freeze amendment. The probe was abandoned for reasons sound on the information then
    available; this is the cost side of that trade, recorded rather than re-litigated.

## 9. Attribution of the amendments

PF-13 and PF-15 repair specifications made by the **ruling side** — the `custom_id` grammar of
`Decisions_v18_G12_2026-08-01.md` §1, which `Decisions_v18_G14_2026-08-01.md` §4 assigns there
explicitly. The executing agent's error at G12 was the **alphabet half of the API constraint**:
asserting `custom_id`'s 64-character limit while never validating its character set. Each is
cited where it belongs.

## 10. Item-7 self-check

Every count and universal above names the procedure that produced it, and each procedure was
executed against **this** text. Output in [`v18/results_run/item7_check.json`](v18/results_run/item7_check.json).

---

**STOP.** Gate 1 deliverable complete. No packaging, no release drafting, no sequencing
recommendation — that decision is Shamik's, taken on the complete record.
