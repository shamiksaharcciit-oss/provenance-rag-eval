# v1.10 CONTEXT-BUDGET — pre-registration draft for agent 1
# (contextual retrieval under the apparatus: does the gain survive matched budget, and how
# much of it is size?)

**Status:** DRAFT FOR FREEZE. Becomes a pre-registration only at its Gate 0 freeze commit.
**Date:** 1 August 2026
**Experiment ID:** `v110` — own directory, own manifest, own results document.
**Executing agent:** agent 1. v1.9 stays parked at `5bc4aeb`, untouched; nothing here
affects its spend gate.
**Authorised by:** Shamik, 1 August 2026 ("Draft it to be run by agent 1").

**The hard constraint, stated first: this experiment spends nothing.** Zero fresh LLM
calls, of any kind, at any stage — the contextual blurbs come from the early-round C2
cache or the affected track is dropped. The experiment-wide assert is `llm.calls == 0`,
per stage, executed not narrated. "We'll just generate a few missing blurbs" is how a free
experiment becomes a spending one; if the cache is incomplete on the primary cell, that is
a STOP, not a top-up.

---

## 0. What this asks, and what it cannot say

Contextual retrieval's published evaluation reports its gain at fixed k while its
transformation lengthens every chunk; no published measurement separates the treatment
from the size effect. This experiment stages the fair fight: at matched token budget, with
added text charged to the budget but unable to score, does the gain survive — and how much
of it is added *length* versus added *information*?

Scope, frozen: results are statements about **C2 — this repo's implementation of
contextual retrieval, with its cached blurbs, on these corpora** — not about Anthropic's
published numbers, product, or corpora. The results document carries this scoping sentence
in its header, not its footnotes.

### Pre-freeze amendment

One Gate 0 finding, ruled in `Decisions_v110_Gate0_2026-08-01.md` and applied before the
freeze commit.

| id | finding | change |
|---|---|---|
| **PF-G1** | §1's "generic English sentences" and "no corpus vocabulary" are jointly unsatisfiable against the enumerated corpus (10,352 content words) | requirement moved to **zero query-vocabulary overlap**, verified; corpus overlap **quantified** (100/334) rather than eliminated; **census-to-fixed-point** added to Gate 0 |

Settled before any v1.10 arm value existed. No amendment to this document is permitted after
the freeze commit.

Contamination disclosure: nothing is blind. v1.6's size findings, CR's published claims,
and this programme's motive to demonstrate its instrument are all known. Every prediction
is HYPOTHESIS under A1g.

Standing constraints, all in force: closed artifacts untouched (`12483f9`, `235ccfb`,
`cdd197f`, `5176903`, the Gate 1 rulings, all PW-1 artifacts, white paper, brief); no
v1.10 number revisits any closed conclusion, v1.6's KILL and PW-1 included; nothing under
`v17/`, `v18/`, or `v19/` modified; commits under `v110/` pathspec plus this document
only; preserve exact domain terms, identifiers and numbers verbatim; the personal
documents in the working folder remain out of scope.

---

## 1. Arms — three, differing only in what is prepended

Let the **base** be C2's published base segmentation (the Gate 0 census establishes which
inventory that is and binds it by content hash; expected: the C0 inventory).

| arm | construction |
|---|---|
| `U` | base chunks, nothing prepended |
| `P` | base chunks + **neutral padding**, per-chunk token length exactly matching that chunk's real blurb |
| `C` | base chunks + the real cached C2 blurbs (contextual retrieval as published) |

**Padding specification (frozen here):** filler is drawn from a fixed, committed pool of
generic English sentences (frozen file, hashed), assigned per chunk by seed 1337, and
truncated to the blurb's exact token length.

**The pool's neutrality requirement [PF-G1].** The draft required the pool to contain *no
corpus vocabulary*. The Gate 0 census established that this is unsatisfiable in conjunction
with "generic English sentences": the corpus carries 10,352 content words — most of ordinary
English — so any pool of real sentences overlaps it, and the only pools that do not are made
of nonce words the same sentence forbids. Two clauses, each reasonable against an imagined
corpus, jointly impossible against the enumerated one. Replaced by the property that does
the work:

1. **Required and verified — zero query-vocabulary overlap.** The pool shares no content
   word with either track's *full query set*, by executed check. BM25 scores on query terms,
   so a filler word absent from every query can earn no lexical match.
2. **Quantified, not eliminated — corpus overlap.** Reported in the results document
   (census baseline: **100 of 334** pool content words), never asserted away.
3. **Census to fixed point.** After *any* pool edit the full overlap check re-runs, and
   editing continues until a **complete pass is clean**. This is procedure, not instinct:
   the first Gate 0 fix introduced a second overlap (`another`) which only the re-run
   caught. Every edit asserts its pattern matched before replacing (A1h).

Declared limitation, unchanged: no filler is perfectly inert for a dense encoder. `P`'s
reading rests on **lexical** neutrality, which is checked, and not on embedding neutrality,
which cannot be. `D_pad` therefore reads as *"added length of lexically-query-foreign
text"*, never as *"added length of nothing"*.

Embedder: `all-MiniLM-L6-v2` only (bge excluded, declared). Retrieval: the standard stack
— dense + BM25, RRF `k_rrf = 60`, `candidate_pool = 50`, seed 1337. Fresh encodes for all
three arms; batch restores by content hash where inputs are byte-identical, recorded under
PROC-1. **Memory order applies:** no encode starts without free memory ≥ 2× the 393 MB
known failure point, or the sharded path regardless.

## 2. Scoring — added text pays and cannot score

