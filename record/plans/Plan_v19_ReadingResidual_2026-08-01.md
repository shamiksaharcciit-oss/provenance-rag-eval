# v1.9 READING-RESIDUAL — pre-registration draft for agent 1
# (the reading test, resurrected under its own freeze, measuring the one mechanism E1 left alive)

**Status:** DRAFT FOR FREEZE. Becomes a pre-registration only at its Gate 0 freeze commit.
Until then nothing is sealed; no test-set call may be spent at any point before the freeze,
and no call of any kind before the Gate 0 ruling.
**Date:** 1 August 2026
**Experiment ID:** `v19` — own directory, own manifest, own results document.
**Executing agent:** agent 1 (v1.7 is closed; this is its next assignment).
**Authorised by:** Shamik, 1 August 2026 ("draft it", following "better to measure it than
give up").

---

## 0. What this tests, and why it is cleaner than the E2 it replaces

v1.6 killed retrieval benefit at matched budget. v1.7 killed structural packaging: at equal
budget, formatter units deliver whole spans in single units no more often than size-matched
arbitrary cuts (+3/176). One measurable mechanism remains: **given the same information, in
same-sized parcels, with equal structural delivery, does the formatter's repaired prose
itself change what a generator extracts from it?**

INTEGRITY-KILL sharpened this question. The original E2 confounded two mechanisms —
whole-span delivery and prose quality. E1 established the first is absent, so any v1.9
effect is attributable to the second alone. That attribution is the point of running.

**Contamination disclosure (freezes with the plan):** nothing here is blind. Two kills are
known to everyone involved, and so is the motivation to find a surviving channel. Every
prediction is HYPOTHESIS under A1g. The prior, stated honestly: two intuitions of this
family have died under measurement; this one gets no benefit of the doubt, only a fair
test.

### Pre-freeze amendments

Four Gate 0 findings, ruled in `Decisions_v19_Gate0_2026-08-01.md` and applied to this
document before the freeze commit. Listed so they are legible rather than merely
discoverable in history.

| id | finding | change |
|---|---|---|
| **PF-G1** | `LLMClient` discards `response.model` (G5's pin unreadable) and always writes cache (G2's bypass impossible) | `V19Client` **subclasses** `LLMClient` inside `v19/`; `src/` untouched; subclass rather than a fresh SDK wrapper **so the cost guard still binds** |
| **PF-G2** | six Track A packages fall short of B2(q), all in `F768`, by 28–76 tokens | §1's exact-B2(q) promise amended to permit document exhaustion **with its cause recorded**; the six listed at freeze; no exclusion, no cross-document padding; **the imbalance's direction declared UNKNOWN, not conservative** |
| **PF-G3** | B2(q)'s `max` rule converts `F768`'s compactness into every arm's padding | `T_a(q)` promoted to a declared descriptive companion; a null PR-1 must carry the padding explanation as HYPOTHESIS beside it |
| **PF-G4** | §6 under-counted the PR-0 control by half | projection recomputed from the census: **1,334** single-run, **2,390** worst case, against the 5,000 ceiling |

All four were settled **before any v1.9 model call existed** — none has been made. No
amendment to this document is permitted after the freeze commit; anything found later is a
new pre-registration.

Standing constraints, all in force: closed artifacts untouched (`12483f9`, `235ccfb`,
`cdd197f`, `5176903`, the v1.7 Gate 1 ruling, all PW-1 artifacts, white paper, brief); no
formatter or frozen-config change; nothing under `v17/` or `v18/` modified; no v1.9 number
revisits any closed conclusion; preserve exact domain terms, identifiers and numbers
verbatim wherever text is handled; the personal documents in the working folder remain out
of scope.

---

## 1. Design — inherited rulings applied, not re-derived

Oracle packages, retrieval removed by construction, exactly as ruled in v1.7's Gate 0:

- **Arms:** `F768` vs `U768` (primary pair), `U256` (descriptive third). Inventories built
  by importing the v1.6 procedures — identity over assertion; a test asserts object
  identity on the imported builder.
- **Packages:** per v1.7 plan §3.1 as amended by ruling PF-2 — minimal gold-overlapping
  unit set in document order, padded alternately to **B2(q) = max(1024, largest minimal
  gold set across all three arms)**, exact-token truncation, `GoldExceedsBudget` as an
  APPARATUS-STOP assertion, 8192 cap likewise. Package selection uses *overlap* with gold
  ranges, not coverage, so E1's whitespace-coverage defect does not touch it — verified by
  a unit test, not asserted.
- **The exact-B2(q) promise, as amended [PF-G2].** Packages are built to exactly B2(q), **or
  short only by document exhaustion, which is recorded per package with its cause**; a
  shortfall from any other cause is an APPARATUS-STOP, established positively by checking
  that no unit of the gold document was left unused. The census found **six** such
  instances, all Track A, all in `F768`, listed here at freeze:

  | query | B2(q) | `F768` | `U768` = `U256` | short by | `T_F768` | `T_U768` |
  |---|---|---|---|---|---|---|
  | `A-008-quartz-resolver::f4` | 1444 | 1368 | 1444 | 76 | 762 | 1444 |
  | `A-023-harbor-sharder::f4` | 1346 | 1300 | 1346 | 46 | 763 | 1346 |
  | `A-019-crag-broker::f4` | 1247 | 1199 | 1247 | 48 | 764 | 1247 |
  | `A-012-ridge-indexer::f4` | 1152 | 1124 | 1152 | 28 | 768 | 1152 |
  | `A-036-halcyon-cache::f4` | 1111 | 1058 | 1111 | 53 | 762 | 1111 |
  | `A-000-kestrel-indexer::f4` | 1105 | 1058 | 1105 | 47 | 763 | 1105 |

  **Track B has none** (census, 150/150 exact). Cause in every case: `U768`'s fixed cuts
  split the gold across two units, driving B2(q) to 1105–1444, while `F768` holds the same
  gold in one unit of 762–768 tokens and then exhausts its document before reaching the
  padding target.
- **No exclusion and no cross-document padding.** The six stay in `F_READ2`, which remains
  declared over all 176: they are the queries where naive fragmentation of the gold is at
  its worst — the mechanism-carrying cases — and excluding them would repeat the error
  rejected at v1.7's Gate 0. Padding `F768` from another document would equalise arithmetic
  while desynchronising content; **equal tokens of unequal kind is a worse imbalance than
  unequal tokens of equal kind.**
- **The imbalance's direction is UNKNOWN, not conservative [PF-G2].** "Short by 28–76
  tokens" is a handicap only if more context always helps, and for extraction it often does
  not — the missing tokens are padding, i.e. distractor material, so a shorter package with
  identical gold is plausibly *easier*. The frozen statement is therefore: **six pairs carry
  a token imbalance of unknown sign, bounded at 3.4% of the track, disclosed per pair.** No
  claim is made that it cannot produce a positive PR-1.
- **No embedder, no index, no encode anywhere in v1.9** — the memory order is satisfied
  vacuously, and this is stated so nobody looks for margins that cannot exist.
- **Generator:** `claude-sonnet-5`; pin per the v1.8 G5 ruling — requested id plus
  `response.model` logged every call and asserted constant, run window in the manifest.
  Temperature 0, fixed `max_tokens`. Prompt: the v1.7 E2 prompt, canonical at `e19dd35`,
  by citation.
- **Determinism probe:** the v1.8 G2 ruling ported in full — repeats bypass the response
  cache, read nothing, write nothing; the harness asserts fresh-call count = queries ×
  repeats; probe on Track A dev only, verdict extended to Track B as the declared
  sampler-property assumption; probe bounded at 500 calls. The identical latent defect in
  v1.7's cancelled E2 spec is the reason this paragraph exists.
- **Nondeterminism fallback (targeted, per the v1.8 G3 pattern):** generator
  nondeterministic → 3× generation with per-query median **only for Track A
  `F768`/`U768`**; all else single-run with the mandatory variance caveat.

## 2. The control this design was missing

E2 had no analogue of PE1-4, and it needs one: on Track B especially, the generator may
answer real published prose **from its own training rather than from the package**, in
which case F1 measures memory, not reading, and every contrast is noise around a ceiling.

**Context-ablation control, run first:** 30 queries per track (fixed seed 1337 sample,
drawn and frozen at Gate 0), each generated once with its correct `F768` package and once
with a **mismatched package** (query *i* receives query *i*+1's package, wraparound).

- **PR-0 (control, both tracks):** F1(correct) exceeds F1(mismatched) decisively — the
  declared criterion: mismatched median F1 < 0.2 and correct − mismatched median gap >
  0.3, per track.
- **Frozen consequence:** a track that fails PR-0 has every v1.9 number on that track
  **quarantined as not evidence about reading** — the run may complete for the record, but
  no prediction is scored on that track and no contrast from it appears outside a flagged
  descriptive table. If both tracks fail, that is APPARATUS-STOP: the design cannot
  measure reading with this generator and corpus, and the honest outcome is "unmeasurable
  as designed", not a verdict in either direction.

## 3. Scoring and the single tested family

- **Primary (objective):** token-F1 against gold span text; the v1.7 normalisation code,
  canonical at `e19dd35`, by citation. Multi-span gold concatenated in document order.
  `NOT FOUND` scores 0; if gold is genuinely absent from a package, that is the
  `GoldExceedsBudget`-class STOP, unreachable by construction.
- **Secondary (descriptive):** exact containment counts.
- **Secondary (declared, judge):** blinded A/B on the Track A primary pair only, order
  randomised, judge determinism handled by the same probe protocol; the judge never
  overrides F1; the pre-declared bias signature stands — judge favours `F768` while F1
  does not = fluency bias observed, reported as such.
- **Tested family `F_READ2`, exactly one member, Track A:** paired token-F1 difference,
  `F768` package vs `U768` package, all 176 test queries (less any PR-0 quarantine, which
  is track-level and cannot be partial). Holm over one member = plain p, stated as such.
  `paired_bootstrap_diff` + `paired_permutation_p`, `iters = 10000`, `seed = 1337`,
  `ci = 0.95`. Per-query direction counts recorded descriptively beside the net.
- Everything else — Track B, `U256` contrasts, containment, judge rates — descriptive:
  values and discordant counts, no test, no mechanism prose.

## 4. Sealed predictions (all HYPOTHESIS; cells named)

- **PR-0** — the control, §2, both tracks, scored first in the results document.
- **PR-1 (Track A, `F_READ2`):** mean token-F1(`F768`) − mean token-F1(`U768`) > 0.
- **PR-2 (Track A, descriptive):** exact-containment count higher for `F768` packages.
- **PR-3 (Track A, descriptive):** judge direction agrees with F1's on the primary
  contrast; disagreement in the formatter's favour is the bias signature, not support.
- **PR-4 (Track B, direction only, descriptive, contingent on PR-0(B)):** the sign of the
  `F768 − U768` F1 difference matches Track A's.

## 5. Frozen consequences

- **PR-1 positive at p < 0.05 (single member):** the claim earned is exactly — *formatter
  prose improves extractive answer quality at equal token cost and equal structural
  delivery, when the answer is present in context.* Nothing about retrieval, packaging,
  ranking, or deployment; no revision to any closed verdict; the internal report may carry
  this sentence and no stronger one.
- **PR-1 null:** the reading-value claim is dead at the last measurable layer, and the
  frozen sentence for the internal report is: *measured at retrieval, packaging, and
  reading, the formatter's value is operational — hygiene, preservation, and cost — plus
  one untested deployment hypothesis (dose-response on degraded corpora), which only its
  own pre-registered experiment can test.* E3 remains the sole surviving question, on its
  own merits, not authorised here.
- **PR-0 failure handling** per §2. No other branch exists.

## 6. Costs and coordination

- **Projected calls [PF-G4], recomputed from the census rather than estimated:**

  | component | calls |
  |---|---|
  | generation, single-run (326 queries × 3 arms) | 978 |
  | PR-0 control (30/track × 2 tracks × **correct + mismatched**) | **120** |
  | determinism probe (20 Track A dev prompts × 3 repeats) | 60 |
  | judge (Track A, 176) | 176 |
  | **total, single-run branch** | **1,334** |
  | **total, worst case with G3 targeted repeats** | **2,390** |

  Declared ceiling: **5,000 calls** — breach is a STOP. Estimated true cost ≈ $10–15.

  The draft said 60 control calls and ≈1,864/3,000 overall. **60 assumed one generation per
  sampled control query; §2 requires two, correct and mismatched, so it is 120** — the
  control was under-counted by half. The probe was also carried at its ≤500 bound rather
  than the 60 it actually needs. Both corrected above; the projection is recomputed at
  freeze under whichever branches the probes select, and a projection over the ceiling is a
  STOP, not a trim.
- **No cost-guard edit is authorised.** The guard returns to its default when v1.8's
  results commit reverts it; if the guard would abort v1.9's run, that is a STOP for a
  ruling, not an edit.
- **Spend sequencing:** Gate 0 build and the ruling may proceed immediately; **no v1.9
  call — probe included — until v1.8's results commit exists**, so the two experiments
  never spend under the same guard window and cost attribution stays clean. `v19/` paths
  only; conflicts are a STOP.

## 7. Gates

**Gate 0 — build and STOP.** Arms by import with identity tests; package builder exercised
against the real corpora with the B2(q) escalation table and attribution column (the
domain-census practice — the builder meets the corpus's real structural variety before
freeze, not the author's model of it); control sample drawn and frozen; all unit tests
including: overlap-not-coverage selection, mismatched-package wiring (query *i* → package
*i*+1 exactly), fresh-call assertion, `response.model` constancy, B2(q) equality across
arms per query. Cost projection per §6. Then STOP for a ruling — findings expected, per
both precedents.

**Gate 1 — run complete.** `Results_v19_ReadingResidual.md`: PR-0 first, predictions
scored against sealed text on named cells, all descriptive companions with direction
counts, determinism probe outcomes, costs actual vs projected, limitations (non-blindness,
single judge, the Track B parametric-knowledge risk PR-0 exists to catch), item-7
self-check with output in the record. Then STOP for the ruling. No E3 work, no internal-
report drafting, no packaging recommendation — the report language in §5 is frozen for
*when Shamik commissions that document*, not an instruction to begin it.

Additionally required at Gate 1 [PF-G2, PF-G3]:

- **The six imbalanced pairs printed individually** — one row each: query id, B2(q), both
  package lengths, both F1 scores, the per-query difference. Raw and descriptive: no
  aggregate over them, no second test on `F_READ2`, so A5b stays intact because no quantity
  acquires a second procedure. A reader who wants to know whether the imbalanced pairs drove
  PR-1's verdict can see it directly, which is transparency doing the work a sensitivity test
  would otherwise be reached for.
- **`T_a(q)` — the gold-delivery cost — as a declared descriptive companion.** Per-arm
  distributions, both tracks, values and attribution, no test. It is the compactness fact in
  the units this experiment measures (on the six queries, 762–768 against 1105–1444), and it
  is already computed as B2(q)'s own input.
- **If PR-1 is null, the padding explanation is stated beside it as HYPOTHESIS.** B2(q)'s
  `max` rule converts `F768`'s compactness into every arm's padding — that is the intended
  behaviour of equal-token matching, since compactness *is* a size effect and neutralising
  size is the design. But it means *"the packaging advantage was spent on padding"* is a live
  alternative reading to *"prose quality does nothing"*, and a null must carry both rather
  than being allowed to read as the broader claim.

## 8. Not authorised

E3 in any form. Any edit outside `v19/` paths and v1.9's own documents. Any recomputation
of closed quantities. Any additional arm, metric, judge, track, or test. Any use of v1.9
to argue about v1.6, v1.7, v1.8, or PW-1. Any external release or draft of one.
