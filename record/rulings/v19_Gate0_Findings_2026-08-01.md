# v1.9 Gate 0 — build complete, findings before the freeze

**Status:** THE FREEZE HAS NOT HAPPENED. `Plan_v19_ReadingResidual_2026-08-01.md` is untracked
and nothing is sealed. Gate 0's build is complete and its tests pass; one finding changes text
the freeze would make permanent, so this stops for a ruling.
**Date:** 1 August 2026
**Executing agent:** agent 1.
**Spend: ZERO.** No model call of any kind was made — not a probe call, not a generation. The
plan forbids any call before the Gate 0 ruling and before v1.8's results commit exists; both
hold. Inventories were built from `cache/llm` behind a guard that raises on a miss rather than
spending.

---

## What is built and green

| | |
|---|---|
| `v19/arms.py` | inventories by **import** of v1.6's `build_arm`, with a runtime identity assertion; `test_queries` uses an explicit `is None` sentinel (v1.7 F5) |
| `v19/control.py` | PR-0 sampler (seed 1337, n=30/track), successor-with-wraparound mismatch, B2(q) across all three arms |
| `v19/generate.py` | `V19Client`, the G5 pin, the G2 cache-bypassing probe with its fresh-call assertion, the G6 anomaly log |
| `v19/gate0_build.py` | domain census, control sample, cost projection |
| `v19/tests/test_v19_gate0.py` | **21 tests, all passing** |
| full suite | **245 passed, 0 failed, exit 0** — nothing outside `v19/` touched |

All five §7-required tests exist and are named as such: overlap-not-coverage selection,
mismatched-package wiring, the fresh-call assertion, `response.model` constancy, B2(q) equality
across arms.

**Nothing under `v17/` or `v18/` was modified.** The v1.8 workstream has files staged in the
index by the other agent; every commit I make is by explicit pathspec so that work is never
swept into mine.

---

## G1 — the shared client cannot express two frozen requirements, and v1.9 subclasses rather than edits

Both ported rulings are unimplementable through `LLMClient` as it stands:

- **G5's pin** requires `response.model` logged on every call. `LLMClient._call_anthropic`
  returns `(text, input_tokens, output_tokens)` and **discards `msg.model`**. No caller can see
  it.
- **G2's bypass** requires repeats that read nothing and write nothing. `complete()` returns
  early on a cache hit and unconditionally writes on a miss, so every repeat after the first is
  served from disk — the probe would measure the cache, which is the exact defect G2 ruled on.

§8 forbids editing anything outside `v19/`, so `V19Client` **subclasses** `LLMClient` inside
`v19/`. `src/` is untouched.

**The reason it is a subclass rather than a fresh SDK wrapper is the cost guard.** A hand-rolled
client would have bypassed `max_llm_calls` and `max_usd` entirely. §6 forbids *editing* the
guard, which certainly forbids *evading* it, so `complete_uncached` runs the same two checks
before any paid call — and `test_uncached_path_still_obeys_the_cost_guard` proves it.

**No ruling needed unless you disagree with the approach.** Recorded because "implemented by
subclassing a shared class" is a design decision a reader should not have to discover.

## G2 — six Track A queries break the equal-tokens guarantee, and the short arm is always `F768`

This is the finding that blocks the freeze.

§1 promises packages built to **exactly B2(q)** for every arm. The census says otherwise on
Track A:

| track | queries | escalated | **packages unequal across arms** |
|---|---|---|---|
| A | 176 | 6 | **6** |
| B | 150 | 65 | 0 |

**The six unequal queries are exactly the six escalated ones**, and on every one of them the
short arm is `F768`:

| query | B2(q) | `F768` | `U768` | `U256` | `F768` shortfall |
|---|---|---|---|---|---|
| `A-008-quartz-resolver::f4` | 1444 | 1368 | 1444 | 1444 | 76 |
| `A-023-harbor-sharder::f4` | 1346 | 1300 | 1346 | 1346 | 46 |
| `A-019-crag-broker::f4` | 1247 | 1199 | 1247 | 1247 | 48 |
| `A-012-ridge-indexer::f4` | 1152 | 1124 | 1152 | 1152 | 28 |
| `A-036-halcyon-cache::f4` | 1111 | 1058 | 1111 | 1111 | 53 |
| `A-000-kestrel-indexer::f4` | 1105 | 1058 | 1105 | 1105 | 47 |

Shortfall 28–76 tokens, **1.9%–6.9%** of the package.

**Mechanism, and it is not a bug in the builder.** B2(q) escalates when one arm's minimal
gold-covering set is large. On these six it is `U768`'s: its fixed cuts split the gold across two
768-token units, costing 1105–1444 tokens, while `F768` holds the same gold in **762–768
tokens** — one unit. B2(q) then takes the *maximum*, so everyone pads to `U768`'s cost. `F768`
cannot reach it because the formatter's output is smaller than the source document, so the
document runs out and `build_package` records a shortfall exactly as §3.1 says it should.

