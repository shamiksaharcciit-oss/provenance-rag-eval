# v1.10 CONTEXT-BUDGET — results

**Scope, stated here and not in a footnote.** Every result below is a statement about **C2 —
this repository's implementation of contextual retrieval, with its cached blurbs, on these two
corpora**. It is not a statement about Anthropic's published numbers, product, or corpora, and
nothing here should be read as one.

**Pre-registration:** `Plan_v110_ContextBudget_2026-08-01.md`, frozen at
**`e52a9a88299de7efd00435e0c63be349e64e041f`** @ 2026-08-01T20:24:16Z, with pre-freeze amendment
PF-G1 recorded in its §0.
**Rulings applied:** `Decisions_v110_Gate0_2026-08-01.md`, `Decisions_v110_PrimaryCell_2026-08-01.md`.
**Cells:** Track A (primary, decision-bearing, n=176); Track B (descriptive, n=150). MiniLM only.
**Contamination:** nothing here is blind. v1.6's size findings, contextual retrieval's published
claims, and this programme's motive to demonstrate its instrument were all known before the
predictions were written. **Every prediction is HYPOTHESIS under A1g.**
**Spend: zero fresh LLM calls**, asserted per stage — `fresh_llm_calls: 0` in both manifests.

---

## 1. PC-1 — the apparatus, scored first

> **PC-1 (apparatus, scored first):** the published recall@5 values for the base arm and C2
> reproduce exactly from the fresh v110 build. Mismatch = APPARATUS-STOP.

An executed `assert` in the runner on integer numerators; a mismatch would have halted the cell
before any contrast was computed.

| cell | arm | condition | v1.10 | published | reproduces |
|---|---|---|---|---|---|
| A | `U` | C0 | 138/176 | 0.7841 → 138/176 | ✓ |
| A | `C` | C2 | 150/176 | 0.8523 → 150/176 | ✓ |
| B | `U` | C0 | 58/150 | 0.3867 → 58/150 | ✓ |
| B | `C` | C2 | 58/150 | 0.3867 → 58/150 | ✓ |

**PC-1 HOLDS — 4 of 4 acceptors reproduce exactly.**

**One fact from the published record that governs how Track B must be read:** on Track B the
published C0 and C2 are **identical** (0.3867 both). Contextual retrieval had **no published gain
on Track B to begin with**. Anything Track B shows below is therefore not a gain attenuating; it
is the absence of a gain that was never there.

## 2. PC-2 — the control, scored second, on its frozen criterion

> **PC-2 (control, Track A, recall@budget, descriptive):** `D_pad ≤ 0`. Padding consumes budget
> and cannot score, so it must not help.

`D_pad` is outside `F_CTX` and is reported as the plan froze it: integer numerator and discordant
counts, **no CI and no p** (primary-cell ruling §3).

| cell | `D_pad` (recall@budget) | n01 / n10 |
|---|---|---|
| **A** | **−9/176** | 4 / 13 |
| B | −4/150 | 3 / 7 |

**PC-2 HOLDS on its named cell.** `D_pad` is negative: padding consumed budget and bought
nothing. Nothing in E1 is quarantined by this control.

The direction is not merely permitted but *measured* — matched-length, lexically-query-foreign
text made retrieval **worse** by displacing units the budget would otherwise have held. That is
the declared limitation arriving as data: `D_pad` reads as *"added length of
lexically-query-foreign text"*, never as *"added length of nothing"*.

## 3. The family — `F_CTX`, Track A, recall@budget

Two members, Holm-corrected within the declared family only.

| member | Track A | p_raw → **p_holm** | verdict |
|---|---|---|---|
| `D_info` | **+20/176** | 0.0001 → **0.0002** | **survives** |
| `D_total` | **+11/176** | 0.0250 → **0.0250** | **survives** |

**Both members are positive and survive Holm at p < 0.05.**

- **PC-3 (`D_total > 0`) — CONFIRMED.** Contextual retrieval retains a real gain at matched
  budget.
- **PC-4 (`D_info > 0`) — CONFIRMED.** The informative component, not length, is where the gain
  lives.

**The licensed sentence, exactly:** *at matched token budget, with added text charged and unable
to score, this implementation of contextual retrieval retained a significant gain on Track A,
attributable to the informativeness of the added context rather than its length.* The scope
clause in this document's header travels with that sentence every time it is uttered.

`F_CTX` on Track B (not decision-bearing, reported for completeness): `D_info` p_holm 1.0,
`D_total` p_holm 0.90811 — neither survives.

## 4. The three contrasts, both metrics, both tracks

Integer numerators; `n01`/`n10` beside every net, descriptively, never tested on (R3/A5b). The
lattice identity `D_pad + D_info == D_total` is an **executed assertion** in the runner, run once
per metric per cell — 4 executions, all passed.

### recall@budget (B = 1920, S2 basis)

| contrast | Track A | Track B |
|---|---|---|
| `D_pad` | −9/176 · n01 4 n10 13 | −4/150 · n01 3 n10 7 |
| `D_info` | **+20/176 · n01 20 n10 0** | 0/150 · n01 6 n10 6 |
| `D_total` | **+11/176 · n01 16 n10 5** | −4/150 · n01 6 n10 10 |
| lattice | −9 + 20 = 11 ✓ | −4 + 0 = −4 ✓ |

### recall@5 (the published frame)

| contrast | Track A | Track B |
|---|---|---|
| `D_pad` | −8/176 · n01 5 n10 13 | −3/150 · n01 3 n10 6 |
| `D_info` | +20/176 · n01 21 n10 1 | +3/150 · n01 9 n10 6 |
| `D_total` | +12/176 · n01 16 n10 4 | 0/150 · n01 8 n10 8 |
| lattice | −8 + 20 = 12 ✓ | −3 + 3 = 0 ✓ |

