# v1.8 INSTRUMENT-DIVERGENCE — pre-registration draft for agent execution
# (the formatter measured on RAGAS, and RAGAS measured against the apparatus)

**Status:** DRAFT FOR FREEZE. Becomes a pre-registration only at its Gate 0 freeze commit;
until then nothing is sealed. **No test-set spend before the freeze commit. Dev-set probe spend
is authorised from the Gate 0 ruling onward, bounded at 1,000 calls total across all probes.**
[Pre-freeze amendment PF-1.] No arm *value* is spent before the freeze on any set.
**Date:** 1 August 2026
**Experiment ID:** `v18` — own directory, own manifest, own results documents.
**Executing agent:** a second agent, distinct from the one running v1.7. Coordination rules
in §8 are mandatory.
**Authorised by:** Shamik, 1 August 2026 ("prepare what is required to test the formatter
against RAGAS by another agent"). Authorisation covers Gate 0 preparation and, after a Gate 0
ruling, the data collection run. It does not cover any release, packaging, or external
disclosure decision — those are explicitly reserved (§7).

---

## 0. What this experiment is

Two questions, one run:

1. **Track-1 data:** what does the field-standard judge-based framework (RAGAS-class
   metrics) report about the semantic formatter, evaluated exactly as the field would
   evaluate it — fixed-k retrieval, standard metrics, no apparatus corrections?
2. **Track-2 data:** where do the three instruments — judge-based metrics, objective answer
   scoring, and the frozen provenance record — agree and diverge on the identical pipelines,
   and is the divergence patterned the way fluency bias and size confounding predict?

One run produces both. The packaging and sequencing of any release built on this data is a
separate decision, deliberately not taken here — but §7 binds what any such release must
contain, and §7 freezes with the plan.

### What this experiment is not

- Not a second retrieval verdict. v1.6's matched-budget conclusion is closed and is **cited,
  never recomputed** (one procedure per quantity, A5b). No v1.8 number revisits v1.6, v1.7,
  or PW-1 on any branch.
- Not blind. v1.6's null and the bias hypothesis are known to everyone involved. Every
  prediction below is HYPOTHESIS under A1g. This is disclosed here and restated in the
  results document.
- Not a modification of anything: closed artifacts, white paper, brief, formatter code, and
  everything under `v17/` are untouchable. The formatter rule stands: preserve exact domain
  terms, identifiers and numbers verbatim. **One scoped exception to "frozen configs" is
  authorised in §10 — the cost guard's `max_usd`, raised in the freeze commit and reverted in
  the results commit.** [Pre-freeze amendment PF-4.]

### Pre-freeze amendments

Sixteen changes were made to this document between drafting and the freeze commit, in response
to Gate 0 and Gate 0(b) findings (`v18_Gate0_Findings_2026-08-01.md`, ruled in
`Decisions_v18_Gate0_2026-08-01.md` and `Decisions_v18_Gate0b_2026-08-01.md`; PF-12 in
`Decisions_v18_PF12_BatchAPI_2026-08-01.md`; PF-13 in
`Decisions_v18_G12_2026-08-01.md`; PF-14 in `Decisions_v18_G13_2026-08-01.md`; PF-15 in
`Decisions_v18_G14_2026-08-01.md`; PF-16 in `Decisions_v18_G15_2026-08-01.md`). The repository history would show them anyway; they are
listed so they are legible rather than merely discoverable.

| id | finding | change |
|---|---|---|
| **PF-1** | G1 | the status header forbade the dev probes §§2/6/9 require; narrowed to test-set spend, dev probes authorised under a 1,000-call bound |
| **PF-2** | G2 | the probe measured the response cache, not the model; repeats now bypass the cache and a fresh-call assertion makes a cached repeat fail loudly |
| **PF-3** | G3 | the ×3-everything fallback was over-broad and breached §6's ceiling; replaced by repeats targeted at the pair `F_BIAS` consumes |
| **PF-4** | G4 | the harness cost guard aborts the run mid-flight; §10 authorises exactly one edit outside `v18/`, scoped and reverted |
| **PF-5** | G5 | `claude-sonnet-5` has no dated snapshot; "exact version pinned" restated in its observable form |
| **PF-6** | G6 | Track B declares `dev_fraction: 0.0` and has no dev split; Track A's probe verdict governs both tracks as a stated assumption |
| **PF-7** | G7 | B2 telescoped to `U768 − U256` and carried no `F768` term; B2 deleted, `F_BIAS` reduced to B1 alone, PD-2 restated descriptively |
| **PF-8** | G8 | `ragas` absent; §3's second branch made the normal case, with formula sources recorded in the metric code |
| **PF-9** | G9 | the pinned model rejects `temperature`; "temperature 0" specified a call that cannot be made, so the sampling clause is restated and no parameter-based determinism claim remains |
| **PF-10** | G10 | `LLMClient` discards `response.model`, so PF-5's pin confirmed itself; `V18Client` subclasses inside `v18/` (v1.9's pattern) to capture it, keeping the cost guard bound |
| **PF-11** | G11 | the probe resolved its model from a harness default and measured `claude-opus-4-8`; the two model roles are separated by name, the probe is abandoned by rule, and a persistent spend ledger replaces the counter that could not survive a restart |
| **PF-12** | — | all test-set model calls move to the Batch API: same model, pins, prompts and call counts, half the per-token price |
| **PF-13** | G12 | the API accepts `custom_id` only on `^[a-zA-Z0-9_-]{1,64}$`, and every query id in both tracks plus PF-12's `:` separator violated it — the identity is re-encoded over closed vocabularies with a frozen query-index codebook |
| **PF-14** | G13 | the targeted pair carries three answers per query but the judge budget covers one; each answer is now judged exactly once and B1 is paired per answer, so both instruments score the same draw |
| **PF-15** | G14 | the identity collapsed two orthogonal coordinates — which answer a judgement concerns and which sub-call within a metric — so the grammar could not express the call plan (`cp` makes 5 calls, `ar` 9 on the targeted pair); an eighth field is added and the validity set is derived from the frozen call plan |
| **PF-16** | G15 | 101 of 15,960 judge replies (0.63%) were prose followed by valid JSON, in violation of the prompt's format instruction; `parse_json_object` is amended by ruling to a total, uniform, content-blind trailing-object rule — the identity on conforming replies, still refusing ambiguity, malformed JSON and wrong key shapes |