**Two things follow, and they point in opposite directions.**

*Against worrying:* the imbalance is **directional against the treatment**. `F768` receives
*less* context, never more, so this cannot manufacture a positive PR-1. A null would be the
outcome it could bias toward, and a null is already the prior.

*Against ignoring it:* equal tokens within each pair is the design's one non-negotiable
guarantee, stated in those words. 6/176 is 3.4% of the decision-bearing track, and `F_READ2` is
declared over **all 176 test queries**.

**Options, none of which I have taken:**

1. **Declare an exclusion at freeze** — drop the six from `F_READ2`, pre-registered with the
   count and the query ids listed. Symmetric and outcome-independent, but it removes the queries
   where the arms' packaging differs *most*, which is the objection that killed the analogous
   proposal in v1.7's F2.
2. **Cap B2(q) at what every arm can supply** — `min` over arms of available document tokens,
   floored at the gold cost. Preserves exact matching; shrinks the package on those six and
   changes what B2(q) means.
3. **Accept the shortfall, report it per query** — keep all 176, record the six token counts
   beside the result, and state the direction of the bias.
4. **Something else.**

I have no recommendation that is not a preference about what `F_READ2` is measuring, and the
plan does not determine it, which §1 of the Gate 1 instructions makes a STOP.

## G3 — B2(q)'s `max` rule converts the formatter's compactness into everyone's padding

Not a defect and not blocking; recorded because it shapes how a null must be read.

On the six escalated Track A queries, `F768` packs the gold into 762–768 tokens and `U768` needs
1105–1444. Because B2(q) is the **maximum** across arms, `F768`'s package is then padded with
~600 tokens of neighbouring material it did not need. **The formatter's boundary placement,
where it works, is spent on padding rather than shown to the generator as compactness.**

That is the correct consequence of equal-token matching — the alternative is unequal tokens, the
confound the whole programme exists to remove. But if PR-1 comes back null, "the packaging
advantage was converted into padding" is a live alternative explanation to "prose quality does
nothing", and the results document should say so rather than let the null read as broader than
it is.

## G4 — census, control sample and projection, all clean

**Domain census** (the practice v1.8 named: the builder meets the corpus's real variety before
freeze, not the author's model of it):

| track | inventories `F768`/`U768`/`U256` | B2(q) min/median/max | escalated | attribution | cap 8192 | builder failures |
|---|---|---|---|---|---|---|
| A | 90 / 90 / 238 | 1024 / 1024 / 1444 | 6/176 | `U768` 6 | 0 | **0** |
| B | 381 / 378 / 1072 | 1024 / 1024 / 3840 | 65/150 | `U768` 54, `F768` 11, `U256` 2 | 0 | **0** |

`GoldExceedsBudget` never fired; the 8192 cap is not approached; no query failed to package.

**Control sample** drawn and written to `v19/results_gate0/gate0_census.json` so the Gate 0
commit freezes it rather than the run redrawing it. 30 per track, seed 1337, sorted before
sampling so the draw depends on the id set and seed and not on loader order (tested).

**Cost projection**, recomputed from the census rather than restated from the plan:

| | calls |
|---|---|
| generation, single-run (326 × 3 arms) | 978 |
| PR-0 control (30/track × 2 tracks × correct+mismatched) | 120 |
| determinism probe (20 Track A dev × 3) | 60 |
| judge (Track A) | 176 |
| **total, single-run branch** | **1,334** |
| **total, worst case with G3 targeted repeats** | **2,390** |
| declared ceiling | 5,000 |

**Under the ceiling on both branches.** The plan's own estimate was 1,864 single-run and ~3,000
worst case; mine is lower because the plan counted the probe at its ≤500 bound rather than at the
20×3 it actually needs, and counted control at 60 rather than 120. **The plan under-counted the
control by half** — §2 requires each sampled query generated *twice*, correct and mismatched, and
60 is one generation per query. That is a second small correction to the frozen text.

---

## What I have not done

- **No freeze commit.** G2 changes §1 or §3; G4's control count changes §6.
- **No model call, no spend**, and no v1.9 call path exercised against a real provider.
- **No E3, no report drafting, no recommendation.**
- Nothing outside `v19/` and this document. `v17/`, `v18/` and every closed artifact untouched.

## What happens on a ruling

G2 needs a decision. G4's call-count correction is arithmetic. G1 and G3 need only your
agreement that they are recorded correctly. Once settled I amend the plan, re-run the suite and
the census, and make the Gate 0 freeze commit — plan plus `v19/` code, tests, frozen control
sample and census — after which no wording change is possible without a new pre-registration.
