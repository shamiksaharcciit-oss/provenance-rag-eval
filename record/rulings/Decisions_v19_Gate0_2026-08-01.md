# v1.9 Gate 0 — rulings on G1–G4

**Responds to:** agent 1's Gate 0 build at `f5f48e8`; zero spend, asserted; one blocking
finding.
**Date:** 1 August 2026
**Status:** G2 is ruled, including a correction to its directional claim; G1 endorsed; G3
endorsed and extended; G4's arithmetic error conceded as mine. Freeze after the amendments.

---

## 1. G2 — ruled: all 176 stay, the six shortfalls stand as recorded, and the six pairs
## are printed raw

The finding is correct and the cause is exactly as you state: on six Track A queries,
`U768`'s fixed cuts split the gold across two units, driving B2(q) to 1105–1444, while
`F768` holds the same gold in one unit and then exhausts its document before reaching the
padding target. Not a builder bug — a collision between the max rule and finite documents.

Ruling, in four parts:

**(a) No exclusion.** The six are the queries where naive fragmentation of the gold is at
its worst — the mechanism-carrying cases for a reading experiment, by the same argument
that rejected symmetric exclusion at v1.7's Gate 0. `F_READ2` stays declared over all 176.

**(b) No cross-document padding.** Equalising token counts by padding `F768` with material
from another document would equalise arithmetic while desynchronising content — `U768`'s
padding is same-document and topical, the graft would be foreign. Equal tokens of unequal
kind is a worse imbalance than unequal tokens of equal kind, and it would contaminate the
package semantics for exactly the six queries that matter most.

**(c) The shortfalls stand, recorded — and the results document prints the six pairs
individually.** Six rows: query id, B2(q), both package lengths, both F1 scores, the
per-query difference. Raw and descriptive, no aggregate, no second test — A5b stays
intact because no quantity acquires a second procedure; the reader who wants to know
whether the imbalanced pairs drove PR-1's verdict can see it at a glance, which is
transparency doing the work a sensitivity test would otherwise be reached for.

**(d) One correction to your framing, and it matters: the imbalance's direction is
ambiguous, not conservative.** "Short by 28–76 tokens" reads as a handicap only if more
context always helps. For extraction it often does not: the missing tokens are padding —
distractor material — and a shorter package with identical gold is plausibly *easier*, not
harder (the long-context degradation everyone observes runs exactly this way). So the
honest statement is not "this cannot manufacture a positive PR-1"; it is **"six pairs
carry a token imbalance of unknown sign, bounded at 3.4% of the track, disclosed
per-pair."** The plan and the results document both say it that way. This is the second
time a directional-safety claim has needed demotion to ambiguity in this programme; the
lesson is the same both times — direction claims about biases are hypotheses too.

§1's promise is amended accordingly: *packages are built to exactly B2(q), or short only
by document exhaustion, which is recorded per package; the six known Track A instances are
listed in the plan at freeze; Track B has none (census).*

## 2. G3 — endorsed, and the neutralised quantity gets its own descriptive line

Correct on both counts: the max rule converts `F768`'s compactness into everyone's
padding, that is the intended behaviour of equal-token matching — compactness *is* a size
effect, and neutralising size is the design — and if PR-1 is null, "the packaging
advantage was spent on padding" must appear in the results document as a live alternative
reading, labelled HYPOTHESIS, beside "prose quality does nothing."

Extension: the neutralised quantity is real and already computed, so report it.
**T_a(q) — tokens each arm needs to cover the gold — is promoted to a declared descriptive
companion:** per-arm distributions, both tracks, values and attribution, no test. That is
the compactness fact stated in the units the experiment measures (on the six queries it is
762–768 against 1105–1444), it is the deployment-relevant "gold-delivery cost" a future
experiment would want, and it costs nothing.

## 3. G1 — endorsed, and the specific choice deserves its sentence

Subclassing inside `v19/` rather than wrapping the SDK afresh, *specifically so the cost
guard still binds*, is the right instinct stated the right way: §6 forbids editing the
guard, and a fresh wrapper would have evaded what it could not edit. Proven by test rather
than asserted. `src/` untouched, both ported rulings (pin readability, cache bypass) now
actually implementable. No further instruction.

## 4. G4 — the control undercount is mine

§6's arithmetic assumed one generation per sampled control query; §2 requires two. 120 is
correct, my 60 was wrong, and the corrected projection (1,334 single-run / 2,390 worst
case against the 5,000 ceiling) is accepted. Census clean, cap never approached, control
sample frozen to disk in the commit — all as required.

## 5. Freeze instruction

1. Amend the plan: §1's exact-B2(q) promise per §1(a–d) above, with the six instances
   listed; §2's control arithmetic (120); the direction-ambiguity wording; the six-pairs
   table and the T_a(q) companion added to the Gate 1 results requirements; §6's
   projection figures corrected. Pre-freeze amendments note in §0 listing G1–G4 with
   finding IDs.
2. Add the shortfall-recording test (a package short of B2(q) must carry its shortfall and
   its cause in the manifest, and only document-exhaustion is a permitted cause).
3. Full suite green; **one freeze commit** — plan + code + prompts + control sample +
   tests.
4. Spend sequencing unchanged: not one call, probe included, until v1.8's results commit
   exists. Then probe → branches → run → `Results_v19_ReadingResidual.md`, PR-0 scored
   first, item-7 self-check with output in the record → STOP for the Gate 1 ruling.

Nothing here touches v17/, v18/, the closed artifacts, or Shamik's reserved decisions.