**`D_info`'s discordant split on Track A is 20:0 at budget** — twenty queries where the real
blurb won and **not one** where matched-length padding did. The net alone does not show that; it
is the reading R3 exists to make available.

## 5. PC-5 — the published frame against the matched budget, in absolute numbers

> **PC-5 (Track A, descriptive):** the matched-budget gain `D_total(budget)` is smaller than the
> fixed-k gain `D_total(@5)`. Scored by direction comparison of the two absolute numbers, never
> by ratio.

| | `D_total(@5)` | `D_total(budget)` | difference |
|---|---|---|---|
| Track A | +12/176 | +11/176 | **1 query** |

**PC-5 HOLDS, and its entitlement is exactly this: the published frame overstated the gain here
by its own grain — one query on the lattice.** No ratio is computed and no stronger reading is
available from this number.

## 6. PC-6 — Track B, direction only, descriptive

> **PC-6 (Track B, direction only, contingent on coverage):** `D_total(budget)`'s sign matches
> Track A's.

Track A **+11/176**, Track B **−4/150**. The signs differ. **PC-6 FAILS.**

Reported descriptively and with §1's fact attached: on Track B, published C0 and C2 are identical,
so there was no gain on that track at fixed k either. Track B is not a case of a gain failing to
survive matched budget; it is a corpus where this implementation of contextual retrieval showed no
gain in the published frame and shows none here. Track B is descriptive and contingent and does
not move the scored cell.

## 7. Arm levels, coverage census, and margins

| cell | arm | units | token mean | recall@budget | recall@5 | realised k | tokens charged (mean) |
|---|---|---|---|---|---|---|---|
| A | `U` | 90 | 609.8 | 132/176 | 138/176 | 3.22 | 2258 |
| A | `P` | 90 | 659.9 | 123/176 | 130/176 | 3.07 | 2299 |
| A | `C` | 90 | 659.9 | 143/176 | 150/176 | 3.26 | 2228 |
| B | `U` | 378 | 708.4 | 50/150 | 58/150 | 3.08 | 2284 |
| B | `P` | 378 | 761.7 | 46/150 | 55/150 | 3.03 | 2409 |
| B | `C` | 378 | 761.7 | 46/150 | 58/150 | 3.05 | 2427 |

`P` and `C` share a token mean to one decimal on both tracks, by construction and by assertion:
per-chunk length match, zero mismatches at Gate 0.

**Coverage census — no track dropped.** C2 blurb cache complete on both: Track A **90/90**, Track
B **378/378**, zero misses. Blurb tokens 29/48/77 (A) and 28/53/86 (B), min/median/max. Arms share
one segmentation by provenance hash, and the base inventory was bound **by identity** to v1.6's
`U768` arm, rebuilt through the imported v1.6 builder.

**Padding pool** `edee52256dd9ce25`, 66 sentences, 334 content words. **Query-vocabulary overlap
0**, verified to fixed point. **Corpus-vocabulary overlap 100 of 334**, quantified and not
eliminated: a 10,352-content-word corpus contains most of ordinary English, so the plan's original
"no corpus vocabulary" was unsatisfiable in conjunction with "generic English sentences" (PF-G1).

**Memory margins per arm** (free MB after each arm; known failure point 393 MB):

| cell | `U` | `P` | `C` |
|---|---|---|---|
| A | 432 | **363** | 553 |
| B | **311** | 714 | 729 |

Both runs used the sharded encode path throughout, which is bit-identical and pinned by
`tests/test_pw1_safe_encode.py`. **Two margins fell below the 393 MB failure point** — Track A `P`
at 363 and Track B `U` at 311 — while sharded encoding was active, which is what it exists for.
Recorded prominently rather than buried: the memory order's ≥786 MB precondition was met at launch
(1,328 MB), and the margin still went under mid-run twice.

## 8. Limitations

- **An out-of-procedure computation, disclosed.** §3 of the frozen plan places `D_pad` outside
  `F_CTX`: integer numerators and discordant counts, no test. The runner I wrote after the freeze
  computed a CI and a permutation p for it anyway. Those values are **`D_pad`(A, budget) CI
  [−0.097, −0.006] against p 0.051**. They are stated here because deleting a number already
  computed is a worse record than owning one that should not exist. **No conclusion in this
  document cites them**; PC-2 is scored on its descriptive criterion alone. Their boundary
  disagreement — an interval excluding zero beside a p just above 0.05 — is the bootstrap and the
  permutation answering slightly different questions at the edge, on a quantity neither was owed.
- **Lexical neutrality is checked; embedding neutrality cannot be.** The padding pool shares no
  content word with any query, so it can earn no BM25 match. No filler is inert for a dense
  encoder, and `D_pad` is a statement about lexically-query-foreign text, not about nothing.
- **Contamination.** Nothing was blind; every prediction is HYPOTHESIS under A1g.
- **One embedder.** MiniLM only; bge excluded by declaration. No claim here is embedder-general.
- **Track B's null is not an attenuation result** (§6) and must not be reported as one.
- Corpus overlap of 100/334 pool content words is reported, not eliminated.

## 9. What this document does not do

The v1.6 symmetry — one transforming method's gain decomposing to size, another's to information —
is **a structural observation about this instrument's reach** and is stated only in those words. It
is not a comparative claim about the two methods, and no sentence here ranks them.

Nothing here says anything about the formatter in either direction, revisits v1.6's KILL, PW-1, or
any closed verdict, or makes an external claim of any kind; the disclosure gate is untouched. No
paper text, no recommendation. Nothing under `v17/`, `v18/` or `v19/` was modified; v1.9 remains
parked at `5bc4aeb`.

**STOP at Gate 1 for the ruling.**
