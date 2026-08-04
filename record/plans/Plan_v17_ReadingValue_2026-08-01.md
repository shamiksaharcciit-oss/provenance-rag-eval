# v1.7 READING-VALUE — pre-registration draft for agent execution

**Status:** DRAFT FOR FREEZE. This document becomes a pre-registration only at the Gate 0
freeze commit. Until that commit exists, nothing here is sealed and no arm may run.
**Date:** 1 August 2026
**Experiment ID:** `v17` — new ID, new results directory, new manifest. Nothing in this plan
reopens v1.6, PW-1, or any closed artifact.
**Authorised by:** Shamik, 1 August 2026 ("create the plan that the agent can execute").
Authorisation covers: Gate 0 preparation, E1 execution, and E2 execution **only if** E1's gate
rule passes and a ruling confirms. E3 is a skeleton only and is NOT authorised.

---

## 0. What this experiment is, and what it must not touch

v1.6 killed the claim that the formatter's editing improves *retrieval* at matched budget. The
claim under test here is different and was never measured: **that the formatter's units are
better to read once found** — that they deliver whole answer spans in single coherent pieces
(E1) and that a generator produces better answers from them at equal token cost (E2).

Standing constraints, all in force:

- The closed record is untouched: `Results_v16_SegmentSize.md` (since `12483f9`),
  `Decisions_v16_Closeout_2026-07-31.md` (since `235ccfb`),
  `Candidates_ScopeOfDirectionTest_2026-07-31.md` (since `cdd197f`), all PW-1 artifacts, the
  white paper, the brief (§12.10). No edit to any of them for any reason arising from v1.7.
- **v1.7 must never be used to revisit v1.6's KILL or PW-1's conclusion.** If a v1.7 number
  appears to bear on either, it is reported descriptively and the observation stops there.
- No change to `formatter.py` (including the `:243` `right_size` override), no change to
  `_emit`'s join separator, no change to any frozen config or published number.
- The formatter rule stands wherever text is generated or compared: preserve exact domain
  terms, identifiers and numbers verbatim; edit only structure and references, never
  vocabulary.
- The working folder's personal documents remain out of scope entirely.

### Contamination disclosure (required at freeze, sealed with the predictions)

Strict-containment numbers (`strict_containment: 0.5`) were computed as cross-checks in prior
runs and may have been partially observed by both the agent and the ruling side. E1's
hypotheses are therefore **not blind to the data** and every E1 prediction is labelled
HYPOTHESIS under A1g, never VERIFIED-in-advance. All E1 arm values are computed by **fresh
runs** under the v17 ID; no strict-containment number from any prior run may be quoted,
compared against, or "sanity-checked" against during E1. The disclosure text in this section
is part of the frozen document.

Procedures in this plan are fixed **before any v17 value exists** — that is the point of
freezing it (candidate criterion: forced means forced by a procedure fixed before the value
was known).

### Pre-freeze amendments

Three changes were made to this document between drafting and the freeze commit, all in
response to Gate 0 findings (`v17_Gate0_Findings_2026-08-01.md` @ `235a59d`, ruled in
`Decisions_v17_Gate0_2026-08-01.md`). The repository history would show them anyway; they are
listed so they are legible rather than merely discoverable.

| id | finding | change |
|---|---|---|
| **PF-1** | §2.2 named provenance rung `S1`, which §2.1's construction cannot produce — `inherited` is a PW-1 `TightUnit` concept and occurs nowhere in `src/chunkers/` or `src/v16/` | `S1` → **`S3`**, the conservative floor v1.6 reported |
| **PF-2** | §3.3's "impossible by construction" was false: gold-bearing unit runs exceed a global B2 = 1024 on 6/176 Track A `U768` and 61/150 Track B `U768` | B2 becomes **B2(q)**, a per-query matched budget; cap at 8192; §3.3's claim restored to truth rather than deleted |
| **PF-3** | §3.2's fenced prompt block carried a mid-sentence line break from the document's 96-column wrap | block rendered unwrapped; the **frozen artifact declared canonical** over this document's markdown |