**Attribution.** PF-13 and PF-15 repair specifications made by the *ruling side* — the
`custom_id` grammar of `Decisions_v18_G12_2026-08-01.md` §1, which
`Decisions_v18_G14_2026-08-01.md` §4 assigns there explicitly. The executing agent's error at
G12 was the alphabet half of the API constraint: asserting the 64-character limit while never
validating the character set. Each is cited where it belongs.

All fifteen were settled **before any v18 arm value existed**. PF-16 was ruled
**after** collection and **before** any score existed — no metric value had been
computed from any reply when it was specified, and it conditions on no verdict. No amendment to this document is
permitted after the freeze commit; anything found later is a new pre-registration.

---

## 1. Arms, corpora, retrieval

- **Arms (three):** `U256` (naive 256), `U768` (naive 768), `F768` (complete formatter) —
  constructed by importing the v1.6 build procedures (identity over assertion; no
  transcription). `U768` is load-bearing: it separates size from editing *inside the RAGAS
  frame*, mirroring v1.6's decomposition.
- **Corpora/queries:** Track A test set (n = 176) and Track B (n = 150), unchanged.
  Embedder: `all-MiniLM-L6-v2` only (published primary). bge is out of scope; declared, not
  silent (no-silent-caps).
- **Retrieval:** the field-standard configuration this study exists to examine — dense +
  BM25, RRF `k_rrf = 60`, **fixed k = 5**, seed 1337. No budget matching anywhere in v1.8:
  the point is to measure what the standard frame reports, confound included.
- Encoder-batch restores by content hash permitted per the intermediate-restore line; hash
  and fact of every restore in the v18 manifest under PROC-1.

