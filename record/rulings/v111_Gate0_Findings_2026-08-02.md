# v1.11 Gate 0 — census complete, three findings before the freeze

**Status:** THE FREEZE HAS NOT HAPPENED. `Plan_v111_ReadingRobustness_2026-08-02.md` is
untracked. Two findings change text the freeze would make permanent; one is a decision the plan
delegated to the census and the census has made.
**Date:** 2 August 2026
**Spend: ZERO generation calls.** The only API contact was `models.list`, which the plan requires
at Gate 0 and which generates nothing.

---

## What is built and censused

| | |
|---|---|
| `v111/ids.py` | v111 custom_id grammar; the **acceptor's** rule imported by identity from v1.8 |
| `v111/prompts.py` | V1 and V2 byte-frozen; the v1.9 prompt imported by identity, never restated |
| `v111/unanswerable.py` | cross-doc and same-doc constructions, with the zero-gold-overlap acceptor |
| `v111/containment.py` | E-D re-score, procedure frozen before any value is seen; zero calls |
| `v111/gate0_build.py` | the census |

**Census results, all executed against the real corpus:**

| check | result |
|---|---|
| same-doc packages checked for gold overlap | **346, zero overlaps** |
| E-E base inventory == v1.6's `U768` (provenance hash) | **True** — the plan's claim holds |
| custom_id cross-product | **2,112 generated, 2,112 unique**, all parse, max length 27 ≤ 64 |
| call table | E-A 704, E-B 352, E-C 704, E-E 352, E-D 0 → **2,112 of a 4,000 ceiling** |
| prompt variants byte-frozen | `frozen` e708031e, `v1` c3ff7b8e, `v2` 3182e733; all retain `NOT FOUND` |
| generation calls | **0** |

---

## G1 — E-B cannot reuse packages by hash; the census decides REBUILD

§2 says the v1.9 packages are "reused byte-identical by hash, or rebuilt by the frozen procedure
— census decides which and records it." **The census decides rebuild, and not by preference:
v1.9 never persisted package text.** Its rows carry `b2`, `tokens`, `shortfalls`, `T_a` and the
answers — no package strings, so there is nothing to hash.

This is the **same persistence defect** that forced v1.9's PR-3 regeneration, surfacing a second
time in a second consumer. It cost 1,056 calls there; here it costs nothing, because rebuilding
from the frozen procedure is deterministic and free. **No ruling needed** — the plan delegated
this and the census answered it. Recorded because the plan's §7 requires the decision be recorded.

**Recommendation, one line, for the freeze:** v1.11 should persist its own package text, or the
next consumer pays the same toll a third time.

## G2 — E-A's same-doc construction is impossible for six queries, all `U768`

The zero-gold-overlap acceptor passed on all 346 packages it could build. It could not build
**6 of 352**: for six Track A queries, the `U768` arm has **no non-gold unit left in the gold
document** once gold-bearing units are excluded — the document is small enough that its gold
occupies every unit.

**They are exactly the six imbalanced pairs from v1.9 §7** — verified by set comparison, not by
resemblance:

`A-000-kestrel-indexer::f4`, `A-008-quartz-resolver::f4`, `A-012-ridge-indexer::f4`,
`A-019-crag-broker::f4`, `A-023-harbor-sharder::f4`, `A-036-halcyon-cache::f4`

The same short documents that exhausted `F768`'s padding in v1.9 now exhaust `U768`'s non-gold
material here. One corpus property, two experiments, two different symptoms.

**This is asymmetric between arms**, which is what makes it a finding rather than a nuisance:
`F768` builds all 176, `U768` builds 170. `F_SAFE` is declared as a **paired** difference on the
same-doc construction, and six pairs cannot be formed. The plan does not say what happens then.

Options, none taken:

1. **Score `F_SAFE` on the 170 complete pairs**, with the six listed and the exclusion
   pre-registered — pairing preserved, n stated, and the excluded set named.
2. **Fall back to cross-doc for those six**, mixing two constructions inside one family — cheap
   but it puts two package kinds under one tested quantity.
3. **Drop same-doc as the family's construction** and test on cross-doc, relegating same-doc to
   descriptive — loses the hard case, which is the interesting one.
4. Something else.

I recommend **(1)** and note it is the same shape as the exclusion *rejected* at v1.7's Gate 0 —
the difference being that here the six are excluded by **construction impossibility**, not by a
property correlated with the treatment, and the impossibility is declared before any value
exists. That distinction is the ruling's to accept or reject, not mine.

## G3 — v1.8's `parse_custom_id` cannot read a v111 id, so v111 defines its own

§6 says the custom_id grammar is "extended with experiment prefix `v111`". `v18.batch.parse_custom_id`
hard-asserts `len(parts) == 8 and parts[0] == "v18"`, and `v18/` is read-only, so the grammar
cannot be extended in place.

`v111/ids.py` defines a 6-field grammar and its own parser, **importing `CUSTOM_ID_PATTERN` and
`CUSTOM_ID_MAX` from v1.8 by identity** so the API's own constraint has exactly one definition in
the repository. Only the v111-specific field vocabulary is new. **No ruling needed** unless you
want the extension done differently; recorded because "extended" and "defined separately" are
not the same word.

---

## What I have not done

- **No freeze commit.** G2 changes §1.
- **No generation call, no judge call, no encode, no spend.**
- Nothing outside `v111/` and this document. `v17/`–`v110/` read-only and unmodified; the internal
  memo draft remains untracked and unopened.

## What happens on a ruling

G2 needs a decision. G1 and G3 need only your agreement that the census's choices are recorded
correctly. Then I amend §1, add the `every-output-persisted` test the plan's §7 requires, re-run
the census and the suite, and make the Gate 0 freeze commit.