All three were settled **before any v17 arm value existed**. No amendment to this document is
permitted after the freeze commit; anything found later is a new pre-registration.

---

## 1. The three claims, and the ladder

- **Claim 1 (E1, structural):** at matched retrieval budget, the formatter's inventory
  delivers whole gold spans inside single units more often than the naive cutter's. No LLM
  involved. Cheap, deterministic.
- **Claim 2 (E2, reading):** with retrieval removed by construction (oracle packages, equal
  tokens), a generator answers better from formatter units than from naive-cut fragments.
- **Claim 3 (E3, dose-response):** the benefit rises with input degradation and approaches
  zero on clean prose. Skeleton only (§4). Not authorised.

E1 gates E2 (§5). E2 gates E3. Each gate is a STOP: results document, then ruling, before
anything further runs.

---

## 2. E1 — span integrity at matched budget

### 2.1 Arms

Reuse the v1.6 arm construction procedures unchanged, executed fresh under `v17`:

| arm | construction |
|---|---|
| `U256` | naive fixed-size cutter, 256 tokens |
| `U768` | naive fixed-size cutter, 768 tokens |
| `U768-ws` | as `U768`, whitespace-join control |
| `S768` | formatter boundary positions applied to unedited text (v1.6 SEAM procedure) |
| `F768` | complete formatter output (v1.6 FULL procedure) |

Encoder-batch restore across runs is permitted exactly per the intermediate-restore line
(Decisions_v16_AllCells §6): restore by content hash only where inputs are byte-identical,
determinism separately verified by the existing test, and both the hash and the fact of every
restore recorded in the v17 manifest under PROC-1. No arm *value* is restored from any prior
run.

### 2.2 Metrics — definitions fixed here

Retrieval, ranking, fusion, pool and budget are all unchanged from v1.6: dense + BM25, RRF
`k_rrf=60`, `candidate_pool=50`, seed 1337, budget **B = 1920 tokens**, take units in rank
order, include the unit that crosses B, stop. Provenance basis **S2** (own + absorbed)
primary, S3 (own only, the conservative floor) reported. [Pre-freeze amendment PF-1.]

For query `q` with gold span set `G(q)` (char offsets in original documents) and retrieved-
at-budget unit set `R(q)`:

- **`integrity_full(q)` = 1** iff every char of every span in `G(q)` is covered by the union
  of `source_ranges` over `R(q)`.
- **`integrity_single(q)` = 1** iff there exists a *single* unit `u ∈ R(q)` whose
  `source_ranges` cover every char of every span in `G(q)`. (For multi-span gold, one unit
  must cover all spans; if no such unit exists anywhere in the arm's inventory, the query is
  still scored 0 — feasibility is reported descriptively per §2.5 but never adjusts the
  score.)

Both are binary per query; rates are `n/176` (Track A) and `n/150` (Track B). The k/n lattice
reading from v1.6 applies.

**Declared mechanical sensitivity:** `integrity_single` increases mechanically with unit
size — a bigger unit contains a full span more easily. This is why no headline is taken from
`F768 − U256`, and why attribution runs through the decomposition below, which holds size
fixed where it matters: `S768` and `F768` share unit boundaries and sizes, so their contrast
isolates the edits; `S768` vs `U768-ws` isolates boundary placement plus the size
distribution the formatter's segmentation induces.

### 2.3 Decomposition (computed for both metrics, both tracks)

```
D_int_size  = U768     − U256
D_int_ws    = U768-ws  − U768
D_int_seam  = S768     − U768-ws
D_int_edit  = F768     − S768
D_int_total = F768     − U256          (check: sum of the four, exactly, on the lattice)
```

### 2.4 Cells, statistics, family

- **Primary, decision-bearing cell: A-MiniLM** (`all-MiniLM-L6-v2`, Track A test set,
  n = 176, `dev_fraction 0.2` split unchanged — dev is for pipeline debugging only and no dev
  number appears in the results document).
