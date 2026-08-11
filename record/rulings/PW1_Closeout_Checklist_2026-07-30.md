# What's left: PW-1 to a signed result, and the paper to a disclosure decision

State as of `cab0b8e` · 2026-07-30

"Finalize" has two possible scopes and I've covered both, because they're coupled: PW-1's outcome
can force further paper corrections, so the paper cannot close first. If you meant only PW-1,
sections 1–5 are the whole list. If you meant through to release, 6–7 matter more than any of it.

---

## 1. Blocking right now

1. **The 64-longest-texts, fresh-process, batch-64 experiment.** Decides whether a zero-deviation
   encoding path exists, and therefore whether the §3.2/§3.3 measurement block is needed at all.
2. **`.dist-info` mtimes / `pip cache list` / pip log forensics**, and **`OMP_STACKSIZE`.** Both
   cheap; record them even when they fail.
3. **Confirm C-2's field list covers the native stack** (`torch`, `transformers`,
   `sentence-transformers`, `tokenizers`, threading runtime) rather than inheriting the published
   runs' field list.

Nothing else in this document can be sequenced confidently until (1) resolves, because it decides
whether family 1 has two embedders or one.

---

## 2. The remaining B-sequence

**B3 — confirm it landed.** You declared it next after B2 and then reported B4. The 136 passing
tests suggest it's in, but I have no artifact for it. NC-A (S0 hit / S1 MISS / S2 HIT / S3 MISS)
and NC-B (S0 hit / S1 HIT / S2 MISS / S3 MISS), extended to S2 as frozen. If it hasn't landed, it
gates B5 — those are the negative controls that establish the stripping code does what the ladder
says it does, and running arms without them means the arms' output is uninterpretable.

**B4 — close the two blocked cells**, by whichever route §1 produces. Three possible end states,
in descending order of value: zero-deviation path found (guard passes clean, arms clean);
mitigated path with the full measurement block (`PASS UNDER DECLARED DEVIATION`, and the deviation
attaches to the arms too); or blocked, family 1 down to one applicable cell.

**B5 — the arms.** S1, S2, S3 across the applicable cells, with S2 primary. Watch for: the `r > 1.0`
diagnostic order pre-decided if any cell runs mixed-path; the A7 halt gap fixed first (§3 below),
since half the grid currently takes the unguarded path; and encoding fragility, which now bites the
arms for all four family-1 cells regardless of how the guard resolves.

**B6 — the results document.** Should carry, at minimum: the eight cells with their S0–S3 values
and `r`, the per-family aggregate under `aggregate()`, the family-2 qualifier in the position §7
requires, the errata block from §4 below, and every guard's disposition.

**One check on B6 that's easy to miss:** every guard named in §8 of the sealed text needs a
recorded outcome, including any that were never run. A guard with no entry is indistinguishable
from a guard that passed, which is the same failure class as `BLOCKED / ENVIRONMENT` — you already
fixed it in one place; make sure the results document doesn't reintroduce it.

---

## 3. Code items still open, all pre-arm

**The A7 halt gap.** `interpret.py:69` divides without the guard on the NOT APPLICABLE path;
`test_branch_1_not_applicable_short_circuits_and_still_reports_r` pins that behaviour. Frozen
`halt_conditions` says "r > 1.0 for **any** cell," and four of eight cells now take that path.
Hoist the check so it runs wherever `r` is computed, and amend the test. The code
under-implements a stamped rule, so the fix is to the code.

**The `delta_full == 0.0` inconsistency.** `retention_ratio` raises `ZeroDivisionError`; the NOT
APPLICABLE path returns `r = None` for the same input. Both defensible, should be one decision.

Do both before B5. They're small and they're inside the path every arm runs through.

---

## 4. The errata block

Five items, none of which touches a stamped input. They should live in a **dated block beside the
freeze**, not inside it — the one-shot rule means the freeze records what was frozen, and
corrections are additive and dated.

1. **§6's declared method.** Says exact sign-flip enumeration; the carried `p_raw` values came
   from `paired_permutation_p`. Record the discrepancy, compute the exact table with
   `exact_signflip_p` and place it beside the stamped values with K per cell, and attach the
   invariance proof (all three families give one classification vector across the entire feasible
   exact-p range).
