# Confirmation — `posthoc_PW1_freeze_TEXT_FOR_CONFIRMATION.md`

**A1 is satisfied.** I read the file directly from the repository rather than from a paste — `<repo-root>` is attached to this session, so from here on send a path and I will read the artifact itself.

**The text is confirmed subject to four residual items**, three of them small. Two are half-landed A-items from the last round rather than new findings; one is a question still unanswered; one is a hole I did not spot before. Fix these four and stamp.

---

## 1. Verified

Everything checkable in the text reproduces.

**Holm within families is correct in both.** Family 1: raw 0.00010 / 0.00020 / 0.01350 / 0.34227 × (4,3,2,1) → 0.00040 / 0.00060 / 0.02700 / 0.34227, matching §5 exactly. Family 2: 0.02050 × 2 = 0.04100 and 0.09309 × 1 = 0.09309, matching. The published `p_holm` values are correctly traced to the run's own six-member pairwise family and correctly excluded.

**Guard 1's published levels are internally consistent with every `delta_full` in §5, and all of them are on grid.** Family 1: 0.5682/0.7216 = 100/176 and 127/176, difference 27/176 = +0.1534 ✓; 0.3533/0.3800 = 53/150 and 57/150, difference 4/150 = +0.0267 ✓; 0.6080/0.7557 = 107/176 and 133/176, difference 26/176 = +0.1477 ✓; 0.3600/0.4267 = 54/150 and 64/150, difference 10/150 = +0.0667 ✓. Family 2: 0.7841/0.8409 = 138/176 and 148/176, difference 10/176 = +0.0568 ✓; 0.7898/0.8352 = 139/176 and 147/176, difference 8/176 = +0.0455 ✓. Every level, every delta, every CI bound sits on its track's grid.

**`W_cover` checks out as defined.** 1/(1 − 0.5610) = 2.2779 against the stated 2.2781, and 1/(1 − 0.5265) = 2.1119 exactly. The four-quantity table resolves A4's spread properly, and the note that `excess` has no meaningful corpus-level union — 96.6% of the corpus, measuring nothing — is a better answer than the reconciliation I asked for.

**The 0.7330 trace closes my error against the artifact.** 0.7330 − 0.4318 = +0.3012, matching the +0.301 parent-dilution inflation figure. Different quantity, different experiment, exactly as stated. Related: my earlier citations of `harness/results/` and `harness/results_v13/` were paths in this session's own sandbox from an extracted bundle, not repository paths. Your note that no `harness/` directory exists is correct and nothing should be searched for under that name.

**Landed cleanly and needing nothing further:** §0 scope of exposure with "NET" doing the right work; §1's pre-stamp justification; §3's `arm_semantics` distinguishing correction from handicap; §5's `boundary_rule` on a CI bound of exactly zero; §7's five branches, which are exhaustive and disjoint, with `r < 0` correctly falling into NOT SEPARATED; §8's `guard_1_order`, the four-item halt list, and NC-A/NC-B extended to S2 with the right expectations (NC-A: S2 HIT; NC-B: S2 MISS); §8's `at_risk_guard_1`, which records that both items were raised as well as how they cleared; PW1-F2 now correctly saying three corrections rather than two, consistent with §1's disclosure.

---

## 2. Residual — fix these four, then stamp

### 2.1 PW1-F3's consequence covers the wrong direction, and sits in the wrong section

PW1-F3 ends: *"It bears directly on how a NOT SEPARATED result on family 2 would have to be reported."*

NOT SEPARATED is the safe direction. If family 2 returns NOT SEPARATED, the conclusion is that the composition difference depended on inherited ranges — unflattering, self-limiting, and nobody misreads it.

**The dangerous direction is SEPARATED.** If family 2 returns SEPARATED, the results document says the composition advantage survives correction of the ruler — and absent an explicit qualifier that reads as *the C4 claim is vindicated*, when PW1-F3 has just established that the claim is not licensed by the programme's own frozen rule in the first place. A surviving effect is not an established claim. That is the sentence a reader will take away, and it is the one the freeze does not currently prevent.

**Do:** state the consequence for **every** family-2 label, not only NOT SEPARATED, and put it in **§7 beside `aggregation`** rather than in §9 among the findings. Suggested placement and wording:

```
family_2_labels_carry_a_qualifier          # PW1-F3
    "Every family-2 classification, whatever it is, is reported with the qualifier that the
     contrast being tested is one the v1.1 pre-registration's prose_rule does not license as a
     'beats' claim (PW1-F3). Family 2 measures whether the OBSERVED composition difference
     depends on inherited ranges. It cannot establish the C4 > C0 claim, and a SEPARATED result
     in particular must not be reported, abstracted, or summarised as vindicating it."
```

