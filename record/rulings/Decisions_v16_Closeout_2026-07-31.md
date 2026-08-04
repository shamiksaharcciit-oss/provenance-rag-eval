# v1.6 — close-out: verification of the results document, two defects, and what carries forward

**Responds to:** `Results_v16_SegmentSize.md` @ `a62e5fe`. Branch: KILL.
**Date:** 31 July 2026
**Status:** I read the document rather than the report of it, and re-derived the arithmetic.
Two defects, both one-line fixes, neither touching a result. Then the programme's carry-forward.

---

## Verification

I have ruled on your reports all programme and at the close it seemed right to check the
deliverable itself rather than sign off on a summary of it. Thirteen re-derivations, all
matching:

Both decomposition identities on integer numerators (4+0+2+7 = 13; 23+0+1+0 = 24). P1's
38/176 = 0.2159. P5's spans, 138−82 = 56 against 132−99 = 33. The six rates and their mean,
0.018789/6 = 0.00313, and 0.00313 × 176 = 0.55 — "about half a query in 176" is exact. The
§3 change column, −15, −18, −20. bge at 139/176 = 0.78977 and 136/176 = 0.77273 against
published 0.7898 and 0.7727. Track B's 53/150 = 0.35333. The discordant sets: 34−11 = 23,
23−8 = 15, 8−8 = 0.

This section originally offered a fourteenth item — that P4's CI half-width times `n` equals the
discordant count, from independent code paths. **It is withdrawn as false. See Correction 01 at
the foot of this document.**

The pipeline's evidence is the thirteen re-derivations above, together with the **eleven** exact
reproductions of published values across the three cells (corrected from eight — see Correction
02):

| cell | exact reproductions |
|---|---|
| A-MiniLM | 4 — `U768`=C0, `S768`=C3-markeronly, `F768`=C3, `U256`=`original_256` |
| A-bge | 3 — `U768`=C0, `F768`=C3, `U256`=`original_256` |
| B-MiniLM | 4 — `U768`=C0, `S768`=C3-markeronly, `F768`=C3, `U256`=`original_256` |

A-bge has three rather than four because `results_v13` carries no ablations, so there is no
published bge `C3-markeronly` to match. That is **an absence in the published record, not a
missed reproduction**, and it should not be read as a partial result.

Both stand without the withdrawn item, which never added anything to them.

The document is the best thing this programme has produced. What follows is small.

---

## Defect 1 — §4.3 states an absolute that §1 breaks

§4.3 says of `D_text` and `D_reseam`: *"No values are printed in this narrative, no test is
computed, and no inference is drawn."*

P6's scoring row prints `D_reseam(768)` = +4/176 = +0.0227, states it is not significantly
negative, and compares it to |`D_text`|. So a value is printed, an interval was computed, and a
comparison was drawn. A reader who reads §4.3 and then flips back to §1 finds the document
contradicting itself, and the natural inference — that the rule was quietly broken — is worse
than what actually happened.

**What actually happened is defensible and the fix is to describe it accurately.** P6 is a
sealed prediction that names `D_reseam`; a sealed prediction must be scoreable, and scoring it
requires its value. `F_MECH` was declared at the freeze, so the quantities and their intervals
are pre-registered and their existence was never in question. My instruction not to print the
values was written about the *narrative* discussion of the mechanism, and it did not anticipate
that a sealed prediction would compel one of them into the scoring table. That is my imprecision,
not your breach.

**Replace §4.3's absolute with the true disposition, in four clauses:** `F_MECH` was declared,
so both quantities and their intervals exist and are persisted; `D_reseam(768)` appears once, in
P6's scoring line, because a sealed prediction names it; `D_text` is not reported as a quantity
anywhere; and the split of `D_edit` into the two is not read, per the frozen rule, so nothing
beyond P6's own verdict is inferred from either.

## Defect 2 — P6's row reads the decomposition it is forbidden to read

*"and does not exceed |`D_text`|"* is a comparison between the two terms of `D_edit`. That is
reading how a null `D_edit` splits, which is exactly what the frozen rule forbids, and it is
doing no work: P6 as sealed says *small and non-negative*, and "small" is established against
P6's own threshold, not against the other term.

**Cut the clause.** P6's evidence is +4/176, non-negative, interval not significantly negative,
within the sealed bound. That scores it completely.

