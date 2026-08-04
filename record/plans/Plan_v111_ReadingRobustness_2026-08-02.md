# v1.11 READING-ROBUSTNESS — pre-registration draft for agent 1
# (four cheap attacks on the reading claim, answered before a reviewer asks them)

**Status:** DRAFT FOR FREEZE. Becomes a pre-registration only at its Gate 0 freeze commit.
**Date:** 2 August 2026
**Experiment ID:** `v111` — own directory, own manifest, own results document.
**Executing agent:** agent 1 (owns the v1.9 reading harness this extends; imports v1.8's
batch machinery read-only).
**Authorised by:** Shamik, 2 August 2026 ("Draft it").
**Cost envelope:** ≈ 2,100 generation calls, all via the Batch API, ≈ **$15**. No judge, no
embedder, no encode. Call ceiling **4,000**; breach is a STOP.

Standing orders in force, restated once: models are plan-pinned, never config-resolved,
asserted at construction and against `response.model` per call; **every repetition's output
is persisted, never only its summary**; every specification is exercised against the real
inputs and the real acceptors at Gate 0; closed artifacts and `v17/`–`v110/` are read-only
(imports by identity encouraged, modification forbidden); the personal documents in the
working folder remain out of scope; preserve exact domain terms, identifiers and numbers
verbatim wherever text is handled.

**### Pre-freeze amendments

Three Gate 0 findings, ruled in `Decisions_v111_Gate0_2026-08-02.md`.

| id | finding | change |
|---|---|---|
| **PF-G1** | v1.9 never persisted package text, so E-B cannot reuse by hash | census decides **rebuild**; **v1.11 persists every package text it constructs**, both arms, all stages — promoted from advice to requirement |
| **PF-G2** | E-A's same-doc package is unconstructible for six `U768` queries | `F_SAFE` over the **170 constructible pairs**, six listed, their `F768` sides reported unpaired, scope clause with PS-1, corpus requirement recorded |
| **PF-G3** | v1.8's parser hard-asserts its prefix and field count; `v18/` is read-only | §6's "extended" → **parallel grammar under the imported acceptor** |

Settled before any v1.11 generation call existed. No amendment after the freeze commit.

Contamination disclosure:** nothing is blind. v1.9's +0.1106 and 15:1, v1.10's arms, and
the motive to defend a positive result are known. Every prediction is HYPOTHESIS under
A1g. This experiment exists to *attack* the reading claim cheaply; a refutation is a
result, not a failure.

---

## 1. E-A — the unanswerable control (completes the metric pair)

**Construction, free by provenance.** For each Track A test query and each arm
(`F768`, `U768`), two unanswerable packages:

- **cross-doc:** the package of a different document's query (the PR-0 mismatch
  machinery, successor-with-wraparound at seed 1337) — answer absent, off-topic.
- **same-doc (the hard case):** a package built by the frozen v1.9 procedure but from the
  arm's units of the *same document* with **every gold-overlapping unit excluded** —
  on-topic, plausible, provably answerless. Gate 0 census: an executed check that zero
  constructed package overlaps its query's gold span by provenance, every package, both
  arms.

Generation: single-run, frozen v1.9 prompt (which defines the NOT FOUND token), Sonnet
plan-pinned. 176 × 2 arms × 2 constructions = **704 calls**.

**Metric:** `false_answer(q)` = 1 iff the reply is anything other than NOT FOUND. Rates on
the k/n lattice, per arm and construction, with discordant counts.

**Tested family `F_SAFE`, exactly one member, Holm = identity:** the paired difference in
false-answer rate, `F768` − `U768`, **same-doc construction**, Track A, declared over the
**170 constructible pairs** [PF-G2].

**The estimand's domain, stated before any value exists.** For six queries the same-doc package
cannot be built for `U768`: excluding gold-bearing units leaves that arm no unit in the gold
document. The contrast is *undefined* there — there is no measurement to exclude — so `F_SAFE`
is declared over the population where both sides are constructible. This is NOT the exclusion
rejected at v1.7's Gate 0, where the six straddle queries were measurable in every arm and
their membership correlated with the mechanism under test. The six:

- `A-000-kestrel-indexer::f4` — `U768` has no non-gold unit in the gold document
- `A-008-quartz-resolver::f4` — `U768` has no non-gold unit in the gold document
- `A-012-ridge-indexer::f4` — `U768` has no non-gold unit in the gold document
- `A-019-crag-broker::f4` — `U768` has no non-gold unit in the gold document
- `A-023-harbor-sharder::f4` — `U768` has no non-gold unit in the gold document
- `A-036-halcyon-cache::f4` — `U768` has no non-gold unit in the gold document

**The six `F768`-side packages that DO construct are still generated and reported**,
descriptively and unpaired, in their own table. Six paid-for measurements are not discarded
because their partners cannot exist.

**Scope clause, travelling with PS-1's result wherever it goes:** the safety finding is
established on documents large enough to admit the control; the six smallest documents are
outside its domain. A scope note, not a bias — and the reader gets to know it.

**Corpus observation, recorded.** These same six short documents have now produced three
distinct symptoms across two experiments: v1.9's padding exhaustion, v1.9 §7's shortfall table,
and this. **Minimum document length relative to unit size** enters the candidate file as a
corpus-design requirement, binding on the future mid-difficulty corpus before it is built. Bootstrap +
permutation as standard, seed 1337.

**PS-1 (sealed):** the formatter does not increase false answering — supported iff the
point estimate ≤ 0, or the difference is not significantly positive AND the point estimate
is < +0.05. A significantly positive difference REFUTES PS-1 and is flagged as a safety
finding about the formatter, reported with the same prominence as v1.9's positive.
Cross-doc: descriptive companion (expected near-zero false answers for all arms; if not,
that is its own observation).

