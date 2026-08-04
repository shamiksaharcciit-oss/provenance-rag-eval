# Experiment Plan Amendment v1.5 — Small-to-big / parent-child retrieval (M7)

**Owner:** Shamik Saha · **Date:** 28 July 2026 · **Amends:** v1.1 base plan.
**Supersedes:** v1.4 (`preregistration_v14.json`, frozen 2026-07-28T10:50:48Z,
**SUPERSEDED BEFORE RUN — never executed, no data observed**).
**Status: DRAFT — NOT FROZEN.**
**Criteria template:** `Amendment_Criteria_Template.md` v1.1 (four-branch + demonstrated-failure guard rule).

---

## 0. Revision note — what changed from v1.4, and why

Recorded plainly because the audit trail is the point.

**(a) The premature freeze.** v1.4's `frozen_utc` was stamped on an explicit instruction to
"stamp `frozen_utc`, commit with the hashes, then run"; further blocking items then arrived
across three subsequent review documents. v1.4 is **not unfrozen** — the seal's value is its
monotonicity, and a freeze that can be undone with a sufficiently reasonable rationale is not a
commitment device. It stands as stamped, marked superseded, and the redesign freezes once here.
The integrity property pre-registration buys is **pre-data, not pre-timestamp**; no run was
executed and no result observed at any point in the sequence.

**(b) The fixed-k volume bias — the reason for the redesign.** v1.4 §4 mandated scoring the
child and never the parent, which prevented parent-dilution and, in the same stroke, created
its mirror. At fixed k a 128-token child retrieves ~6× less text than a 768-token parent
(5×128 = 640 vs 5×768 = 3840). Measured on Track A C0: parents@5 = 0.790 against children@5 =
0.4886. H7 as written would have returned REJECT_HARM on both tracks for a measurement-design
reason, indistinguishable in the write-up from real harm.

**(c) The headroom bound, invalidated by (b).** v1.4 §2 scoped H7 to Track B using the ceiling
gap (1 − r@10) — correct when new small units could *surface* gold that large units missed.
Under the redesign the parent inventory is set-identical to the baseline, so the treatment can
only **reorder**. §2 is rewritten around `r@∞ − r@5`.

**(d) C4's non-derivable provenance.** Formatter units carry merged, disjoint sentence ranges
spanning *more* original text than the unit's own text (one C4 unit: 108 ranges, span 7492
chars against text 5371), over edited text whose offsets are not linear. Offset arithmetic
cannot map a C4 child back to original offsets, so `ProvenanceNotDerivable` is raised rather
than guessed — the alternatives were handing children the parent's ranges (the dilution defect
itself) or interpolating across edited text (fabricated provenance).

**(e) Sentence alignment — re-decided, not inherited.** It was originally adopted to give C4
derivable child provenance. Under (b) children only *rank* and are never scored, so that
necessity evaporated. It is **kept on the independent uniformity ground**: child cutting
quality drives ranking quality, so condition-asymmetric cutting would be a machinery advantage
in the one place that now determines the entire result. Recorded as re-made rather than carried
forward, because superseded requirements surviving as unexplained design is its own failure mode.

**(f) Calibration data source, declared.** The parents@5 = 0.790 / children@5 = 0.4886
calibration was measured on Track A **test**. It is a property of the *baseline configuration*
— the token volume a fixed k delivers — not a treatment outcome, and it motivated a
measurement-validity repair rather than a hypothesis fitted to an observed result. From here,
calibration runs on Track A **dev only**, never Track B (`dev_fraction: 0.0` — every query is
test on the primary track). The §2 headroom bound is computed from v1.3 **test** artifacts
extended in k, under the admissibility principle in §2.

---

## 1. Why this, and why now

Next on the retrieval-stack roadmap, and v1.3's diagnosis promoted it: reranking harm
concentrated where first-stage recall was already high (r = −0.853 with baseline recall),
so the headroom is in the **first stage**, not post-hoc reordering.

## 2. Headroom bound — `r@∞ − r@5`

**`r@10 − r@5` is the wrong bound.** It measures reordering *within* an existing shortlist,
which would be right if best-child scoring were a local re-rank. It is not. Under
`max`-over-children, a parent whose whole-unit embedding is diluted — one relevant passage
averaged with ~700 unrelated tokens — can sit at rank 200 under whole-unit scoring and rank 3
under best-child scoring, because the child carrying that passage is embedded alone. Nothing
confines the movement to the top-10. **That dilution-rescue is the mechanism**, and it is why
the redesign preserves small-to-big rather than hollowing it out.