2. **The CI procedure is unnamed.** §5 asserts three criteria agree while specifying two. Name it:
   `paired_bootstrap_diff`, percentile method, iteration count and seed — and state that it is a
   second procedure, not the test's inversion, which is why it can disagree on the secondary
   bge/B cell.
3. **`descriptive_companion_cells`** enumerates two cells where its general clause now covers
   four. Prefer deleting the enumeration over extending it.
4. **`source_document_sha256` doesn't name its object.** Record which byte sequence it covers, and
   record the hash of the `freeze_text_verbatim` block separately, since that block is the
   designated authority.
5. **Any declared deviation from B4**, if the encoding path changes — including, if applicable,
   that family 1's bge cells carry a retention ratio built from two embedding paths.

Item 1 has a small piece of computation attached (the exact table). Schedule it; it's independent
of everything else and can run any time.

---

## 5. PROC-1 and the template

**A new class for PROC-1: declaration/implementation divergence.** The four existing instances are
incomplete-criteria failures; §6 is different — a fully specified procedure that isn't the one
that ran. The authoring gate that catches an incomplete rule will not catch this, so it needs its
own check: for each declared procedure, name the function that implements it and assert the
declaration matches at freeze time.

**The pinning lesson**, which you've already recorded: pin at every freeze, before there's a reason
to. Worth stating as the general form — a pin's value is realised only when something breaks, so
its field list must be chosen for what could break, not for what the analysis config happens to
contain.

**A1e and A1f are in.** The tripwire test should be documented as a tripwire, so nobody "fixes" it
by updating the constant when it goes inert.

---

## 6. The paper

Two corrections are unconditional and don't wait on the arms: **PW1-F1** (the methods description)
and **PW1-F3** (the word "significantly" on the C4 headline).

`Semantic_Formatter_WhitePaper_v2.pdf` is currently with your manager for approval, carrying both
defects. I raised this a few steps back and you haven't come back on it, so I'll put it more
plainly: every day it sits there is a day someone might approve text that you already know is
wrong, and an approval obtained on defective text is worse than no approval — it consumes the
approver's willingness to review and produces a sign-off you'll have to go back and undo.

A short note naming the two corrections costs you very little. It's also the version of events
where you found the problems yourself and said so, which is the version you want on the record.

Beyond those two, **the paper can't be finalised until PW-1 concludes**, because the arms decide
whether the provenance-width correction leaves the headline intact. If family 1 ends up as a
one-cell aggregate, that is itself a material fact about the strength of the evidence and belongs
in the paper regardless of which way the arms come out.

---

## 7. Decisions that are yours, not the agent's

**The disclosure route** — defensive publication, file first, or internal-only. This is the
irreversible gate: Europe has no grace period, so external disclosure destroys novelty absolutely.
Internal circulation for approval doesn't, which is why the current approval round is safe. This
decision has to be made before anything is disclosed externally, and it should be made *after* PW-1's outcome
is known, because the outcome changes what you'd be disclosing.

**How to report family 1 if it ends up one-cell.** If B4 resolves to (b), family 1's aggregate
comes from MiniLM/Track A alone. That's a reportable result, but it has to be reported in those
words rather than inferred from blank rows — and it's worth deciding in advance whether a one-cell
primary family is something you'd publish, or whether you'd hold and solve the encoding problem
properly first.

---

## 8. Definition of done, as a checklist

PW-1 is finished when all of these are true:

- B3's negative controls pass at S2.
- Every guard named in §8 has a recorded outcome, including blocked ones with their halt class.
- The A7 halt covers every path that computes `r`.
- All applicable cells have S1/S2/S3 values and a classification produced by `classify_cell`, not
  by a human reading a table.
- Each family has an aggregate label from `aggregate()`, with the family-2 qualifier attached in
  the required position.
- The errata block exists, is dated, sits beside the freeze, and the stamped values are unchanged.
- The results document states what was blocked and what that costs, in plain sentences.
- Whatever `archive_placement` points at actually exists and contains the bundle.

The paper is ready for a disclosure decision when PW-1 is finished, PW1-F1 and PW1-F3 are applied,
and any further corrections the arms imply are applied.

---

## 9. If you do one thing today

Run the two-minute experiment. Then send the approver the two-line note. The first unblocks
everything downstream; the second is the only item on this list with another person's time
running against it.