- Reported, non-decision-bearing: A-bge, B-MiniLM (n = 150). Absolute numbers are comparable
  only within an embedder (Template §B).
- Tests: `paired_bootstrap_diff` percentile CI + `paired_permutation_p`, `iters = 10000`,
  `seed = 1337`, `ci = 0.95`.
- **Declared family `F_INT` (decision-bearing), Holm-corrected, exactly two members:**
  `D_int_seam(integrity_single, A-MiniLM)` and `D_int_edit(integrity_single, A-MiniLM)`.
  Everything else — `integrity_full`, all other cells, all other contrasts — is descriptive:
  integer numerators, discordant counts, no test. One procedure per quantity (A5b);
  discordant `n01`/`n10` recorded beside every contrast, descriptively, never tested on.

### 2.5 Descriptive companions (report, never test)

Per arm and track: unit-count and unit-size distributions at budget; the number of queries
where no single unit in the *entire inventory* contains the full gold span (the feasibility
ceiling for `integrity_single`); recall@budget re-stated from the fresh run solely as a
reproduction check against v1.6's published values — any mismatch is an apparatus STOP, not a
finding.

### 2.6 Sealed predictions (all HYPOTHESIS under A1g; each names its cell — candidate
amendment 1 applied)

- **PE1-1 (A-MiniLM, `integrity_single`):** `D_int_seam > 0` — formatter boundary placement
  raises single-unit whole-span delivery over size-matched arbitrary cuts.
- **PE1-2 (A-MiniLM, `integrity_single`):** `D_int_edit ≥ 0` — the edits do not *reduce*
  integrity (dedup/absorption could in principle split provenance).
- **PE1-3 (A-MiniLM, `integrity_full`):** `F768 ≥ U768` at matched budget (descriptive
  scoring: direction only, no test).
- **PE1-4 (control, A-MiniLM, `integrity_single`):** `D_int_size > 0` — the mechanical size
  effect appears where it must. If it does not, the metric or the apparatus is suspect and
  everything else in E1 is quarantined pending a ruling.
- **PE1-5 (B-MiniLM, direction only):** the sign of `D_int_seam(integrity_single)` on Track B
  matches Track A's. Stated over B-MiniLM alone; no other prediction reaches Track B.

Scored at Gate 1 against this sealed text, on the named cells, and no others (§A1g, §A2,
AllCells §8).

---

## 3. E2 — the reading test (runs only if the §5 gate passes)

### 3.1 Design: oracle packages, retrieval removed

No retriever, no embedder, no index. For each test query and each arm inventory
(**primary contrast `F768` vs `U768`;** `U256` as descriptive third), construct a package:

1. Select the minimal set of the arm's units whose `source_ranges` overlap `G(q)`, in
   document order.
2. Pad alternately with the adjacent units (following, then preceding, by document order)
   until the package reaches **B2(q)** tokens; truncate the final unit at the token
   boundary to land on exactly B2(q). If the document is exhausted first, record the
   shortfall and pad nothing else.
3. Package text is the arm's own unit text (formatter arms use formatted text — that is the
   treatment). Unit order within the package is document order. No markers, headers or
   annotations are added by the harness to either arm.

**The budget is per query, not global. [Pre-freeze amendment PF-2.]**

> **B2(q) = max(1024, T_a(q) over every arm `a` included in E2 on that track)**, where
> `T_a(q)` is the token length of arm `a`'s minimal gold-covering unit set for query `q`.
> Every arm's package for query `q` is built to exactly B2(q) tokens, by the procedure above
> unchanged.

The design's one non-negotiable guarantee is **equal tokens within each pair**, because the
comparison is paired per query. Nothing requires the budget to be a global constant, and the
first draft of this plan conflated the two. B2(q) is deterministic from the frozen
inventories, symmetric across arms, fixed before any generation, and outcome-independent —
the budget is set by rule, not by result, exactly as `recall@budget` is.

**B2(q) > 8192 is an APPARATUS-STOP.** Nothing known approaches it; if it fires, diagnose,
do not accommodate.