The true bound is `recall@∞ − recall@5`, where `recall@∞` is **coverage**: the fraction of
queries whose gold lies in *some* indexed unit.

Measured (`scripts/headroom_bound.py`; v1.3 test artifacts extended in k; bge-base;
`--no-sweep` baseline config verbatim). Every `r@5` and `r@10` reproduces v1.3's published
values exactly, confirming the baseline configuration matches the one the experiment will run.

| Track | Cond | units | r@5 | r@10 | r@50 | **r@∞** | r10−r5 | r50−r5 | **r∞−r5 (the bound)** |
|---|---|---|---|---|---|---|---|---|---|
| A | C0 | 90 | 0.790 | 0.847 | 0.977 | **1.000** | +0.057 | +0.188 | **+0.210** |
| A | C2 | 90 | 0.852 | 0.881 | 0.972 | **1.000** | +0.028 | +0.119 | **+0.148** |
| A | C4 | 90 | 0.835 | 0.875 | 0.989 | **1.000** | +0.040 | +0.153 | **+0.165** |
| B | C0 | 378 | 0.353 | 0.473 | 0.700 | **1.000** | +0.120 | +0.347 | **+0.647** |
| B | C2 | 378 | 0.387 | 0.473 | 0.693 | **1.000** | +0.087 | +0.307 | **+0.613** |
| B | C4 | 379 | 0.400 | 0.507 | 0.740 | **1.000** | +0.107 | +0.340 | **+0.600** |

**Track B's pool is ~3–4× Track A's.** The scoping of H7 to Track B therefore survives the
correction, on corrected reasoning rather than by luck.

**Coverage is complete (`r@∞` = 1.000) on every condition of both tracks — including C4.**

*Two limitations on how far that result reaches.*

**(a) For C0 and C2 complete coverage is expected by construction**, so the bound collapses
to `1 − r@5` there. With contiguous chunking every character sits in some unit, and under
the `any` overlap variant a gold span is covered by definition. The measurement was still
worth taking — it was the only way to find out whether **C4** was the exception, and C4 is
the informative result.

**(b) What is retired is narrower than "no gold was lost".** Coverage is measured against a
unit's *claimed* ranges, and a C4 unit's ranges are wider than its own text — the canonical
unit absorbs its duplicates' ranges (108 ranges / 7492 chars against 5371 chars of text). A
gold span sitting in a deleted duplicate is therefore counted as covered by the canonical
unit, whose text is a near-copy rather than that text. Retired: *no gold span falls outside
the union of claimed ranges.* **Not** retired: *no gold text was removed by dedup.* Those
coincide only if absorbed duplicates were genuine duplicates — very likely, and recorded
here as an explicit assumption rather than left implicit.

**The spread between the columns says how far reordering must reach**, and the two tracks
differ sharply:

- **Track A**: `r@50` is already 0.972–0.989, so almost the entire pool sits *within* the top
  50. Reordering has a short distance to travel.
- **Track B**: `r@50` is 0.693–0.740 against `r@∞` = 1.000, so **~26–30 points of the pool lie
  beyond rank 50**. Much of Track B's larger pool is *deep*, reachable only by the dilution-rescue
  mechanism moving a unit a long way. That is where the mechanism's claim is strongest, and it is
  also the part least likely to be realised.

This reinforces the caveat below rather than softening it: Track B has more addressable gold
*and* has to move it further.

**Two caveats, stated so the bound is not misread.**

*It is a bound, not a prediction.* The realistically achievable fraction is a small share of it
on both tracks. A large pool means the test is *capable* of expressing an outcome, not that an
outcome is expected.

*Track-level scoping only.* Per-condition pools inside a track are within noise at n=176/150.
The bound scopes the primary hypothesis to a track; it must **not** be used to drop or select
conditions.

**Admissibility of the data source.** Computed from v1.3 **test** artifacts extended in k.
Quantities that *bound what an experiment could show* are admissible pre-data; quantities that
*indicate what it would show* are not. A headroom analysis can only shrink or cancel an
experiment — it cannot manufacture a positive — and that asymmetry is what makes it safe on
spent test data. Precedent: v1.4 §2's ceiling-gap table came from the same source and was
approved in writing as the model for doing headroom before the hypothesis.

