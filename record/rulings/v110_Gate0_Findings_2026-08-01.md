# v1.10 Gate 0 — census complete, one finding before the freeze

**Status:** THE FREEZE HAS NOT HAPPENED. `Plan_v110_ContextBudget_2026-08-01.md` is untracked.
One finding changes text the freeze would make permanent; everything else is clean.
**Date:** 1 August 2026
**Spend: ZERO fresh LLM calls**, asserted per stage and printed in the census —
`total_fresh_llm_calls: 0`. Not narrated: `no_fresh_calls()` installs a provider that raises, so
a cache miss fails the build rather than quietly spending.

---

## The census — real inputs, real acceptors

| | Track A | Track B |
|---|---|---|
| documents / test queries | 45 / 176 | 60 / 150 |
| **fresh LLM calls** | **0** | **0** |
| C2 blurb cache | **90/90, 0 misses** | **378/378, 0 misses** |
| blurb tokens min/median/max | 29 / 48 / 77 | 28 / 53 / 86 |
| base inventory | 90 units | 378 units |
| arms share one segmentation | **True** | **True** |
| base inventory **== v1.6's `U768` arm** | **True** | **True** |
| unit tokens median `U`/`P`/`C` | 768 / 807 / 807 | 768 / 818 / 818 |
| `P` vs `C` length mismatches | **0** | **0** |
| scorer agreement `U`=`P`=`C` | **15,840 agree / 0 disagree** | **56,700 agree / 0 disagree** |

**Both tracks are fully cached, so neither is dropped** and §0's constraint holds without
sacrificing the descriptive track.

**The base inventory is bound by identity, not by claim.** Rather than asserting "expected: the
C0 inventory", the census rebuilds v1.6's `U768` arm through the imported v1.6 builder and
compares provenance hashes. They match on both tracks. C2's declared base *is* the segmentation
this programme has been publishing since v1.3.

**§2's rule is a property the implementation already has, and it is verified rather than
assumed.** `ContextualChunker` prepends the blurb to `Unit.text` and leaves `source_ranges`
untouched, so prepended tokens are counted by `count_tokens` — charged to the budget — while
contributing nothing to coverage. Exercised against the **real scorer on real C2 units**: across
72,540 unit-query pairs on the two tracks, `U`, `P` and `C` score **identically, with zero
disagreements**. The `P` arm is built to the same contract and matches `C`'s length on every
single chunk.

**Memory order:** 1,328 MB free against the required ≥ 786 MB (2 × 393). Met; the sharded path is
available regardless and PROC-1 recording is wired.

**Tests:** 21 v110 tests — padding-truncation roundtrip, crossing-unit-with-blurb accounting, the
lattice identity, the charged-but-cannot-score contract, and the zero-spend guard. Full suite
**271 passed, 0 failed**.

---

## G1 — "the pool contains no corpus vocabulary" is unachievable as written; the property that matters is achievable and achieved

§1 requires the padding pool to contain **no corpus vocabulary**, verified by an executed
overlap check. The check is executed, and the requirement fails:

| | count |
|---|---|
| pool content words | 334 |
| **overlap with corpus vocabulary** | **100** |
| corpus content-word vocabulary | 10,352 |
| **overlap with query vocabulary** | **0** |

The overlapping words are `across`, `air`, `along`, `behind`, `door`, `edge`, `front`, `full`,
`grew`, `half`, `handle`, `kept` and 88 more of that kind. **A 10,352-word technical corpus
contains most of ordinary English**, so no pool of real English sentences can avoid it. The
requirement as written could only be met by nonce words, which §1 also rules out by specifying
"generic English sentences" — the two clauses cannot both hold.

**The retrieval-relevant property is different, and it is met exactly.** BM25 scores a unit on
*query* terms. A filler word that appears in the corpus but in no query cannot earn a lexical
match for any query in this experiment. **Query-vocabulary overlap is zero.**

I reached zero by editing the pool during Gate 0 — eight substitutions removing `gathered`,
`new`, `passing`, `set`, `time`, `two`, and then `another`, which I introduced with the first
fix. Each substitution asserted that its pattern matched before replacing, per A1h. The pool is
pre-freeze and unfrozen, so this is design, not tampering; after the freeze its hash
(`edee52256dd9ce25`) binds it.

**Proposed amendment, for your ruling:** replace §1's "contains no corpus vocabulary" with

> the pool contains **no content word appearing in any query** on either track — the property
> BM25 can score on, verified by an executed check — and its corpus-vocabulary overlap is
> **quantified and reported** (100 of 334 pool content words), not eliminated, because ordinary
> English cannot be disjoint from a 10,352-word English corpus.

The declared limitation is unchanged and still binds: **lexical neutrality is checked; embedding
neutrality cannot be**, so `D_pad` reads as "added length of lexically-foreign text", never as
"added length of nothing".

## G2 — one defect of mine, reported per A1f

My first census printed **"inventory hashes equal across arms: False"** and I nearly reported it
as a finding. It was my checker: `inventory_hash` includes `unit_id`, and the `P` arm suffixes
its ids with `-pad`, so the hashes differed for a naming reason and not a provenance reason. The
invariant the experiment actually rests on is that all three arms carry the same segmentation.
Added `provenance_hash`, which hashes doc ids and source ranges only; it returns **True** on both
tracks, and the `assert_prepended_text_is_unattributed` acceptor had already been passing
throughout. The plan was right and my check was wrong.

---

## What I have not done

- **No freeze commit.** G1 changes §1.
- **No fresh LLM call** — zero, asserted per stage, printed in the census.
- **No encode, no retrieval, no arm value.** Gate 0 builds inventories and censuses them; it
  computes no `recall@budget` and no contrast.
- **No bge**, no C5, no additional arm or metric.
- Nothing outside `v110/` and this document. `v17/`, `v18/`, `v19/` and every closed artifact
  untouched; v1.9 stays parked at `5bc4aeb` and its spend gate is not engaged by anything here.

## What happens on a ruling

G1 is a wording amendment to §1. G2 needs only your agreement that it is recorded correctly.
Then I amend the plan, re-run the census and suite, and make the Gate 0 freeze commit — plan
plus `v110/` code, the hashed filler pool, tests and census — after which no wording change is
possible without a new pre-registration.