I am flagging something this minor because the wall holds everywhere else in the document and
this is its one gap. A rule that is honoured in six places and quietly crossed in a seventh is
how a rule stops being a rule — not by being overruled, but by acquiring a precedent nobody
argued about.

**Both edits remove interpretation rather than adding any, and change no number.** They are
corrections to prose in a results document, not to the freeze or to any arm value, so they
reopen nothing. Make them, commit, and that closes v1.6.

---

## The two items you surfaced — both handled correctly

**No sealed prediction names a cell.** Your resolution is right and I would not change it. The
decision rules name A-MiniLM throughout and the other two cells are declared non-decision-bearing,
so scoring on A-MiniLM follows from the cell designations even though the prediction text is
silent; labelling that inference HYPOTHESIS and telling the reader they may score differently
without contradicting the freeze is the correct disclosure. You chose the reading that collects
fewer results, which is the right tiebreak when the sealed text is silent.

The defect is in the **template**, not in v1.6, and it is fixed below.

**Track B's `D_size` p-value, recorded and not interpreted.** Correct, and worth noting for a
reason beyond the ruling: I never ruled on this case. You generalised the `D_text`/`D_reseam`
disposition — *the rule forbids interpretation, not existence* — to a situation I had not
anticipated, and you reached the disposition I would have. That is a principle being applied
rather than a instruction being followed, which is the thing the whole apparatus was trying to
produce.

---

## Carries forward to the next pre-registration

Five template amendments, earned by this experiment. They are candidates for
`Amendment_Criteria_Template.md`, not rules yet — that decision is Shamik's and belongs to
whatever comes next, not to v1.6.

1. **Every prediction states, at freeze, the cell or cells it is scored on.** A prediction with
   no declared scope is scored on the decision-bearing cell only, and the omission is recorded
   as a defect. This is the direct fix for §1's gap and it costs one line per prediction.
2. **Every contrast records `n01` and `n10` beside its net difference, always, reported
   descriptively and never tested on.** R3 earned this twice on its first outing: `D_edit(768)`'s
   8-and-8 turned a null into a finding about arbitrariness, and Track B's 8-against-23 turned
   an interesting number into a broad consistent tilt. Neither reading was available from the
   net, and this programme has published net differences for its whole history.
3. **An artifact may be restored across runs when it is a pure function of byte-identical
   inputs and the function's determinism is separately verified. A quantity that entered a
   decision may not, whatever its provenance.** §5's line, promoted.
4. **Every parameter a sweep selects is persisted in the run manifest alongside the value it
   beat.** Carried from before v1.6; still unrecorded; still worth recording.
5. **A closed document may be corrected only in the direction of claiming less, and may never be
   reopened to claim more.** A permitted correction removes a false statement, narrows an
   overreaching one, or withdraws a claim; it never leaves any claim stronger than it found it.

   *The direction test is the rule. "Correct for falsehood" is not*, and an earlier draft of this
   amendment made that the operative clause — a defect the coding agent identified. Almost any
   strengthening can be framed as repairing an understatement, and the framing is chosen by
   whoever wants the edit, so a test that turns on characterising the existing text hands the
   decision to the party with the motive. The direction of travel is observable and is not.

   The rationale stands behind the test rather than in front of it: correcting a false statement
   makes the record more accurate, strengthening a true one makes it more *persuasive*, and **a
   document whose persuasiveness is not fixed at closing is not closed.**

   Applied to this document: Correction 01 withdrew a claim, Correction 02 replaced a wrong
   number with a right one and added no claim, the two results-document fixes removed and
   narrowed. The §4.1 edit would have added. This revision of amendment 5 narrows the latitude
   the amendment grants, so it passes its own test — and it is the last revision of this
   document.

---

## What is closed and what is not

**Closed:** the experiment, the branch, the results document. No paper edit, no brief edit, no
white-paper amendment, and none authorised.

**Open, and all Shamik's:** whether to apply the frozen KILL consequence wording to v3; what to
do about the bge reversal and the Track B inversion, both of which reach past the formatter and
past this experiment; the disclosure decision, now shaped by a retrieval claim that no longer
exists; and whether the apparatus rather than the formatter is the thing worth publishing.

None of those is a v1.6 question and v1.6 should not be reopened to answer any of them.

---

## Correction 01 — a false verification claim, withdrawn