**`recall@∞` also earns its keep independently.** `recall@∞ < 1` for a condition means that
condition's pipeline **loses gold outright at any k**. C4 is the one to watch: the formatter
edits and deduplicates, and a gold span sitting in a duplicate whose ranges were not absorbed
into the canonical unit is unreachable at any k — a genuine treatment defect, invisible in
every number reported to date and paper-relevant well beyond M7.

## 3. Design

An **orthogonal axis**, not a new condition. Applied to **C0, C2, C4**. C1 is excluded (its
semantic chunker sets its own boundaries).

### Child construction — ONE rule across all three conditions

Split the condition's indexed text into sentences; greedily accumulate sentences into a child
until adding the next would exceed `child_tokens`; emit. A sentence longer than `child_tokens`
alone is hard-cut at a token boundary.

`child_tokens` is a **ceiling, not a size** — conditions will not land on identical
distributions. **Report the realized child token distribution (mean, median, p10/p90) per
condition**, as a fact the reader needs and a diagnostic if something looks strange.

One rule across three corpora, so the only thing differing between conditions is **the corpus,
not the machinery**. Sentence-aligned children are probably better ranking units than arbitrary
cuts, which raises all three baselines — the conservative direction.

### Parents — set-identical to the baseline unit inventory

| Condition | Child (ranks only) | **Parent (scored and delivered)** |
|---|---|---|
| C0 | sentence-aligned cut of raw text | the enclosing 768-token naive chunk = **C0's baseline unit** |
| C2 | sentence-aligned cut of raw text, **with the blurb prepended** | enclosing naive chunk + blurb = **C2's baseline unit** |
| C4 | sentence-aligned cut of formatted text | the enclosing 768-token cut of formatted text = **C4's baseline unit** |

**C4's primary parent is its baseline unit, not the formatter-marked section.** Marked-section
parents move to a **declared secondary arm**, reported separately with the width asymmetry
stated. This removes the last machinery asymmetry from the primary.

**C2 children are `blurb + child text`; `child_tokens` is the ceiling on the child *text*, with
the blurb prepended on top.** That is what contextual retrieval actually does — context on
every indexed unit — and it keeps C2's child text directly comparable to C0's. Children are
used only for ranking, never scored or delivered, so child size carries no volume consequence.
**Report the mean blurb-to-child token ratio per track**: if C2's ranking underperforms,
near-duplicate sibling vectors is the first hypothesis and the ratio is how to check it.

## 4. Retrieval, scoring, and the guard

### Both arms produce parent rankings of identical depth, per modality, and fuse at parent level

This is load-bearing. `Retriever` builds both indexes over whatever unit list it is handed and
truncates each modality to `index.candidate_pool` before fusing. Hand it children and two
one-directional biases against the treatment appear, **both in the primary metric**:

- **Fusion at the wrong level.** The baseline fuses two *parent-level* rankings, so a parent
  that is a moderate dense match **and** a moderate sparse match collects both RRF terms — that
  agreement bonus is the entire point of RRF. Fusing at *child* level and then taking `max`
  picks the single best child, which typically carries one modality's evidence, so the treatment
  behaves like `max(dense, sparse)` while the baseline behaves like `dense + sparse`. H7 would
  then change the ranking function (the hypothesis) *and* the fusion locus (an artifact) at once.
- **Pool denominated in the indexed unit.** 50 children is bounded above by 50 parents and in
  practice far fewer, since siblings of a strong child cluster near it and consume slots. The
  treatment's reach would be strictly shallower than the baseline's — precisely where §2 locates
  the hypothesis, given that ~26–30 points of Track B's addressable pool lie beyond rank 50.

**Specification.** For each modality independently (dense, sparse):

1. Rank children by that modality's score.
2. Walk the ranked child list in order, emitting each parent on **first appearance**, until
   `index.candidate_pool` **distinct parents** have been emitted or the child list is exhausted.
   First appearance in a rank-ordered list *is* `max`-over-children, so this **is** best-child
   scoring, per modality.
3. The result is a parent ranking `candidate_pool` deep — the same depth, in the same units, as
   the baseline arm's.

Then **RRF-fuse the two parent-level rankings** with the same `k_rrf`, and take top-k parents.

> **`candidate_pool` is denominated in delivered parents in both arms, never in indexed
> children.** The child-side pool becomes whatever depth is needed to reach that many distinct
> parents — variable per query, which is correct: the child side is now the harness parameter and
> the delivered side is pinned.

The baseline arm is **untouched**, so v1.3's published values still reproduce exactly and §2's
configuration-match check survives.

