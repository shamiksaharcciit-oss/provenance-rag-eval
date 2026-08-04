# v1.9 Gate 1 — ruling: PR-1 stands, PD-4 is attributed, and one missing stage is
# executed before closure

**Responds to:** `Results_v19_ReadingResidual.md` at `dfbd511`; PR-0 scored first (A PASS,
B quarantined); PR-1 CONFIRMED (+0.1106, CI [+0.066, +0.157], p 0.0001); PR-2 FAILS;
PR-3 not executed; item-7 check 15 claims with two self-caught defects.
**Date:** 2 August 2026
**Status:** findings adopted; PD-4 attributed within stated limits; PR-3 ordered executed
as a supplement; v1.9 closes on that supplement's commit unless it surfaces a STOP.

---

## 1. PR-1 is adopted, and the formatter's ledger finally has an entry

The frozen licensed sentence applies exactly as sealed: **formatter prose improves
extractive answer quality at equal token cost and equal structural delivery, when the
answer is present in context** — established on Track A (n = 176, the corpus built to
contain the defects the formatter repairs), at +0.1106 mean token-F1, p 0.0001, with the
scope clauses attached: nothing about retrieval, packaging, ranking, or deployment;
Track B unmeasurable at this task difficulty (quarantined by PR-0's gap clause, not
negative); and the contamination disclosure carried.

Robustness the reader can do from the printed rows, recorded here descriptively: removing
the six imbalanced pairs entirely leaves the remaining 170 at ≈ +0.104 — the result does
not ride on the shortfall queries. That arithmetic uses only §7's printed values; no new
procedure touches `F_READ2`.

## 2. The internals are reported with their names, and two of them get labelled
## hypotheses

**The abstention asymmetry is a component, not an artifact.** `U768` answered NOT FOUND
fifteen times with the gold present by construction; `F768` once. An abstention on a
present answer is a reading failure, so it is legitimately part of what PR-1 measures —
but it is a *distinct mechanism* from graded extraction quality, and the two are fused in
+0.1106. Any formal split is a new quantity and belongs to a future pre-registration;
the results document's side-by-side presentation is the licensed form. The behavioural
fact itself deserves its sentence: **fragmented context induced abstention on answerable
queries fifteen times more often than repaired context** — descriptive, Track A,
deployment-relevant, no mechanism.

**PR-2's failure is real and gets a named HYPOTHESIS, clearly labelled.** Exact
containment requires the answer to reproduce the *original* span text; `F768`'s packages
carry *formatted* text, in which structure and references — though never vocabulary —
may lawfully differ from the original. An answer quoting formatted text faithfully could
therefore fail verbatim containment while scoring high token-F1. That would make PR-2's
split partly an artifact of measuring verbatim fidelity against a text the treatment is
permitted to edit. **HYPOTHESIS under A1g** — stated here so the split is not read as
mere noise, testable by a future offsets-aware containment check, asserted nowhere as
fact. The prediction failed as sealed and stays failed; the hypothesis is about *why*,
not about the score.

## 3. PD-4 is attributed — within exactly these limits

v1.8 Gate 1 §2 assigned attribution of the unattributed +0.135 to this experiment.
Ruling: **v1.9 establishes that the prose channel exists, is significant, and is of
comparable magnitude (+0.111 at oracle-matched information against +0.135 at fixed-k),
with retrieval removed by construction.** The licensed attribution sentence: *the reading
channel demonstrated by v1.9 is sufficient to account for the bulk of PD-4's composite;
retrieval-set differences need not be invoked to explain it.* What remains unlicensed:
any exact apportionment across the two settings (different budgets, different package
construction), and any claim that retrieval-set differences contributed nothing. The
attribution closes v1.8's open number at the strength the evidence supports and no
further.

## 4. PR-3 is executed before closure — and the order is outcome-independent

The judge secondary was declared in the frozen plan and was not run. That is a gap, the
agent flagged it in exactly the right register, and the remedy is to **execute the
declared stage, not to record its absence as permanent**: a frozen design left partially
unexecuted after results are known invites the question of *which* parts got skipped and
why, forever. Stated for the record: this order derives from "declared stages get
executed" and would have issued identically had PR-1 failed — the judge's verdict on the
formatter is wanted in both worlds, which is what makes running it now clean.

Specification, resolving the same ambiguity G13 resolved for v1.8, by the same logic:
the three generation reps per arm are paired by index; **each of the three rep-pairs is
judged exactly once** (three judge calls per query — satisfying the nondeterminism
fallback over the joint draw), blinded to arm, order randomised per call, prompt as
frozen. Per-query judge direction is the median of the three pairwise verdicts. Scoring:
PR-3 as sealed — agreement of judge direction with F1's direction; judge-favours-`F768`-
while-F1-does-not recorded as the bias signature. ~528 calls, ≈ $1.50, inside every
bound. The mechanical safeguards are the ones already in force: arm-blind judge, no
score content in prompts, ledger accounting, fresh-process scoring.

The supplement is **one appended section** in the results document, marked as executed
post-STOP by this ruling with this document cited — the assemble-once clause bends to
the complete-the-design clause here, and the bend is disclosed rather than smoothed.

## 5. The programme-level sentence this unlocks — held, not yet spent

With v1.9's result, the formatter's completed ledger reads: no retrieval benefit at
matched budget; no structural packaging benefit; **a real reading benefit, at a layer no
retrieval metric measures.** The sentence now licensed for the paper's case study and
the internal report, in exactly this form: *standard evaluation both overstated this
system (crediting size as retrieval gain) and missed its one genuine effect (which lives
below the retrieval layer, in what the model does with the text once found).* That
sentence is the programme's sharpest single claim about the field's measurement stack,
it is now backed at every clause by a closed experiment, and it goes into no external
document until the memo returns. The memo's §3 slot can be filled the moment v1.9
closes; the internal report's frozen language from the plan's §5 applies in its
PR-1-positive branch.

## 6. Endorsements

Flagging PR-3's absence unprompted and in bold rather than letting a missing stage read
as a null; the item-7 check catching its own checker's mis-sum and — the deepest catch
of the series — a self-falsifying compliance sentence, where the statement "no PD-4
sentence appears in this document" was itself the second occurrence; the six pairs
printed raw with the UNKNOWN-not-conservative framing carried verbatim; and the run
landing at 1,982 calls and $24.92 against a $60 guard that was never approached and
never edited. The two-defect commit message is the item-7 practice at its terminal form:
the check's own failures reported inside the artifact the check certifies.

## 7. Closure

On the supplement's commit — assuming no STOP from it — **v1.9 is closed** with record:
frozen plan (`5bc4aeb`), Gate 0 ruling, probe-checkpoint ruling, results at `dfbd511`
plus the PR-3 supplement, and this document. Amendment 5 governs from that commit. The
data phase of the programme ends there: v1.6, v1.7, v1.8, v1.9, v1.10 all closed, every
number reproduced or attributed, and the three reserved decisions — the withdrawn
paper's replacement, the memo, packaging — sit with Shamik on a complete record.