§9 is where findings live; §7 is where the classifier and the reporting rule live. A qualifier that governs reporting has to be in the section the results document is generated from.

### 2.2 A3c did not land — the §A5 pattern needs its own record and a forward control

PW1-F3 notes the third instance in passing. That is not the same as recording it. Three independent instances — v1.3's incomplete criteria, v1.5's `significant_definition`, v1.1's `prose_rule` — is not three mistakes, it is evidence that the template rule is not being applied at authoring time, and the only useful response is a control on future authoring rather than a note about past failures.

**Do:** add a standing finding separate from PW1-F3, and a gate:

```
PROC-1
    "Three independent instances of the template §A5 defect — a criteria field naming more than
     one quantity or more than one procedure — have now been found: v1.3's incomplete criteria,
     v1.5's significant_definition, and v1.1's prose_rule ('CI excluding 0 after Holm'). Each was
     found after the fact, by a reader, not at authoring time.
     GATE: every criteria field in every future pre-registration is checked against §A5 — one
     quantity, one procedure, exhaustive and disjoint — before the file is sealed, and the check
     is recorded in the file."
```

Worth one line in the eventual write-up: reference 8 claims the archive is checkable in one place; the archive was checked, and checking it produced a finding against the paper. That is the discipline working, and it is the strongest thing the programme can say about itself.

### 2.3 A4b closes by arithmetic — one line, and the judgment call disappears

I asked whether `W_index_char` matches the mechanism §11 describes. It does, and the freeze can say so as a fact rather than leaving it a choice.

§11's mechanism is stated per indexed **token** — a formatted unit claims more original surface per indexed token, so at fixed *k* it has more chances to overlap a gold span. The corresponding ratio of ratios is `W_index_token`:

- Track A: 15.9662 / 6.8877 = **2.3181**, against `W_index_char`'s 2.3182.
- Track B: 12.5845 / 5.3434 = **2.3551**, against `W_index_char`'s 2.3574.

Identical to four significant figures on Track A and to three on Track B. The char and token denominators give the same answer, so PW1-F1's use of `W_index_char` is mechanism-faithful and not a selection among four numbers.

**Do:** add to `pw1_f1_refers_to`:

```
    "§11's mechanism is stated per indexed TOKEN. W_index_token's ratio of ratios is 2.3181 (A)
     and 2.3551 (B), against W_index_char's 2.3182 and 2.3574 — the same figure to three or four
     significant digits. The choice of denominator does not move the finding. W_index_mean (3.09)
     is a mean of ratios, not an aggregate, and is never used for the headline figure."
```

That pre-empts the obvious hostile question — *why that one of the four* — with arithmetic rather than with a rationale.

### 2.4 `family_secondary` is declared with no frozen inputs

§4 declares C4-vs-C0 on Track B as a secondary family. §5 gives it no classification row, and §8's `guard_1` gives it no published levels. As written it is a family that exists in the freeze with nothing frozen about it, which is the one thing a freeze cannot contain — its inputs would have to be supplied after the stamp.

**Do:** either give it its published levels, `delta_full`, CI, raw p and branch-1 classification in §5 alongside the other six cells, or reclassify it explicitly as descriptive-only in the manner of `arm_1_clean_gold`, which is already the right template for a thing that is reported but does not run inferentially. Either is fine; leaving it declared-but-unspecified is not.

---

## 3. Still open from the work order

**A7's question is unanswered in the text.** §8 records `RatioExceedsOne`, the unbypassable classifier path, the 1e-9 float slack and the demonstration test — all good. What it does not say is how the exhaustiveness sweep that tripped the halt was fixed. The correct fix is to bound the sweep so `delta_corrected ≤ delta_full` by construction, since that is the structural truth the halt encodes. If instead the sweep acquired a `pytest.raises` wrapper that lets it continue past the halt, or any suppression parameter, that is a hole in the guard we just installed. One line in reply; it does not need to go in the freeze.

---

## 4. Confirmation

With 2.1, 2.2, 2.3 and 2.4 applied, **the freeze text is confirmed and you may stamp.** No re-confirmation round is needed for those four — they are additive, none touches a definition already settled, and none is a judgement I would want to see again before it is sealed.

Then B1 with a real UTC timestamp, and B2 guard 1 on MiniLM / Track A alone.