`parents-ranked-by-best-child`, **not** children-then-collapse: the latter makes the delivered
ordering a function of the child pool size, which is a harness parameter rather than a property
of the method.

Implementation: `src/smalltobig/retrieve.py`.

**Hits are scored on the delivered parent.** Parents are baseline units, so this is exactly
what the baseline scores — same inventory, same widths, same delivered volume, different
ranking function.

**Report the children-per-parent distribution per condition.** `max` over N gives a parent with
more children more chances at a high score. Parents are fixed-size baseline units so the
distribution should be near-uniform — but "should be" is what the distribution is for.

### The guard: parent-inventory set-identity

> **Assert set-identity between the s2b parent inventory and the baseline unit inventory, per
> condition, per track — exact identity, not overlap or containment — checked at build time and
> again at scoring time.**

Widening then becomes *unavailable* rather than merely discouraged: any parent that is not
literally a baseline unit fails the assertion. This is a stronger property than "widening
didn't change the number in the one test we wrote".

**Per template §A1b, this assertion is true by construction** (parents are built *from* baseline
units) and is therefore a **regression guard, not evidence**. A negative control asserts it
**fails** against a deliberately widened inventory, mirroring `test_invariance_test_actually_bites`.

**Depth assertion, added alongside set-identity:** both arms' per-modality parent rankings must
have equal length per query — either both reached `candidate_pool` distinct parents, or both
exhausted their source. This is the assertion that would have caught the pool-denomination bug,
and it too carries a negative control asserting it fires when the walk is truncated in children
rather than parents (`ParentRankingDepthMismatch`).

**What becomes of `ParentContext`.** Under v1.5 the primary parent **is** a baseline `Unit` and
carries `source_ranges` legitimately, because the pinned inventory means there is no wider parent
to reach for. The v1.4 type separation therefore **retires from the primary path** and survives
only for the C4 marked-section **secondary arm**, where parents are *not* baseline units and
dilution is still live. Stated explicitly so the next reader does not find a type system
forbidding the frozen design; `src/smalltobig/units.py` and
`tests/test_smalltobig_provenance.py` are scoped to that arm accordingly.

The v1.4 parent-dilution control measured recall@5 inflating by **+0.267 (C0) / +0.301 (C2)** on
Track A — larger than any genuine effect in this programme. That number is the documented
motivation for pinning the inventory rather than merely testing it.

**Retained descriptive:** the child-scored fixed-k numbers become "localisation precision at
fixed k", reported, not decision-bearing, with a stated reason to be low. Caption note: for C4
a sentence range is **provenance of origin, not byte-identity** — the formatter may have edited
the sentence, so the range identifies where the text came from rather than asserting the text
is verbatim.

**Duplicate parents** collapse as an inherent consequence of ranking parents directly.

## 5. Residual asymmetry — primary carries none

With children sentence-aligned everywhere and C4's primary parent width-matched to its baseline
unit, **the primary comparison carries no machinery asymmetry.** The only differences between
conditions are the corpora.

Residual, confined to the **secondary arm** (marked-section parents): those are semantically
coherent and variable-width against C0/C2's fixed windows. Reported separately with the
asymmetry restated at the point of comparison.

One note that belongs here rather than being discovered in the results — **stated as a
hypothesis, not a fact.** It is often assumed that C4's parents hold denser text because dedup
removed redundancy, which would make its children more heterogeneous and its `max`
correspondingly higher. **The unit counts weakly contradict this:** Track A C0 90 units vs C4
90; Track B C0 378 vs C4 **379**. If dedup had removed material redundancy the formatted
corpus would be shorter and cut into fewer 768-token units. It does not — reference
resolution and right-sizing plausibly add back what dedup removes. §7's mandatory verdict
wording must therefore **not** lean on density as established. To be settled by the realized
child token distributions and the unit counts, and reported either way.

## 6. Pre-registered hypotheses

**H7 (primary, Track B).** For each X ∈ {C0, C2, C4}: ranking X's units by **best-child score**
improves recall@5 (hybrid, `any`) over ranking them by **whole-unit score**, paired over queries.

**H7a (secondary, Track A).** No-harm check — best-child ranking does not significantly *reduce*
recall@5.

**H7b (robustness).** H7 at `child_tokens=256`, reported alongside 128, no post-hoc selection.

**H7c (descriptive).** Localisation precision at fixed k (child-scored); realized child token
distributions; children-per-parent distribution; blurb-to-child ratio. **No decision weight.**

