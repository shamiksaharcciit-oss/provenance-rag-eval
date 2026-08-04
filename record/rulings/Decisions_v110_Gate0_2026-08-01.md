# v1.10 Gate 0 — ruling on G1, acknowledgment of G2, and the freeze instruction

**Responds to:** census complete at `73ba19d`; both tracks fully cached; zero fresh calls
enforced by a raising provider; one finding.
**Date:** 1 August 2026
**Status:** G1 ruled — the amendment is adopted as proposed, with one addition. Freeze
after it.

---

## 1. G1 — adopted: the requirement moves to the property that does the work

The conjunction I wrote — "generic English sentences" with "no corpus vocabulary" — is
unsatisfiable against the real corpus, and the census proved it rather than arguing it: a
10,352-word technical corpus contains most of ordinary English, so any pool of real
sentences shares words with it, and the only pools that don't are made of nonce words the
same sentence forbids. This is the census family again, in conjunction form: two clauses,
each reasonable against an imagined corpus, jointly impossible against the enumerated one.
Written by me, caught pre-freeze by the rule built for exactly this — which is the system
working at the cheap end for once.

Ruling, as proposed with one addition:

1. **Required and verified: zero query-vocabulary overlap** — the padding pool shares no
   content word with either track's full query set, by executed check. This is the
   property that does the work: BM25 scores on query terms, and a filler word absent from
   every query can earn no match.
2. **Quantified, not eliminated: corpus overlap** — reported in the results document
   (census baseline: 100/334 pool content words), never asserted away.
3. **Addition — census to fixed point:** after *any* pool edit, the full overlap check
   re-runs, and editing continues until a complete pass is clean. Your first fix
   introduced a second overlap and your re-run caught it; that loop is now the required
   procedure rather than good instinct. A1h's assert-before-replace practice is noted and
   kept.
4. **`D_pad`'s reading is restated** exactly as you put it: "added length of
   lexically-query-foreign text," never "added length of nothing." The embedding-
   neutrality limitation stands unchanged — checked lexical neutrality, uncheckable
   embedding neutrality, declared.

## 2. G2 — acknowledged, and the distinction it drew is worth keeping

A hash that includes `unit_id` measures naming; a hash over doc ids and ranges measures
provenance. Your checker conflated them, nearly reported a false finding, and you caught
it before it left the room — A1f honoured, and `provenance_hash` is the right acceptor
for the claim being made. The near-miss is also the useful lesson: an executed check can
still check the wrong property, so the check's *object* needs the same census discipline
as the spec's domain.

## 3. Endorsements, briefly

The raising provider (`no_fresh_calls()` installing a provider that throws) is
enforcement where the plan asked for an assert — stronger, kept. Binding the base
inventory by rebuilding v1.6's `U768` through the imported builder and comparing
provenance hashes is identity over assertion in its best form. And verifying §2's
charged-but-cannot-score rule against the real scorer on all 72,540 real unit-query pairs
— zero disagreements — is the enumerate-from-the-artifact rule applied before it was
asked for.

## 4. Freeze instruction

1. Amend the plan: §1's padding specification per §1 above, with a pre-freeze amendments
   note naming G1 and this document; the fixed-point census requirement into Gate 0's
   census list.
2. Full suite green.
3. **One freeze commit** — plan + padding pool (hashed) + census outputs + tests. Then
   the run: encodes under the memory order (1,328 MB against the required 786 is
   comfortable; record margins per arm regardless), arms, retrieval, scoring,
   `Results_v110_ContextBudget.md` with PC-1 scored first and PC-2 before anything else
   is read, item-7 self-check with output in the record, STOP at Gate 1.
4. Priority rule unchanged: if v1.8's results commit lands and wakes v1.9, v1.9 takes
   the machine; v1.10 pauses at the nearest arm boundary and the manifest records it.

Nothing here spends anything, touches any other experiment, or moves any closed artifact.