**Added after the fact, deliberately visible rather than silently edited out.** The claim was
made in the verification section of this document; a reader who saw it must be able to see it
withdrawn.

**What I claimed:** that P4's CI half-width × `n` = 8.008 matched the discordant count exactly,
from independent code paths, and that this was quiet evidence the pipeline is sound.

**Why it is false, in two layers.** The arithmetic first: `n01 + n10` is **16**, not 8. The 8
matches `n01` alone, and only because this cell happens to be an exact 8/8 split. Checked across
twelve contrasts in three cells it holds in 1 of 12, and that one — B-MiniLM `D_edit`, 4.00
against 4 — is the same coincidence recurring.

The second layer is worse and is mine to state plainly. **Even a corrected version would not
have been a cross-check.** A paired bootstrap over binary per-query outcomes resamples a vector
whose entries are −1, 0 and +1, and whose nonzero entries are *exactly* the discordant queries.
The interval's width is therefore a function of `n01` and `n10` up to resampling noise — the
relationship being `hw × n ≈ 1.96 × √(n01 + n10)`, which here gives 1.96 × 4 = 7.84, rounded to
8.00 by the 1/176 percentile grid. That is an algebraic property of the estimator, not agreement
between two witnesses. I mistook an identity for a coincidence and then offered the coincidence
as evidence.

**And it cut against a rule this document enforces.** A5b is one quantity, one procedure. The
discordant counts were introduced under R3 as *descriptive context for reading the interval,
explicitly not an alternative to it*. Claiming they corroborated the interval quietly promoted
them to a second reading of the same quantity — the exact move R3 was written to forbid, made by
the person who wrote it.

**The general fact, worth carrying forward:** `n01`/`n10` and a paired interval can never
corroborate each other on this apparatus. R3's value is that the counts reveal structure the net
conceals — 8-and-8 as arbitrariness, 8-against-23 as a consistent tilt — and never that they
provide a second measurement. Anyone reading the two side by side should know they are one
witness, not two.

**Caught by the coding agent, in the document that closes the programme.** Every earlier
correction in v1.6 was to a design decision *before* data existed, where the gate structure is
built to catch things. This one was to a verification claim made *after* the fact, which is the
more dangerous category: a wrong design is caught by the next gate, and a wrong verification
claim is what everyone downstream trusts. A1g exists because a wrong claim in a durable document
is worse than no claim, and I wrote A1g.

---

## Correction 02 — the reproduction count was 8, and is 11

The verification section above originally gave eight exact reproductions across three cells. The
count is **eleven**; the corrected table is in that section. Track B reproduces its entire 768
row, not only `original_256`, and A-bge's three is an absence in the published record rather than
a miss.

**It is recorded with the same visibility as Correction 01 although it cuts the favourable way,
and that is the point.** A correction policy where errors against the author get a monument and
errors in the author's favour get a quiet edit is still an asymmetric policy, and asymmetric
correction is what erodes a record regardless of which direction it leans. The reader-facing test
is whether a number offered as evidence changed, not whether the change was flattering. It was
offered as evidence of apparatus soundness and it changed, so it is marked.

---

## §4.1 of the results document stays as written

The full 768-row Track B reproduction is stronger evidence than the single `original_256` figure
§4.1 cites, and §4.1 is the section carrying the run's most challengeable finding. There is a
real case for the edit. I am declining it, and the reasoning is the durable part.

**The distinction the agent drew is correct and decisive.** The two defect fixes corrected
*false* statements. This would strengthen a *true* one. §4.1 as written is accurate and complete
about what it claims; it simply selects the weakest supporting fact from the set available.

And selection in the conservative direction is what this programme has demanded throughout. I
withdrew my own 65% figure for being a selective quotation of my own evidence. Reopening a closed
document to un-under-claim would reverse that standing preference on the single occasion where
the conservative reading is inconvenient — which is exactly when a standing preference is worth
having.

**The fact does not disappear; it moves.** The eleven-reproduction table sits in this document,
one link from the results document, in an artifact that is a decision record rather than a closed
result. A reader who wants the fullest statement of the apparatus evidence finds it. A reader of
`Results_v16_SegmentSize.md` gets a claim that is true and weaker than the evidence supports,
which is the failure mode worth having.

Template amendment 5 above is this ruling, generalised.