## 7. Decision rules — four branches with explicit arithmetic

H7 is **three per-condition paired tests**, so the arithmetic across them is written down here,
before freezing. Form: **per-condition, not pooled** — C0/C2/C4 are different corpora, not
replicates, so a pooled delta is not a well-defined single effect and would let a harm in one
condition be averaged away by gains in another.

**Pre-named families:** `unformatted` = {C0, C2}; `formatted` = {C4}.

"Significant" = paired CI excludes 0 after Holm within {C0, C2, C4}, positive direction.

| Significant-positive set at `child_tokens=128` | Verdict |
|---|---|
| {C0, C2, C4} | **ADOPT** — provided H7a clean |
| {C0, C2} | **ADOPT_SCOPED** — unformatted family |
| {C4} | **ADOPT_SCOPED** — formatted family |
| {C0} · {C2} · {C0,C4} · {C2,C4} · {} | **KILL** — not a pre-named family |

Conditions passing inside a KILL pattern become **hypotheses for a future pre-registered test**,
never a verdict.

**Child-size scope:** if 128 yields KILL and 256 would independently yield ADOPT, the verdict is
**ADOPT_SCOPED — child size** ("helps at 256, not at 128"). No other child-size pattern creates
a scope.

### Multiplicity across the child-size axis — one Holm family of six

Two child sizes give two looks at a positive verdict. Left uncorrected, the family-wise error
rate across the size axis is uncontrolled: either look alone would suffice for a scoped adopt.

**Decision: Holm over all six tests — three conditions × two child sizes — as a single family.**

Chosen over the alternative (two families plus an honest "rests on an uncorrected second look"
label) because it removes the multiplicity rather than annotating it. The cost is a higher bar,
which is the correct direction for a claim that would otherwise rest on two looks, and it means
a child-size scope — if it triggers — is a **finding** rather than a caveated one needing a
paragraph of explanation to be read correctly. Holm is valid under arbitrary dependence, so the
two sizes sharing corpora and queries is not an obstacle.

Consequence to accept in advance: with six comparisons the correction is stricter, so a genuine
but small effect is more likely to be missed. That is the trade being made deliberately.

**REJECT_HARM overrides every row**, including a full ADOPT sweep: any significant *negative*
on any primary condition on *either* track. A harm finding is reported as harm, never absorbed
into a null nor offset by gains elsewhere.

**Mandatory verdict wording** if the outcome is `ADOPT_SCOPED — formatted family {C4}`: the §5
secondary-arm asymmetry must be restated in the verdict text itself, so "small-to-big helps only
on formatted corpora" cannot silently absorb "C4's parents are denser by treatment".

## 8. Statistics

Primary recall@5, hybrid, `any`. Secondary recall@{1,3,10}, nDCG, MRR, strict variant.
Paired bootstrap (10k) + paired permutation (10k), Holm within {C0, C2, C4} on Track B;
Track A no-harm checks form a **separate** family. Neither merges with v1.1's H1–H4 or v1.3's
H6. Child-size variants reported separately, never pooled.

## 9. Environment pins

`embedding.model` = **`BAAI/bge-base-en-v1.5`**, revision `main`, pinned explicitly, not
inherited. LLM `claude-opus-4-8` (A) / `claude-sonnet-5` (B), cache-served. `run_id` populated.
`--out results_v15` — never `results/`.

**Comparability:** v1.5 absolutes are comparable to v1.3's, **never** to v1.1's (MiniLM stack).
Only within-run paired deltas travel across amendments.

**Truncation note:** v1.3's confound does not apply — no cross-encoder here, and 128/256-token
children sit comfortably inside bge-base's 512-token input window, so no indexed text is
truncated before embedding.

## 10. Cost — size-cut decision taken BEFORE any measurement

**Both child sizes (128 and 256) will be run. Neither is dropped.** The two-size design exists
for a methodological reason (Track B has no dev split, so both are pre-declared to prevent
post-hoc selection); dropping one pre-emptively reintroduces the freedom the design removes.

**If compute forces a cut**, it is a documented amendment recorded **before any
`child_tokens=128` result exists**, stating compute cost as the reason. Running both and
reporting the better one — or skipping 256 "for time" after seeing 128 — is indistinguishable
from post-hoc selection after the fact.

## 11. What this does not test

Generation quality with parent context (no generation metric). Child sizes other than 128/256.
Track C (blocked on v1.2's open items). Interaction with reranking (that axis is spent on this
split).