Both arms therefore hand the generator the same number of tokens **per query**, containing
the same gold information; the only difference is how the pipeline packaged it.

**Reported descriptively in `Results_v17_E2_Reading.md`:** the distribution of B2(q) per
track, and the count of queries with B2(q) > 1024 attributed to the arm whose `T_a(q)` set
it. A reader must be able to see how often the budget escalated and which arm forced it.

### 3.2 Generator protocol

- Model: `claude-sonnet-5`, exact version string pinned in the manifest. Temperature 0. Fixed
  `max_tokens`. The prompt template is frozen at Gate 0 as `PROMPT_TEMPLATE` in
  `src/v17/reading.py`. Rendered here with the instruction on one logical line
  [Pre-freeze amendment PF-3]:

  ```
  Answer the question using only the provided context. Quote the answer as exactly as the context allows. If the context does not contain the answer, reply exactly: NOT FOUND.

  Context:
  {package}

  Question: {query}
  ```

  **The frozen artifact is canonical; this block is a rendering of it.** Where the plan's
  markdown and a frozen artifact differ in line-wrapping or whitespace, the artifact governs.
  Any *semantic* divergence between them is an APPARATUS-STOP, not a choice.

- **Determinism check before any test query runs:** 20 dev queries × 3 repeats per arm. If
  all outputs are byte-identical, single-run scoring. If not, the declared fallback is: 3
  runs per test query, score each, take the **median** per-query metric — chosen now, before
  any value exists.
- Arm order is interleaved per query; the generator never sees arm labels.

### 3.3 Scoring — objective primary, judge secondary, disagreement reported

- **Primary (objective, deterministic): token-F1** between the generated answer and the gold
  span text, after normalisation (lowercase; strip punctuation; collapse whitespace;
  normalisation code frozen at Gate 0). Multi-span gold: F1 against the concatenation in
  document order. `NOT FOUND` scores 0 unless the gold span is genuinely absent from the
  package — impossible by construction, now truly so: B2(q) is defined as at least the
  gold-covering set's own token length, so no package can be truncated below its gold.
  `GoldExceedsBudget` is retained as an assertion against B2(q) and is unreachable; if it
  ever raises, that is an APPARATUS-STOP. [Pre-freeze amendment PF-2.]
- **Secondary (binary, descriptive): exact containment** — normalised gold span text is a
  substring of the normalised answer.
- **Secondary (declared, LLM judge):** same model, blinded A/B: the judge sees the question,
  the gold span, and the two answers in randomised order under neutral labels, and picks
  better/equal. Judge determinism checked the same way as the generator. **The declared bias
  risk is that a fluency-preferring judge is correlated with the treatment, because the
  formatter produces fluency.** Therefore: the judge never overrides F1; agreement between
  judge and F1 is itself reported; and if they disagree on the primary contrast's direction,
  the disagreement is a stated finding and F1 decides.
- **Declared family `F_READ` (decision-bearing), exactly one member:** paired difference in
  token-F1, `F768` package vs `U768` package, Track A test set, A-track gold. Bootstrap +
  permutation as in §2.4 (F1 is continuous; the paired machinery applies unchanged). Track B
  packages: descriptive only. Discordant-direction counts (queries where F1 differs)
  recorded descriptively.

### 3.4 Sealed predictions (HYPOTHESIS; cells named)

- **PE2-1 (Track A, primary):** mean token-F1(`F768` package) − mean token-F1(`U768`
  package) > 0.
- **PE2-2 (Track A, descriptive):** exact-containment count higher for `F768` packages.
- **PE2-3 (Track A, descriptive):** judge agreement with F1's direction on the primary
  contrast, ≥ chance. If the judge favours `F768` and F1 does not, that pattern is *itself*
  the fluency-bias signature and is reported as such.

---

## 4. E3 — dose-response skeleton (NOT AUTHORISED; recorded so the shape is fixed)

