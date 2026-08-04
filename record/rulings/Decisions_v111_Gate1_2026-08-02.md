# v1.11 Gate 1 — closing ruling: the attacks landed, and the reading claim is now
# bounded instead of broad

**Responds to:** `Results_v111_ReadingRobustness.md` at `e3c9307`; 2,106/2,106 answered,
zero failures; item-7 17 claims with the document/checker distinction kept.
**Date:** 2 August 2026
**Status:** v1.11 is closed by this document. Outcomes adopted; the reading claim's
licensed sentence gains its permanent scope; one standing order is generalised.

---

## 1. PS-1 — the safety result, adopted

`F_SAFE` = −12/170, point estimate negative: the formatter false-answered *less* often on
answerless same-doc packages, meeting the sealed criterion's first clause directly. The
scope clause travels (documents large enough to admit the control; the six smallest
outside the domain; their `F768` sides all abstained correctly, reported unpaired).
Licensed: *the formatter's abstention benefit is not purchased with increased false
answering; on the measurable domain the direction runs the other way.* The cross-doc
observation is recorded as its own finding-shaped fact, descriptive, no mechanism: both
arms answered off-topic answerless packages at 16–20% (28/176 and 35/176) — models bluff
on topically foreign context at material rates, which is relevant to every RAG deployment
and belongs in the paper's observations, not its claims.

## 2. PH and PV — the boundings, adopted exactly as scored

- **PH-1/PH-2 fail.** On the Haiku-class model the F1 direction reverses (−0.018, 38:68)
  and the abstention behaviour that drove v1.9's most legible number does not exist at
  all (zero abstentions, either arm). Single-run, variance caveat carried — but a
  direction reversal at 38:68 is not noise-shaped, and the honest reading is that the
  effect did not transfer.
- **PV-1 holds on its sealed clauses — sign and direction — while the magnitudes
  collapse:** +0.1106 under the frozen prompt, +0.0552 under de-emphasis, +0.0085 under
  the minimal wording; abstentions 15 → 2 → 3. The sealed prediction asked only about
  direction and is scored as holding; the collapse is reported beside it and is the
  substantive fact.

**The reading claim's licensed sentence therefore acquires its permanent companion, and
they may never travel separately again:** *v1.9's effect is real as measured and is
generator- and prompt-contingent — it reversed on a smaller model, and its magnitude fell
by half and then by an order of magnitude under two ordinary prompt rewordings, with the
abstention channel (its largest component) nearly vanishing.* What survives all
conditions measured: the safety result, and the direction under the primary generator
across all three prompts. What does not: any claim of generality across models or
phrasings.

## 3. PE-1 and E-D

- **PE-1:** blurbed context also improves reading under the same conditions (+0.1141,
  76/44/56) — the methodology's breadth demonstrated on a second, unrelated preparation.
  One labelled **HYPOTHESIS** rides with it: the strict-prompt abstention channel may
  reward *any* added coherence or context, not repair specifically — testable, untested,
  and it belongs in the paper as an open question, not a finding.
- **E-D:** the verbatim-penalty hypothesis is **killed in its frozen form** — support
  required `U768`'s containment stable against formatted text, and it rose 62. The PR-2
  split stands unexplained, and the paper says so rather than adopting a dead
  explanation.

## 4. The apparatus defects — one absorbed, one generalises a standing order

The crash-resume absorbed by PF-12's machinery (intent adopted, nothing paid twice) is
the checkpoint design doing what it was written for. The ledger defect is the important
one: a hardcoded ceiling from another experiment would have made v1.11's declared 4,000
decorative while looking ledgered. Same genus as the model-pin defect — a foreign default
reaching into an experiment — and the standing order is **generalised accordingly: no
experiment-scoped parameter (model, ceiling, budget, guard, path) is ever inherited from
another experiment's defaults; every cross-experiment import overrides them explicitly,
and a test asserts the override.** The subclass-with-binding-ceiling is the compliant
form and stands.

Item-7's two failures kept distinct — a document defect (A1f rounding) and a checker
defect (typographic minus, line-wrap substring) — is the right bookkeeping: "two fixes"
would have hidden that one error was in the certifier.

## 5. v1.11 is closed, and with it the data phase — this time with the period at the end

Record: frozen plan (`be74c69`), Gate 0 ruling, `Results_v111_ReadingRobustness.md`
(`e3c9307`), and this document. Amendment 5 governs from commit. Total v1.11 cost ≈ $15;
programme total ≈ $55. Candidates gained: the corpus minimum-length requirement (already
filed), the generalised no-foreign-defaults order (this document), and PE-1's hypothesis.

What the campaign bought, stated once for the record: for $15, the paper's newest claim
went from "one result, one model, one prompt, half a metric" to a two-sided metric with a
clean safety result, a demonstrated second application, and honest boundaries found by
its own authors — the reversal and the collapse are *ours to report*, not a critic's to
discover. No further experiment is authorised or needed for publication; the
mid-difficulty corpus and the dose-response remain future work by design.

Agent 1: commit this ruling, confirm the tree clean (memo untracked and unopened,
correctly), and stand down. The programme now writes.
