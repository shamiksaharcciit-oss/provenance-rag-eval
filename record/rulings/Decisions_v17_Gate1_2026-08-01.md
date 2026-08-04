# v1.7 Gate 1 — branch declaration and rulings

**Responds to:** `Results_v17_E1_Integrity.md` at `5176903`; all three cells complete;
stopped at Gate 1 as instructed.
**Date:** 1 August 2026
**Status:** the branch is declared, the metric defect is ruled on and owned, and v1.7 is
closed by this document. Six sections.

---

## 1. The branch: INTEGRITY-KILL, declared

`F_INT` after Holm: `D_int_seam` 0.89471, `D_int_edit` 0.89471. Neither member positive at
`p_holm < 0.05`. The frozen condition is met and the branch is **INTEGRITY-KILL**.

The frozen consequences apply exactly as written at `e19dd35`: **E2 is cancelled**; the
reading-value claim is recorded as structurally unsupported; the residual channel —
equal-integrity fluency benefit — is named as the only surviving reading hypothesis and
testing it requires a new pre-registration. E3 was gated behind E2 and is therefore moot in
this line; the dose-response question survives only as a future pre-registration on its own
merits.

PE1-1 deserves its sentence stated plainly, because it was the prediction the experiment
was built to test: on the corpus constructed to contain the defects the formatter repairs,
formatter boundary placement delivered whole spans in single units **three more times out
of 176** than size-matched arbitrary cuts, interval spanning zero. The structural-packaging
claim is dead on its own cell, by the same instrument and the same discipline that killed
the retrieval claim.

The control ran first and held (`D_int_size` +65/176, p = 0.00010), so this null is a
measurement, not a malfunction: the metric sees the mechanical effect it must see, and does
not see the formatter effect it was built to look for.

## 2. Apparatus, acknowledged

15/15 reproduction asserts, executed rather than written; lattice identity 6/6; F768 fully
cache-served behind a raising guard; nothing spent; item-7 self-check PASS 10/0 with output
in the commit. No notes.

## 3. The metric defect — mine, and here is its classification

The defect: `integrity_*` demands every character of the gold span be covered, formatter
units carry unions of sentence ranges, and inter-sentence whitespace belongs to no unit.
The metric charges formatter arms for whitespace they never claimed. The specification is
mine: I defined coverage over an imagined provenance domain (contiguous ranges) rather
than the one the apparatus actually produces (sentence-range unions). F4's principle — a
metric must be total over its input domain — was honoured on the gold side and not on the
unit side, because the unit side's structural variety was never censused. That is the
lesson to keep: **before freeze, a metric definition is exercised against the real
structural variety of every arm's provenance, not against the author's mental model of
it.** Recorded as a candidate for the next pre-registration (the "domain census"), item
8-shaped, alongside the amended definition for any future use: coverage assessed over
non-whitespace gold characters, or equivalently whitespace-only gaps bridged — chosen and
frozen *there*, not applied retroactively here.

Rulings that follow:

- **The decision-bearing cell survives the defect, and this is established by an executed
  check, not by argument:** the bridging diagnostic's Track A delta is zero on both
  formatter arms. The defect biases *against* the formatter, and on the cell where the
  branch was decided it did not operate at all. INTEGRITY-KILL therefore stands without
  qualification.
- **The Track B quarantine is endorsed in full**: `D_int_seam(B)`, `D_int_total(B)`, the
  S768/F768 levels and ceilings, and PE1-5's failure are artefacts of the defect and are
  not evidence about the formatter, in either direction. The results document reports them
  as the frozen metric produced them, flagged — which is exactly right.
- **No Track B re-run is ordered.** No decision rests on Track B integrity: the branch was
  decided on A-MiniLM, E2 is cancelled regardless, and Track B in E1 was descriptive. A
  re-run under the amended definition is queued as a candidate question for whenever a
  future pre-registration wants Track B integrity for its own reasons — not before.
- **The bridged numbers are characterisation, not results**, exactly as you handled them:
  same standing as the pre-freeze probes. They appear in no results table and are quoted
  only to establish the quarantine's boundary — which is the one use they are valid for.

Not changing the frozen metric mid-experiment, scoring with it as sealed, and diagnosing
separately was the correct order of operations at every step.

## 4. Memory ruling

394 MB free against a ~393 MB known failure point is not a margin; it is a coin that
happened to land flat. Standing order for every future run in every experiment: **a
pre-run margin check with a declared STOP threshold — no encode starts unless free memory
is at least twice the known failure point, or the sharded path is used regardless of
margin.** A-bge completed and reproduced, so nothing is quarantined; but the next
one-megabyte margin is a STOP before the fact, not a note after it. A-MiniLM's absent
margins, stated rather than back-filled, is the honest record and is accepted as such.

## 5. v1.7 is closed

The v1.7 record is: the frozen plan (`e19dd35`), the Gate 0 ruling, the freeze-to-Gate-1
instructions, `Results_v17_E1_Integrity.md` (`5176903`), and this ruling. No further v1.7
document is authorised — no close-out beyond this one, no addendum, no E2 artefact of any
kind. Amendment 5's discipline governs the results document and this ruling from their
commits onward: corrections downward only, and anything new goes to a future
pre-registration.

Queued as candidates, none started: the domain census; the amended integrity definition;
the residual fluency-channel pre-registration question; the Track B integrity re-run
question.

## 6. Boundary confirmation

Your handling of `Plan_v18_InstrumentDivergence_2026-08-01.md` and `v18/` is correct and
stays exactly so: v1.8 belongs to the second agent under its own plan; nothing in v1.8 is
yours to open, and nothing in this ruling changes that. With v1.7 closed, you have no
further tasked work; anything rule-shaped you have left over goes into no document until a
pre-registration asks for it.
