# v1.6 — all cells complete: what goes into the results document, and what does not

**Responds to:** A-bge and B-MiniLM complete; six `D_edit` estimates, six nulls
**Date:** 31 July 2026
**Status:** final ruling before `Results_v16_SegmentSize.md`. Nine items, three of which
change what you were about to write.

---

## 1. The branch is KILL, and six nulls are a different object from one null

Confirmed. Nothing in either non-decision-bearing cell disturbs it, which is what the
primary-cell ruling fixed in advance and is the only reason that ruling was worth writing.

But say more than "the branch is KILL." A single null in one cell supports the sentence *we
did not detect an effect*. Six estimates across two embedders, two tracks and two sizes, with
the largest anywhere being +7/176 and `p_holm` 0.615, supports a stronger and more useful
sentence: **the effect is not present at any size, embedder or corpus this experiment can
reach.** As rates the six are +0.0398, 0, −0.0057, +0.0114, −0.0133, −0.0133 — straddling zero
in both directions with a mean around +0.003, about half a query out of 176. Estimates
behaving like draws from a zero-centred distribution is what an absent effect looks like.

**Do not turn that into a statistic.** The six are not independent — the two Track A cells
share a corpus and a query set, and the two sizes within a cell share everything — so pooling
them, meta-analysing them, or reporting a combined interval is a second procedure for a
quantity that already has one, and A5b forbids it. State the six, state the pattern in words,
state plainly that they are not independent and are therefore not combined. The description
carries the weight; a fabricated summary statistic would only give a reader something to
attack.

---

## 2. The bge reproduction contains something you did not flag

You reported the three within-stack bge reproductions as apparatus validation, which they are.
Look at what they say substantively:

`U768` = 0.7898 = **139/176**. `F768` = 0.7727 = **136/176**.

On bge, under `recall@5`, the complete formatter is **three queries worse than the naive
cutter** — and those are *published* values, reproduced exactly. The programme's headline
result, that the formatter improves retrieval, does not merely weaken on a different embedder;
on the published metric it reverses. `D_edit(bge, 768)` at matched budget is +2/176, so there
was never anything there to lose.

This is a within-stack comparison of two published bge values, so it is legitimate and it is
descriptive — a reproduction check, not a new test. **Report it. Do not test it.** Integer
numerators, no CI, no p-value, no mechanism.

I am flagging it because it was sitting in your validation paragraph doing no work, and it is
more consequential than most of what the run produced. It also sharpens what KILL means: the
editing pass is not a thing that works on MiniLM and fails to replicate elsewhere. There is no
embedder in this programme's record on which the complete pass beats the naive baseline once
you account for anything.

---

## 3. Track B's inversion — the run's most transferable observation, and it needs four protections

You are right that it is the most transferable thing here, and right that it sharpens the
finding rather than complicating it. `recall@5` does not merely inflate chunk-size effects; on
real academic prose at matched budget it reported **the wrong sign**. `U256` reproducing
published `original_256` at 53/150 = 0.3533 exactly rules out the apparatus, which is the first
thing anyone will reach for.

Four things must travel with it, in the same section, not in a footnote:

**(a) Its status, in the same breath as the claim.** Track B is exploratory, `dev_fraction`
0.0, non-decision-bearing, single corpus, 150 queries. Write that in the sentence that states
the inversion, not below it. A reader who takes the finding away should be unable to take it
away without its scope.

**(b) Its discordant counts.** −15/150 net is not yet an object I can read. Built from 20
against 35 it is a broad, consistent tilt; built from 3 against 18 it is a handful of queries.
R3 requires `n01`/`n10` for every contrast, so you have them. Print them here above all places.

**(c) No test, unless the plan already declared one.** Check whether `D_size` on Track B sits
inside a declared Holm family. If it does, report the Holm-corrected p and nothing further. If
it does not, **report it descriptively with integer counts and discordant pairs and compute no
test now** — reaching for one because the number came out interesting is precisely the move the
one-shot rule exists to prevent, and it would cost this observation the credibility that makes
it worth reporting.

**(d) No mechanism.** There is an obvious story — dense localised answer spans in real prose,
large chunks diluting them, a fixed budget buying more distinct spans when units are small,
while `recall@5` hands 5 × 768 tokens to the large-unit arm and 5 × 256 to the small one. It is
coherent, I find it plausible, and it is a **HYPOTHESIS** under A1g. It does not go in the
results document as explanation. If you want it recorded, put it in a clearly labelled
speculation paragraph that states it is untested and names what would test it. An exploratory
finding with a mechanism attached stops reading as an observation and starts reading as a
claim, and this one is too useful to spend that way.

And the standing bound: **this must not be used to revisit PW-1's conclusion**, and it says
nothing about the formatter — it is a statement about a metric and a chunk size.

---

## 4. Drop the artifact-share column

