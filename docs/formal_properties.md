# Formal properties of the provenance layer

This note states precisely what the apparatus guarantees and why the guarantees
survive arbitrary pipeline transformations. It covers the published scope of the
companion paper; nothing here is new machinery, only the existing machinery stated
formally.

## 1. The coordinate space

Let a corpus be a set of documents D = {d₁, …, dₙ}, each dᵢ an immutable string.
The address space is the set of pairs (i, k) with 0 ≤ k < |dᵢ|: one address per
character of the original, untransformed corpus. A **range** r = (i, s, e) with
s < e denotes the half-open character interval [s, e) of document dᵢ. Ranges never
address transformed text; transformed text carries ranges *into* the originals.

## 2. Provenance and the three update rules

A **unit** u (chunk, segment, package member) carries a finite set of ranges
P(u), its provenance. Pipelines construct units only through three operations:

- **Cut.** A unit u is divided at an internal boundary into u₁, u₂ with
  P(u₁) ∪ P(u₂) = P(u) and P(u₁) ∩ P(u₂) = ∅, each part taking the sub-ranges
  corresponding to its text.
- **Combine.** Units u₁, u₂ merge into u with P(u) = P(u₁) ∪ P(u₂).
- **Create.** Text produced by the pipeline itself (repaired references, generated
  context, filler) forms content with P = ∅ (**orphan text**).

Rewriting a unit's surface text is Create composed with derivation bookkeeping:
the rewritten unit retains the P of the unit it derives from; the claim provenance
makes is *derives-from*, not *is-a-copy-of*.

**Exactness lemma (composition).** If every individual operation applies its rule
correctly, then after any finite sequence of operations, every unit's P is exactly
the set of original-corpus ranges its content derives from. *Sketch:* each rule
preserves the invariant "P(u) = union of the ranges u's non-orphan content derives
from"; the invariant holds trivially at initial segmentation (identity ranges);
induction over the operation sequence. No step ever inspects transformed text, so
no step's correctness depends on how heavily the text has been transformed. This
is the property post-hoc alignment cannot have: alignment error grows with edit
depth; recorded provenance has no error term at any depth.

## 3. Ground truth and scoring

An answer is registered once as a range set Ω in the originals. For retrieval
scoring at token budget B: walk the ranking, summing each unit's full token length
(orphan text included); include the unit that crosses B; stop. The query scores
positively iff the union of retained units' provenance intersects Ω (S2; stricter
ladder levels tighten the intersection requirement). Two consequences:

- **No size subsidy.** Larger units consume more budget; no per-pipeline k exists.
- **Orphan text cannot score.** P = ∅ implies empty intersection with every Ω:
  generated text is charged (it consumes budget) but can never earn credit. A
  pipeline profits from added text only if the addition improves *ranking* enough
  to pay for its own cost.

## 4. Verified-content constructions

For question q with answer Ω, from a pipeline's unit set:

- **Answer-bearing package**: a unit multiset whose provenance union ⊇-intersects
  Ω, padded with adjacent units to exactly B. Two pipelines' packages for q are
  budget-matched, so only text form differs while answer content is present in
  both — *information-identical by construction*.
- **Answerless package** (same-document): all units of the answer's document whose
  provenance intersects Ω are excluded; remaining on-topic units padded to B.
  Guarantee: provenance union ∩ Ω = ∅ — *provably answer-free*, a property of the
  construction, not an observation about the text.

Both guarantees are decidable by interval arithmetic and are re-verified by an
executed census before use (the census results ship in this repository; 346/346
answerless packages verified at zero overlap across the programme).

## 5. What is deliberately not claimed

The interval arithmetic itself is standard (source maps, stand-off annotation,
diff/patch). Token counts are an intentional in-repo approximation (see
`src/textutil.py`), applied identically to every condition — budgets are
comparable across arms by construction, and the meter is pinned by the repository
rather than by any external tokenizer version. Judge-based measurements reported
in the record are scoped to the specific judge measured. Claims about reading-side
effects are generator- and prompt-contingent, as measured; the apparatus makes
them exactly measurable, not universal.