Requires, in order, none of which starts now: a degradation scorer whose procedure and
threshold are frozen before any outcome is seen; a real degraded corpus (ASML legacy
documents — outside this repo, subject to ownership and confidentiality constraints that are
Shamik's to resolve); hand-labelled gold spans on it; and a registered **interaction**
prediction — the formatter-vs-naive difference increases across degradation strata and
approaches zero on the clean end, with Track B anchoring the clean end. A main effect without
the interaction does not satisfy E3. Everything else about E3 is deliberately unspecified
until its own pre-registration.

---

## 5. Gates and frozen consequences

**Gate 0 — freeze.** The agent: creates the `v17` directory and manifest; implements
`integrity_full`/`integrity_single` and the E2 package builder with unit tests (including:
multi-span gold; a span straddling two units scores `integrity_single = 0`; budget-crossing
unit included; decomposition sums exactly on the lattice); runs the metric tests green;
commits this document unchanged together with the metric code, prompt template, and
normalisation code. That commit is the freeze. Any wording change after it is a new
pre-registration.

**Gate 1 — E1 complete.** Results document `Results_v17_E1_Integrity.md`: predictions scored
against sealed text on named cells; decomposition tables both tracks both metrics; discordant
counts beside every contrast; feasibility ceilings; reproduction check against v1.6
recall@budget; run parameters; limitations. Then STOP for a ruling.

- **Branch INTEGRITY-CONFIRMED:** at least one of `F_INT`'s two members positive with
  `p_holm < 0.05`. Consequence: E2 authorised to run after the ruling.
- **Branch INTEGRITY-KILL:** neither member survives Holm. Consequence, frozen now: **E2 is
  cancelled and the reading-value claim is recorded as structurally unsupported.** The
  residual channel (equal-integrity fluency benefit) is *named* as the only surviving
  hypothesis and testing it requires a new pre-registration — it is not a licence to run E2
  anyway.
- **Branch APPARATUS-STOP:** PE1-4's control fails or the v1.6 reproduction check mismatches.
  Nothing is interpreted; diagnosis only; ruling before any further step.

**Gate 2 — E2 complete (if run).** Results document `Results_v17_E2_Reading.md`, same
discipline. Frozen consequence: if `F_READ`'s single member is null, the reading-value claim
**dies at matched information and matched tokens**, and the formatter's remaining case is
operational (hygiene, preservation, cost) plus the untested E3 interaction — and the internal
ASML report must say so in those words. If it is positive, the claim earned is exactly:
*formatter packaging improves extractive answer quality at equal token cost when the answer
is present* — nothing about retrieval, nothing about v1.6, nothing about deployment.

**No v1.7 outcome, on any branch, modifies any closed artifact or the white paper.**
Consequence wording against external documents is drafted only after a Gate ruling and only
with Shamik's authorisation.

---

## 6. Execution order for the agent

1. Gate 0 as specified. STOP if any existing test breaks — fix nothing outside `v17` scope
   without a ruling.
2. E1 fresh runs: A-MiniLM first (decision-bearing), then A-bge, then B-MiniLM. Memory notes
   per arm recorded as margins (both numbers), per the v1.6 practice.
3. `Results_v17_E1_Integrity.md`, self-checked before commit: every count and universal in
   the document names the procedure that produced it and that procedure is run against the
   final text (candidate item 7, applied in full — including to the results document's own
   summary sentences).
4. STOP. Deliver the results document and wait for the ruling.
5. E2 only on INTEGRITY-CONFIRMED plus an explicit ruling: determinism check first, then
   packages, then generation, then scoring, then `Results_v17_E2_Reading.md`, same
   self-check, STOP.
6. At every STOP: working tree clean, manifest current, no artifact outside `v17` touched.

## 7. Not authorised by this plan

E3 beyond §4's skeleton. Any formatter code change. Any gate/scorer implementation. Any edit
to closed artifacts, the white paper, or the brief. Any use of v1.7 numbers to revisit v1.6
or PW-1. Any test on any quantity outside `F_INT` and `F_READ`. Any disclosure-related
action — the ASML memo and the v3 consequence wording remain separate items on Shamik's
queue, untouched by this plan.