## 2. Generation

- Generator: `claude-sonnet-5`, fixed `max_tokens`. **Sampling parameters are omitted — the
  pinned model accepts no `temperature` (`400 ... deprecated for this model`), so no
  parameter-based determinism claim exists anywhere in v1.8; determinism is an empirical
  property to be measured, or, where unmeasured, assumed absent [PF-9].** The shared client's
  silent retry cached a `t=0.0` record for a call that never carried the parameter;
  `V18Client` never constructs it, and records the **actual request payload**, so the
  manifest describes calls that happened rather than calls that were asked for. Prompt: **the v1.7 E2 frozen
  prompt, reused verbatim by citation** (the file frozen at `e19dd35` is canonical) — one fewer
  free parameter, and it makes v1.8's objective scores comparable with E2's if E2 runs.
- **Version pinning, in its observable form [PF-5].** `claude-sonnet-5` is an alias with no
  dated snapshot, so there is no exact version string to request. The pin is therefore: the
  requested model id, plus the **`response.model` string logged on every call and asserted
  constant across the run** — any mid-run change is an APPARATUS-STOP — plus the run's start and
  end timestamps in the manifest. That is the strongest pin the surface offers; claiming a dated
  snapshot that does not exist would be a self-description with no procedure behind it.
  **Implemented by `V18Client` [PF-10],** which subclasses `LLMClient` inside `v18/` and
  overrides the provider call to keep `msg.model` — the parent discards it, so reading its
  cache record back would confirm the pin against the id we sent. The subclass pattern
  (v1.9's) is chosen *specifically so the shared cost guard still binds*; where the override
  duplicates provider-call code, a test hashes the parent's source and fails if `src/` moves
  underneath.
- Context: the k = 5 retrieved units, in rank order, joined by the standard harness
  separator. Answers generated per query per arm: 3 × 326 = 978 calls.
- **The determinism probe is abandoned by rule, and the branch selected without it [PF-11].**
  Four attempts produced no valid verdict: the first measured its own cache (the PF-2 assertion
  fired), two died on API credit exhaustion, and the fourth resolved its model from a harness
  default and measured `claude-opus-4-8` rather than the pinned model. The probe is **not
  re-run**, for three reasons in order: its only purpose was branch selection, and both
  targeted-repeat branches fit the frozen ceiling (17,642 against 25,000); PF-1's 1,000-call
  probe bound is treated as **consumed**, since cumulative probe spend is 334-1,018 and cannot
  be computed after two credit deaths; and assuming nondeterminism is the safe direction —
  median-of-3 over a deterministic model returns the deterministic value, so the conservative
  branch is valid under either truth and the cost fits.

  Therefore: **determinism unmeasured, recorded as such; both targeted-repeat branches active.**
  Generation runs 3x and judge calls run 3x, **Track A `F768`/`U768` only**, per PF-3's
  targeting. Every single-run number carries the strengthened caveat — *single sample,
  sampling nondeterminism unquantified, temperature pin unavailable.* The probe's INVALID
  artifacts are retained with their hashes; the spend range is recorded in the ledger as a
  range, attributed.

- **The two model roles are separated by name [PF-11].** Arm construction stays at the track
  default (`claude-opus-4-8`, cached, reproduces v1.6 byte for byte); generation and judging pin
  to §2's model. Both are named explicitly in the v18 run config, with a **per-call assertion
  that requested = configured**. Config fall-through to a harness default is how the probe
  burned 254 calls measuring the wrong model; no v18 call resolves its model by default again.

- **Operational orders carried from the wreckage [PF-11].** A persistent, file-backed **spend
  ledger** inside `v18/` records actuals from API usage rows and survives any interruption —
  the Gate 0 counter reset on every restart, which is why spend became uncomputable. The run
  phase **checkpoints per stage**; an interruption resumes from the last checkpoint. Under PF-12
  the batch ids are themselves the checkpoints.

- **Probe scope and the cross-track assumption [PF-6].** Track B declares `dev_fraction: 0.0`
  and has no dev split, so any probing would have run on Track A dev alone. With the probe
  abandoned the assumption is moot for branch selection, but its guard stands: finish reasons
  and output lengths are logged for every call on both tracks, and any truncation, refusal, or
  length anomaly is flagged descriptively.

- **Targeted repeats, as frozen [PF-3].** Repeats protect the tested family, and only `F_BIAS`
  is tested: generation 3x with per-query **median** token-F1 and judge 3x with per-query
  **median**, both **only for Track A `F768`/`U768`** — the pair B1 consumes. Every other
  arm-track and every other judge call is single-run, caveated as above.

## 2A. Execution mode — the Batch API [PF-12]

All test-set model calls (generation and judging, repeats included) run through the Anthropic
Message Batches API: **same model, same pins, same prompts, same call counts, half the
per-token price.** Batching changes *when* calls run, never *what* they contain — blinding
and order-randomisation happen at request construction, exactly as frozen.

Pipeline, forced by data dependency only: **Batch G** (all generation, ~1,682 requests) ->
collect, score token-F1 locally, construct judge inputs -> **Batch J** (all judge calls, ~15,960
requests, partitioned into <=10,000-request sub-batches) -> collect, compute contrasts, results
document.

- **`custom_id` is identity; the payload cache is banned in batch mode.** Every request carries
  `v18-{stage}-{track}-{arm}-q{index}-{metric}-a{answer}-s{sub}` — e.g.
  `v18-j1-B-u768-q149-cp-a0-s4` [PF-13, PF-15]. The 3x repeats are byte-identical payloads, so any payload-keyed store collapses them
  back into one sample — G2 in new clothing. The record is the API's own result rows, keyed by
  `custom_id`, persisted verbatim with a SHA-256 in the manifest. A test asserts repeats are
  distinct rows and that batch mode performs zero payload-cache reads or writes.

- **Every identity field is a closed vocabulary [PF-13].** The API accepts `custom_id` only on
  `^[a-zA-Z0-9_-]{1,64}$`. Every query id in both tracks violates that alphabet
  (`A-040-marlin-planner::syn`, `1911.07555::q5`), and so did the separator first frozen for
  this format, so Batch G was rejected at submission with zero spend. Free text is therefore
  removed from the identity: stage, track, arm, metric and repeat are two-or-fewer-character
  codes from frozen bijective tables, and the query is a zero-padded **index into a frozen
  codebook** (`v18/codebooks/query_index_{track}.json`, SHA-256 in the manifest). **`custom_id`
  and the codebook jointly constitute the identity** — that is the exact and only amendment
  to this section's "sole record", and it buys back the uniform-split parse as a structural
  property rather than a special case.

- **Two coordinates, because the domain has two [PF-15].** `{answer}` is which generated
  answer a judgement concerns; `{sub}` is the position within that metric's own call plan.
  They are orthogonal: context precision's five calls attach to *contexts* and to no answer,
  while answer relevancy's three attach to *each* answer. Collapsing them left the grammar
  unable to express the call plan — `cp` needs 5 ids per cell and `ar` 9 on the targeted
  pair, against 3 slots — and Batch J could not be built. The metric code table is untouched
  and remains a bijection onto the five metric names.

- **The validity set is derived, never enumerated in parallel [PF-15].** The legal
  `(stage, track, arm, metric, answer, sub)` tuples are generated **from** `CALLS_PER_QUERY_ARM`
  and the targeted-pair spec — the same objects the request builder consumes — so the
  census and the call plan cannot disagree: one is a function of the other. G14 happened
  because an identity was specified over "one call per metric" while the real plan sat frozen
  in the repository, readable, since Gate 0.

- **Judging splits into J1 and J2 [PF-15].** Faithfulness is extract-then-verify and stage 2's
  prompt depends on stage 1's reply, so the split follows from §2A's own "stage order is
  forced by data dependency only". J1 carries 14,278 calls, J2 the 1,682 verdict calls; the
  total is unchanged at 15,960. **Conduct clause:** building J2's prompts requires reading J1's
  extraction outputs, and that reading is *construction, not peeking* — confined to statement
  lists, with no F1 computed, no judge score aggregated, and no per-arm signal assembled before
  the results stage. The builder imports no scorer, and a test inspects its source to keep that
  true.

- **The acceptance census is mandatory before any submission [PF-13].** The complete
  cross-product of possible ids — every stage, track, arm, query, metric and repeat — is
  generated and validated against the API's real pattern as a test: 35,208 ids, all legal, all
  23 characters against the 64 limit. Not a sample and not the worst case reached by
  inspection. G12 happened because the length half of that constraint was asserted and the
  alphabet half was never checked; a census that stops at the convenient half is the
  mental-model failure wearing a census's clothes.
- **Partial failure is expected.** `errored` rows are collected and resubmitted under their
  original `custom_id`s, **bounded at two rounds per stage**; anything still failing is a STOP
  carrying the row-level errors, because a dropped request silently shrinks `n`.
- **Submission is idempotent, and a refusal is not a loss [PF-13].** An intent record (stage,
  request count, request-set SHA-256) is written *before* submission and the batch id
  immediately after. Intents carry a **state**: `submitted` means an id may exist, so an intent
  without one triggers adoption by match on request count and a sampled `custom_id` — an
  unambiguous match adopts, **anything ambiguous is a STOP, never a resubmission by default**.
  `rejected` means the API refused the set synchronously and nothing was created, so a fresh
  submission is not a duplicate. Without that distinction a rejected submission leaves an
  orphan the adoption logic can never resolve, and a legitimate retry STOPs — which is what
  Batch G's rejection produced.
- **Batches are the checkpoints.** A batch id is a durable pointer to results retrievable for 29
  days, so a crash, credit death, or machine loss between submission and collection loses
  nothing. This structurally retires the Gate 0 failure that discarded 194 calls of finished
  work.
- **Guard and ledger.** `max_usd` 150 as-computed stands; the guard's pricing model knows
  neither the Sonnet rate nor the batch discount and is like-for-like inflated, exactly as PF-4
  left it — a tripwire, not an invoice. The ledger takes actuals from per-row usage. Call
  counts are unchanged by batching: 17,642 projected, 25,000 ceiling, breach is a STOP.
- **No peeking between stages.** Batch G's answers arrive complete before judging begins.
  Nobody — agent or ruling side — reads answers, F1 distributions, or any per-arm signal
  between Batch G and Batch J beyond the mechanical checks (row counts, model constancy,
  resubmission triage). The results document is assembled once, after Batch J.
- **Wall clock, accepted.** Worst case ~24 h per batch round; with two stages and up to two
  retry rounds each the pessimistic envelope is a few days, the typical case hours. v1.9 waits
  longer; the spend-sequencing rule (no v1.9 call until v1.8's results commit exists) is
  unchanged.

## 3. The three instruments

**I1 — judge-based (RAGAS-class), the object of study.** Five metrics: context precision,
context recall, faithfulness, answer relevancy, answer correctness. Reference for the
reference-based metrics: the gold span text. **Implementation: the published formulas are
implemented directly; `ragas` is not installed and will not be [PF-8].** The pinned environment
under which v1.6's and v1.7's `recall@budget` reproduction checks pass (torch 2.13.0,
transformers 5.14.1, numpy 2.2.6) outranks the convenience of a library, and perturbing it to
obtain metric code would risk the apparatus those checks defend. **The metric code frozen at
Gate 0 is canonical over any library documentation**, and the exact prompts the judge receives
are part of the freeze. The formula sources — document and version consulted — are recorded in
the metric code's header comments as part of the freeze. A consequence to state in the results
document: I1 is a **reimplementation of RAGAS-class formulas, not RAGAS**, which slightly
qualifies §0's "exactly as the field would evaluate it".

Judge model: `claude-sonnet-5`, pinned in the observable form of §2 [PF-5] — `response.model`
logged on every call and asserted constant. Judge nondeterminism is handled by §2's
probe-and-targeted-repeat protocol applied to judge calls. Single-judge dependence is a declared
limitation, not a footnote.

**I2 — objective answer scoring.** Token-F1 of each generated answer against gold span text,
using the v1.7 normalisation code by citation (canonical at `e19dd35`). Deterministic; no
judge anywhere in I2.

**I3 — the frozen provenance record.** v1.6's published matched-budget values and
decomposition, **quoted with commit hashes, never recomputed.** I3 contributes no new
number to v1.8.

## 4. Contrasts and the single tested family

Per metric and track, arm contrasts `F768 − U256`, `F768 − U768`, `U768 − U256`, paired per
query, with `n01`/`n10` (or the continuous analogue: count of queries favouring each side)
recorded descriptively beside every net.

**Per-answer pairing for B1 [PF-14].** Track A's `F768` and `U768` carry three generated
answers per query (PF-3's targeted repeats), and the frozen judge budget covers three
answer-level judgements per (query, arm, metric). Ruled at G13: **each of the three answers is
judged exactly once** — no answer twice, none unjudged — and B1 is computed *per answer*
before aggregation. Reps pair by index (`F768` rep r against `U768` rep r; the draws are
independent, so any fixed pairing is exchangeable and index pairing is the one with no
discretion in it). For each query and each r: the judge-preference indicator on answer-pair r
minus the I2 token-F1 preference indicator on **the same two answers**; the per-query B1 value
is the **median of the three per-answer differences**, in that order — differencing medians
instead would compare a judge median and an F1 median drawn from different answers.

B1 is a *between-instrument* comparison, so this is not a stylistic reading of PD-3's "on the
identical answers": scoring the judge on one answer while token-F1 spans three would confound
instrument bias with generation-draw variance, which is the difference between measuring bias
and measuring noise. Descriptively, I1's answer-level values per (query, arm) are the median
over the judged answers and I2 is the median token-F1 over the same answers; **context-level
metrics stay single-judgement**, because the retrieved contexts are byte-identical across reps
and tripling them would buy nothing.

**Declared narrowing [PF-14].** PF-3 said the judge repeats measure judge variance. Under
per-answer pairing each judged answer is a fresh generation sample *and* a fresh judgement
sample, so the repeats cover the **joint** draw and the two sources are not separately
identified. Separating them serves no frozen prediction and would breach the ceiling. The
results document states this rather than leaving it implied.

**Tested family `F_BIAS` (decision-bearing), exactly one member, Track A [PF-7]:**

- **B1 (fluency excess):** paired per query: judge-preference indicator for `F768` over
  `U768` (from I1's answer-level metrics, direction of the per-query composite declared in
  the frozen code) minus the I2 token-F1 preference indicator for the same pair. Positive
  mean = the judge favours the formatter beyond what objective scoring supports.

With one member, Holm reduces to the plain p-value, and it is reported and labelled as such
rather than dressed as a correction.

**B2 is deleted [PF-7].** As drafted it was `(F768 − U256) − (F768 − U768)` on the context
composite, which telescopes exactly to `U768 − U256` — the `F768` terms cancel, so no test on
B2 could express any claim about what fraction of `F768`'s apparent gain is size. Adding a
ratio to recover the "majority" reading would have reintroduced a small, noisy denominator.

In its place, the **absolute-numbers pattern**: the results document reports, per context metric
and per track, the three contrasts `F768 − U256`, `U768 − U256`, and `F768 − U768` as values
with their discordant counts — descriptive, no test, no ratio. The reader does the subtraction.

Statistics for the single tested member: `paired_bootstrap_diff` + `paired_permutation_p`,
`iters = 10000`, `seed = 1337`, `ci = 0.95`. Everything outside `F_BIAS` — every raw RAGAS
score, every Track B number, every per-metric contrast — is **descriptive**: values, discordant
counts, no test, no mechanism prose.

## 5. Sealed predictions (all HYPOTHESIS under A1g; cells named)

- **PD-1 (Track A, descriptive):** RAGAS context-level metrics favour `F768` over `U256` at
  fixed k — the standard frame reports the formatter as an improvement.
- **PD-2 (both tracks, descriptive) [PF-7]:** on the context-metric composite, the size contrast
  `U768 − U256` will be **at least as large as** the residual `F768 − U768`. Scored by direction
  comparison of the two point values, labelled descriptive, never tested. (As drafted this
  predicted "the majority of the gain", scored on a family member that telescoped away the
  `F768` term; predicting a direction between two reported numbers is what the design can
  actually support.)
- **PD-3 (Track A, `F_BIAS`'s single member B1):** judge-based answer metrics favour `F768` over
  `U768` in excess of token-F1 on the identical answers — the fluency-bias signature,
  measured.
- **PD-4 (Track A, descriptive, control):** token-F1 `F768 − U768` ≈ 0, consistent with the
  frozen provenance record; `F768 − U256` may be positive at fixed k (that is the size
  effect operating end-to-end, and it is expected, not a finding for the formatter).
- **PD-5 (Track B, direction only):** B1's sign on Track B matches Track A's.

Interpretations are pre-committed. PD-2 is descriptive, so "confirmed" means its stated
direction holds between the two reported point values; PD-3 is the tested member. PD-2 and PD-3
confirmed → the standard frame's favourable report is attributable to size plus judge
preference, and **no formatter claim may be built on I1**. PD-2/PD-3 refuted → the bias
argument is weakened, that is stated
plainly wherever v1.8 is reported, and judge-based monitoring gains the first controlled
validation on a transformed corpus — a publishable result in its own right. Either branch
is a result; neither branch reopens v1.6.

## 6. Costs, and a spend gate

At Gate 0 the agent reports, before any test-set call: exact call counts per stage
(generation, per-metric judge calls, repeats), the probe results, and the projected total.
**No test-set spend before the freeze commit.** Dev probe spend is bounded at 1,000 calls
total [PF-1].

The **25,000-call ceiling stands unchanged**. With the probe abandoned and both targeted-repeat
branches active by rule [PF-11], the projection is no longer contingent and is **frozen at
17,642 end-to-end test-set calls**:

| stage | calls |
|---|---:|
| generation, base (326 queries × 3 arms) | 978 |
| generation, targeted 3× repeats (Track A `F768`/`U768`) | +704 |
| judging, base (326 × 3 arms × 12 metric calls) | 11,736 |
| judging, targeted 3× repeats (answer-level, Track A `F768`/`U768`) | +4,224 |
| **total** | **17,642** vs 25,000 |

Batching does not change these counts [PF-12] — only the price per token. A breach **at run
time** is a STOP, detected by the persistent ledger rather than by a per-process counter, and
the trim is a ruling rather than the agent's discretion.

**Affordability is checked before each submission, not discovered mid-run.** Two Gate 0 probe
attempts died on API credit exhaustion; the ledger's `affordability_check` runs against the
projection before every batch goes out.

**The harness cost guard [PF-4].** Separately from the call ceiling, `LLMClient` aborts on
`est_usd > cost_guard.max_usd`, and it prices every provider at Opus rates ($5/$25 per MTok)
regardless of the model actually called. At the drafted `max_usd: 60.0` the single-run branch
aborts roughly 60% of the way through. §10 authorises raising it to **150.0** in the freeze
commit and reverting it in the results commit. The guard's pricing inaccuracy is **documented,
not fixed** — repairing shared pricing code mid-programme for one run's convenience is scope
creep, and at 150 the guard still binds meaningfully (~1.5× the projected single-run figure,
computed the same wrong way, so like-for-like).

## 7. Release conditions — frozen with this plan, binding on every future packaging decision

The sequencing/packaging decision is deliberately open. Whatever is decided later:

1. Any external statement drawing on v1.8's I1 results **must present the full
   three-instrument record for the same pipelines** — I1, I2, and I3 with its matched-budget
   null — in the same document, with equal prominence. The favourable increment alone is
   forbidden by this plan's own terms (completeness over the declared class; the class is
   declared here: all three instruments, both tracks, all three arms).
2. No external statement may describe I1-favourable results as evidence the formatter
   improves retrieval. The pre-committed reading of §5 governs.
3. Nothing in v1.8 changes the disclosure calculus: any external release remains gated on
   the pending IP ruling, which this plan does not touch.

These conditions freeze with the plan. A later decision can choose *whether* and *where* to
publish; it cannot choose *less than this* about what an honest publication contains.

## 8. Coordination with the running v1.7 agent — mandatory

- Nothing under `v17/` is read-as-mutable, written, or locked. v18 state lives under `v18/`
  only. Shared read-only caches (encoder batches by content hash) may be restored, never
  written concurrently: if a needed cache entry is absent, **build it only when no v17 cell
  is running** (the memory margins are thin — v1.6 recorded 224 MB free against a 393 MB
  known failure point; two concurrent encodes are how that margin dies).
- Heavy local stages (encoding, indexing) wait for v17 cell boundaries; API-bound stages
  (generation, judging) may run concurrently.
- If both agents must touch the repo, v18 commits only under `v18/` paths plus its own
  documents; any merge conflict is a STOP, not a resolution.

## 9. Gates

**Gate 0 — build and freeze-readiness.** Arms built (import, not transcription); I1/I2
implemented with unit tests (including: judge-prompt snapshot tests; composite-direction
tests; normalisation by citation; a synthetic case where judge and F1 disagree by
construction, verifying B1's sign convention; the probe's fresh-call assertion; the
`response.model` constancy assertion; the guard-revert check); determinism probes run on dev
only within the 1,000-call bound; cost projection per §6. **STOP for a ruling** — findings
expected, per v1.7's precedent. *This stop occurred and was ruled in
`Decisions_v18_Gate0_2026-08-01.md`; the eight amendments above are its output.*

**Gate 0(b) — the second stop, and the last one.** Four probe attempts produced no valid
verdict and three further findings (G9–G11), ruled in `Decisions_v18_Gate0b_2026-08-01.md`.
Its output is PF-9…PF-11: the sampling restatement, `V18Client` with payload recording and the
parent-source-hash test, model-role separation with per-call assertions, the spend ledger, and
incremental checkpointing. PF-12 (Batch API execution) followed. **No further Gate 0 stop is
needed — everything discretionary is ruled.**

**Then: one freeze commit** — plan + code + prompts + tests + the probe disposition (the
INVALID artifacts' hashes, the spend range, the branch-by-rule declaration) + the 17,642
projection + the `max_usd` 150 raise. **The run starts only after the balance check** against
the ledger's projection.

**Gate 1 — data complete.** `Results_v18_InstrumentDivergence.md`: predictions scored
against sealed text; the three-instrument table per track; **`F_BIAS` = B1 alone, with
single-member Holm stated as the identity it is**; all descriptive companions with discordant
counts; the probe disposition (abandoned by rule, determinism unmeasured, every single-run
number caveated); costs **actual vs projected against the ledger**; limitations including
non-blindness, single judge, fixed-k-by-design, and the unavailable temperature pin; item 7
self-check with its output in the record. Then STOP. No packaging, no release drafting, no
sequencing recommendation from the agent — that decision is Shamik's, taken on the complete
record.

## 10. Not authorised

Any external release or draft thereof. Any recomputation of v1.6/v1.7 quantities. Any
additional metric, arm, judge, or test not named here (anything interesting the run surfaces is
an observation for the results document and a candidate for a future pre-registration). Any use
of v1.8 to argue about v1.7's branches or v1.6's KILL.

Any edit outside `v18/` paths and v18 documents, **with exactly one authorised exception
[PF-4]**: `cost_guard.max_usd` in `config/default.yaml` is set to `150.0` in the freeze commit
and reverted to `60.0` in the results commit, both changes stated in their commit messages. No
other line of that file, and no other file outside `v18/`, may be touched. The guard's
Opus-rate pricing is documented, not repaired.