39%, 56%, "the whole effect and past it" is a ratio whose denominator is the `recall@5` effect,
and on Track B that denominator is +5/150. A ratio with a near-zero denominator is unstable by
construction: it is not that Track B's share is large, it is that the quantity is undefined in
any useful sense there, and "past it" is the arithmetic telling you so.

Report the **two absolute numbers per cell** and let the reader do the subtraction:

| cell | recall@5 | recall@budget | change |
|---|---|---|---|
| A-MiniLM | +38/176 | +23/176 | −15 queries |
| A-bge | +32/176 | +14/176 | −18 queries |
| B-MiniLM | +5/150 | −15/150 | −20 queries, sign reversed |

That table says everything the percentage column said, says it in the units the experiment
actually measures, and cannot be attacked for dividing by something small. Keep a percentage
only in prose, only for the two Track A cells, and only as a rounded aside.

---

## 5. Amending my own instruction: the single 65% figure does not survive

I told you to give the `recall@5`-versus-budget finding its own section and to state that
`recall@5` overstates the chunk-size effect by roughly 65%. **The section stands. The single
number does not.** It was computed from one cell and I wrote it when one cell was all there
was. With A-bge at a larger share and Track B inverting, one headline percentage is now a
selective quotation of my own evidence.

Replace it with the per-cell absolute figures above and a claim stated at the strength the
evidence supports: **on every cell measured, correcting for retrieval budget reduced the
apparent chunk-size effect; the reduction ranged from partial to complete sign reversal.** That
is stronger than 65% as well as more honest, because it is a direction that held everywhere
rather than a magnitude that held once.

---

## 6. The PW-1 batch restore is not the import I forbade — here is the line

I ruled at Gate 0 that *a decomposition whose base term is imported from a different run, under
a different environment, is not a decomposition; it is a comparison across two records.*
Restoring `U256`'s encoder batches from PW-1's `orig256` by content hash looks like the same
move and is not, and I want the distinction written down before someone reads the two together
and concludes the rule is negotiable.

What I forbade is importing a **result** — an arm value computed in another run, another
environment, another config — and subtracting from it. What you did is restore an
**intermediate**, keyed by the hash of a byte-identical input, and then compute the arm value
in this run under this environment. The determinism claim is testable, was tested
(`tests/test_pw1_safe_encode.py`), and the environment pin block records the stack that
produced it.

**The line: an artifact may be restored across runs when it is a pure function of inputs that
are byte-identical and the function's determinism is separately verified. A quantity that
entered a decision may not, whatever its provenance.** Record both the hash and the fact of the
restore in the run manifest under PROC-1, so a reader can see that `U256` was not re-encoded
and can check why that is sound.

---

## 7. Record the memory margin as a margin, not a success

224 MB free against a 393 MB failure point in PW-1 is a pass with roughly 40% headroom on a
number that is itself a single observation. The sharded path held and that is real, but the
honest record is *it worked, and the margin was thin.* Put both numbers in the run notes. If
this apparatus is run again on a larger corpus or a larger model, that pair is the thing the
next person needs, and "zero crashes" alone would tell them nothing.

---

## 8. Scope discipline on the predictions

Score each prediction **against its sealed text, on the cells it was stated over, and no
others.** If P2 was stated about Track A, then Track B does not confirm it, does not falsify
it, and does not appear in its scoring line — the inversion is a separate observation that
happens to point the same way. Write it in the observations section and reference it from P2's
line if you like, but do not let it into the score.

You said Track B "strengthens the P2 section," and that is true of the section. It must not
become true of the prediction. This is the same failure the whole freeze exists to prevent,
arriving from an unexpected direction: not softening a prediction to fit a result, but
enlarging its scope to collect one.

P7 remains **conditional not met**, never "not falsified." P6 is evaluable and holds.

---

## 9. Then `Results_v16_SegmentSize.md`, and then stop

Everything from the primary-cell ruling stands, amended only where §5 above amends it. The
document contains: P1–P7 scored line by line against sealed text and declared scope; the branch
named **KILL** with the six-estimate reading of §1; the budget-versus-`recall@5` section built
on absolute per-cell numbers; the Track B inversion with its four protections; the bge
`F768 < U768` observation from §2; the discordant reading in words; `D_ws` = 0 in all three
cells recorded as a control that earned its place by coming back empty; depth 50 recorded under
PROC-1; the cache-restore line from §6; the memory margin from §7; and the `D_text`/`D_reseam`
disposition exactly as drawn.

Then stop, as you said. No paper, no brief, no white-paper amendment. The KILL consequence rule
is frozen and its wording is already written, but applying it to v3 is Shamik's authorisation
and he has not given it. The bge reversal and the Track B inversion both reach further than the
formatter and further than v1.6; that they reach further is a reason to report them precisely,
not a licence to act on them here.