## 2. E-B — the second generator

Track A, the frozen v1.9 `F768`/`U768` packages (reused byte-identical by hash, or rebuilt
by the frozen procedure — census decides which and records it), generated single-run by a
**Haiku-class model**: exact model id enumerated from the API's model list at Gate 0 and
frozen there (the id is an acceptor fact, not a guess — the plan deliberately does not
name it). 176 × 2 = **352 calls**. Token-F1 by the frozen normalisation (import by
identity); NOT FOUND counts.

- **PH-1 (descriptive, direction only):** mean F1(`F768`) − mean F1(`U768`) > 0.
- **PH-2 (descriptive, direction only):** the abstention asymmetry (`U768` > `F768`)
  replicates.

Single-run is declared: per-query pairing is noisy under nondeterminism, but both
predictions are rate/mean-level over n = 176, where single draws estimate adequately;
the variance caveat is mandatory.

## 3. E-C — prompt-wording sensitivity

Two variants of the generation prompt, frozen verbatim here; both retain the NOT FOUND
token (required for mechanical scoring — token-free prompts are a declared limitation),
varying emphasis and position:

- **V1 (de-emphasised, trailing):** `Answer the question using only the provided
  context.\n\nContext:\n{package}\n\nQuestion: {query}\n\nIf the context does not contain
  the answer, reply exactly: NOT FOUND.`
- **V2 (minimal, no exactness instruction):** `Use the context to answer the
  question.\n\nContext:\n{package}\n\nQuestion: {query}\n\nReply NOT FOUND if the answer
  is not in the context.`

Track A `F768`/`U768` packages, single-run per variant, Sonnet: 176 × 2 × 2 = **704
calls**. Descriptive per variant: mean F1 both arms, the F768−U768 gap, NOT FOUND counts
both arms, discordant direction counts. **PV-1 (descriptive):** the gap's sign and the
abstention asymmetry's direction persist under both variants. No test; the reader
compares three prompts' tables.

## 4. E-D — the containment re-score (code only, zero calls)

The PR-2 hypothesis, tested: recompute exact containment for the **existing v1.9 answers**
against the *formatted package text* (in addition to the already-reported original-text
containment), same normalisation, procedure frozen here before any value is seen.
Descriptive: the two containment tables side by side. If `F768`'s containment rises
against its own text while `U768`'s is stable, the §2-of-Gate-1 hypothesis is supported;
if not, it is killed. Either lands in the paper's PR-2 discussion as a measurement.

## 5. E-E — the third preparation (methodology breadth)

Does *prepended context* (v1.10's real blurbs) help reading at matched information, the
way repair does? Self-contained pair, Track A: `C768` packages (the v1.10 `C` arm's
blurbed units — base inventory is v1.6's `U768`, so the comparison is clean) versus
`U768` packages, both built by the frozen v1.9 procedure with B2(q) taken over **this
pair** (blurb text counts toward package budget; gold-overlap selection by provenance
unchanged — blurbs carry no ranges and cannot affect selection). Single-run, Sonnet:
176 × 2 = **352 calls**. Descriptive only: mean F1, gap, NOT FOUND counts, direction
counts. **PE-1 (descriptive, direction only, sealed with honest uncertainty):** no
directional prediction is made — blurbs might aid reading (more context) or dilute it
(more tokens between the model and the span); whichever way it lands, the point is that
the methodology measures it. This arm's `U768` packages are built under this pair's
budgets and are **not** comparable to v1.9's numbers; stated in the table header.

## 6. Costs and machinery

| stage | calls | est |
|---|---|---|
| E-A | 704 | ~$5 |
| E-B (Haiku) | 352 | <$1 |
| E-C | 704 | ~$5 |
| E-E | 352 | ~$3 |
| E-D | 0 | $0 |
| **total** | **2,112** | **≈ $14** |

All generation through the v1.8 batch client, imported read-only (identity asserted);
custom_id: a **parallel grammar under the imported acceptor** with prefix `v111` and an `exp` field for E-A/…/E-E
— the derived-validity pattern: legal tuples generated from this plan's call table, census
against the API's pattern over the full cross-product before submission. Intent records,
two-round resubmission, ledger, checkpoint-by-batch: all as PF-12 established. One batch
per stage is acceptable; stages are independent (no ordering dependency — they may share
one batch if the builder prefers, declared in the manifest).

## 7. Gates

**Gate 0 — build, census, STOP.** The census list: unanswerable packages' zero-gold-
overlap executed check; package reuse-vs-rebuild decided by hash and recorded; the Haiku
model id enumerated from the live model list; prompt variants byte-frozen; custom_id
census over the derived cross-product; batch-client import identity test; every-output-
persisted verified by test (the v1.9 lesson, now load-bearing). Then STOP for a ruling —
findings expected, per five precedents.

**Gate 1 — results and STOP.** `Results_v111_ReadingRobustness.md`: PS-1 scored first
(it is the safety result), then PH/PV/PE descriptively with every table carrying
direction counts; E-D's two containment tables; costs actual vs projected; limitations
(single-run stages' variance caveat, token-retaining prompts, difficulty-extremes
inheritance); item-7 self-check with output in the record. No interpretation beyond
scoring lines; no paper text; no edit to any closed artifact. STOP for the ruling.

## 8. Not authorised

Any spend beyond the ceiling. Any judge call. Any new corpus work (the mid-difficulty
corpus and dose-response are explicitly out of scope). Any modification outside `v111/`
paths and this document. Any use of v1.11 to revisit closed verdicts — including v1.9's:
if E-B or E-C fail to replicate the direction, that is scope information about the
reading claim, reported descriptively, and what it means is the Gate 1 ruling's to say,
not the report's.