Primary metric: `recall@budget`, B = 1920 tokens, S2 basis, exactly as v1.6, with one
rule doing the new work:

> **Prepended text (blurb or padding) is charged to the budget — its tokens count toward
> B, because they occupy context in deployment — and carries no `source_ranges`, so it can
> never contribute coverage.** CR must pay for its added tokens and win on findability
> alone.

The crossing-unit rule is unchanged (the unit that crosses B is included, its full length
counted, blurb included). Descriptive companion: `recall@5` for all three arms — the
published frame, reported so the attenuation is visible in one table.

## 3. Decomposition, cells, family

```
D_pad  = P − U     added length alone, at matched budget
D_info = C − P     added information beyond length
D_total = C − U    contextual retrieval vs base (lattice check: D_pad + D_info exactly)
```

Same three contrasts computed descriptively at `recall@5`.

- **Primary, decision-bearing cell: Track A** (n = 176), contingent on the census
  confirming full C2 blurb coverage there; incomplete Track A coverage is a STOP.
- Track B: descriptive, and only if its cached coverage is complete; otherwise dropped
  with the count of missing blurbs stated (no-silent-caps).
- **Tested family `F_CTX`, Holm within, exactly two members, Track A, recall@budget:**
  `D_info` and `D_total`. Everything else — `D_pad`, all recall@5 numbers, all Track B —
  descriptive: integer numerators, `n01`/`n10` beside every net, no test, no mechanism.
- Statistics as standard: `paired_bootstrap_diff` + `paired_permutation_p`,
  `iters = 10000`, `seed = 1337`, `ci = 0.95`; every rate on the k/n lattice.

## 4. Sealed predictions (all HYPOTHESIS; cells named)

- **PC-1 (apparatus, scored first):** the published recall@5 values for the base arm and
  C2 reproduce exactly from the fresh v110 build. Mismatch = APPARATUS-STOP; nothing
  downstream is interpreted.
- **PC-2 (control, Track A, recall@budget, descriptive):** `D_pad ≤ 0`. Padding consumes
  budget and cannot score, so it must not help; `D_pad > 0` by more than the lattice's
  grain quarantines the run for diagnosis before any other number is read.
- **PC-3 (Track A, `F_CTX`):** `D_total > 0` — contextual retrieval retains a real gain
  at matched budget.
- **PC-4 (Track A, `F_CTX`):** `D_info > 0` — the informative component, not length, is
  where any gain lives.
- **PC-5 (Track A, descriptive):** the matched-budget gain `D_total(budget)` is smaller
  than the fixed-k gain `D_total(@5)` — the published frame overstates CR, in the
  direction v1.6 found for size. Scored by direction comparison of the two absolute
  numbers, never by ratio (AllCells §4).
- **PC-6 (Track B, direction only, contingent on coverage):** `D_total(budget)`'s sign
  matches Track A's.

Pre-committed interpretations, both directions: PC-3/PC-4 confirmed → the first
controlled, budget-fair, provenance-scored validation of contextual retrieval's mechanism
as implemented here — reported with exactly that scope. PC-3 null or negative → the
published-frame gain is attributable to size and budget accounting as far as this
implementation reaches — a finding about the *metric frame*, stated with the same scope.
Neither outcome says anything about the formatter, revisits any closed verdict, or
licenses an external claim before Shamik's decisions.

## 5. Costs and coordination

- **API cost: zero, by the §0 constraint.** Local compute: three arms × up to two tracks
  of MiniLM encodes, under the memory order.
- Agent 1 only. v1.9's spend gate is untouched — v1.10 makes no call the gate governs. If
  v1.8's results commit lands mid-run and wakes v1.9, **v1.9 takes priority** (it spends
  under a clean window and its answer is on the critical path); v1.10 pauses at the
  nearest arm boundary and resumes after — the manifest records the pause.
- No cost-guard interaction: nothing here prices anything.

## 6. Gates

**Gate 0 — build, census, STOP.** The census, against real inputs and real acceptors (the
four-instance rule, applied in full): C2 blurb cache coverage per track, per chunk; blurb
token-length distribution (the padding matcher's real domain); the padding pool's overlap
check against corpus and query vocabularies, **run to fixed point** — re-run in full after
any pool edit until a complete pass is clean [PF-G1]; the base-inventory identification
bound by hash; unattributed-range handling exercised against the real scorer on real C2 units (not
a synthetic case); arms built with `llm.calls == 0` asserted; unit tests including the
lattice identity, the crossing-unit-with-blurb accounting, and a padding-truncation
roundtrip. Then STOP for a ruling — findings expected; this plan's author has been wrong
against an uncensused domain four times in this programme's recent history.

**Gate 1 — run complete.** `Results_v110_ContextBudget.md`: PC-1 first, PC-2 second, then
the family; the three-contrast table at both metrics with discordant counts; the
recall@5-vs-budget absolute-numbers table; coverage censuses and any dropped track with
counts; memory margins per arm; item-7 self-check with output in the record. Then STOP
for the ruling. No paper text, no external claim, no recommendation.

## 7. Not authorised

Any fresh LLM call. Any bge run. Any edit outside `v110/` and this document. Any
recomputation or reinterpretation of closed quantities. Any additional arm, metric, or
test (in particular: no C5 — formatted-plus-blurbs — however tempting the interaction is;
it composes two treatments and belongs, if anywhere, in a future pre-registration after
Shamik's decisions). Any use of v1.10 to argue about the formatter, v1.6, v1.7, v1.8,
v1.9, or PW-1. Any external release or draft of one.
