# v1.6 — reading the primary cell, and what the remaining cells can and cannot do

**Responds to:** primary cell @ `2eedb4e`; freeze `1b01f9b` → completion 10:40:53Z, 34 minutes
**Date:** 31 July 2026
**Status:** ruling, written **before** A-bge and B-MiniLM have been run. That timing is the point.

---

## First: the branch is already determined, and the remaining cells cannot change it

I am writing this before either remaining cell exists, so that it cannot later look like a
reaction to one.

Read the frozen decision rules against the primary cell:

- **ADOPT** requires `D_edit` significantly positive **in cell A-MiniLM**. It is 0/176 at 768
  and +7/176 at 384 with `p_holm` 0.61454. Fails.
- **ADOPT_SCOPED** requires significance confined to one pre-named admissible scope. The
  admissible list is closed: `{m=384 only}`, `{m=768 only}`, `{Track A only}`,
  `{all-MiniLM-L6-v2 only}`, `{strict only}`. Nothing is significant anywhere in the primary
  cell, so no scope qualifies. Note also that **`{bge only}` is not on the list** and cannot be
  added now. Fails.
- **REJECT_HARM** requires a significant negative. Fails.
- **KILL** requires `D_edit` not statistically distinguishable from zero on
  `recall@budget(1920)` in cell A-MiniLM. **Satisfied.**

**A-bge and B-MiniLM are declared non-decision-bearing, and the branch is KILL whatever they
show.** If bge comes back with a positive, significant `D_edit`, that is a robustness
observation and a candidate question for a different experiment — it is **not** a rescue, not a
scope, and not a reason to revisit this. Run both cells, report both in full, and name the
branch KILL.

You already said naming the branch waits for the results document, and that is right
procedurally. This is not naming it early; it is fixing in advance what the remaining evidence
is permitted to do, which is the only moment at which saying so costs nothing.

---

## What the numbers actually say

**The apparatus is sound.** Four-for-four exact reproduction to the query — `U768` 138/176,
`S768` 140/176, `F768` 144/176, `U256` 100/176 — means the arms are wired correctly, the split
matches, the environment holds, and the decomposition is being computed on the same objects the
programme published. A null from an apparatus that reproduces is worth something. A null from
one that did not would be worth nothing.

**The claim fails and the confound is confirmed as the effect.** At 768, of `D_total`'s +24
queries, **+23 come from the size dial alone**. Seam placement contributes +1. Editing
contributes 0. The programme has been attributing to an editing pass an advantage that is
almost entirely the cutter's setting.

**`D_ws` = 0 exactly at both sizes.** The `_emit` whitespace artifact is verified harmless, the
upper bound turned out to be nil, and `D_seam` needs no correction. That was worth the control
even though — especially though — it came back empty.

**P2 is the sleeper result and must not be reported as a footnote.** Under recall@5,
`D_size(768)` is 138 − 100 = **+38/176**. Under `recall@budget(1920)` it is **+23/176**. Fifteen
queries — about 39% of the published size effect — were a **metric artifact**: recall@5 rewards
larger chunks for handing the scorer more text per unit retrieved, and correcting for that
removes nearly two-fifths of the apparent benefit. Stated the other way, **recall@5 overstates
the chunk-size effect by roughly 65% relative to a budget-matched metric.**

That finding is independent of the formatter, independent of this programme's thesis, and
applies to anyone benchmarking chunking strategies with a top-k metric. It may well be the most
generally useful thing v1.6 produces. Give it its own section in the results document, not a
line in a table.

But report the other half of it just as plainly: **+23 survives.** The size effect is not
merely an artifact. At matched retrieval budget, cutting at 768 still beats cutting at 256 by 23
queries, built from 34 discordant favourable against 11 unfavourable. Bigger segments genuinely
retrieve better here, and that is now the programme's best-evidenced empirical claim.

**The discordant counts turn a null into a finding.** `D_edit(768)` is a net 0 built from
`n01 = 8` and `n10 = 8`. The editing pass is **not inert** — it changes the retrieval outcome on
sixteen queries. It changes them in both directions equally. Report it in those words. "No
effect" implies the pass does nothing; what the data show is that it does something *arbitrary
with respect to retrieval*, which for a practitioner is the worse of the two findings, because
it means the pass introduces variance without expected gain. That distinction is invisible in
the net and would have been invisible in this programme's published results too. It is the
clearest vindication R3 could have got on its first outing.

**On the 384 column, resist the obvious temptation.** `D_edit(384)` is +7/176 and is the largest
single term at that size, which will read to someone as "it works at 384 and we tested the wrong
size." `p_holm` is 0.61454. It is noise, and the one-shot rule means it cannot be re-tested on
this split. If you want that question answered it is a v1.7 on a different track or a freshly
generated corpus, and it needs its own pre-registration. Say so in the results document so that
nobody else has to have the idea and be talked out of it.

---

## `D_text` and `D_reseam` — disposition

The frozen rule is that a null `D_edit` is not decomposed, and you honoured it. You also told me
the values (−4 and +4, cancelling) while flagging exactly why you were doing so. That was the
right call and I want the boundary drawn explicitly so it is not left to judgement next time.

**The rule forbids interpretation, not existence.** The arms ran; the numbers exist; §A2 requires
them persisted. Suppressing their existence would create a different integrity problem — a
reader who knows `F@S` was built will ask what it produced, and an unexplained gap invites a
worse inference than the numbers themselves support.

So, in `Results_v16_SegmentSize.md`: **state that `D_text` and `D_reseam` were computed as a
mechanical consequence of the arms existing, that the pre-registration forbids decomposing a
null `D_edit`, and that they are therefore recorded in the run artifact and not interpreted
here.** Do not print the values in the narrative, do not test them, do not draw a sentence of
inference from them. Anyone re-scoring the persisted artifact can find them, which is as it
should be.

P7's conditional fails — `D_edit(768)` is not distinguishable from zero — so P7 is **not
evaluated**, and that is reported as "conditional not met," never as "not falsified." P6 is
evaluable and holds.

---

## R4 — my number was wrong and you caught it before it cost anything

I wrote `candidate_pool = 50` and reasoned that fifty was comfortable. The actual retrieval
depth was **10**, and the budget needs ~16 units at m=128. Max realised `k` came in at 16. **The
truncation I invented the check to prevent would have happened**, silently, and it would have
understated precisely the small-unit arms — biasing the result in favour of large units, which
is this programme's existing bias and therefore the direction in which a silent truncation is
hardest to notice. It would have corrupted `D_size` and P5 specifically.

You verified `pool = max(candidate_pool, top_k)` leaves the fused ranking identical, so no arm
is advantaged by running at depth 50. Record the depth change in the results document with that
justification — it is a run parameter that differs from the naive reading of the config, and
PROC-1 applies.

I had the mechanism right and the number wrong. Finding that before implementing rather than
after running is the fourth time the gate structure has paid for itself; keep the habit.

---

## Consequences that are already frozen

The KILL consequence rule is written and is not negotiable now: the white paper's claim is
amended to *"better segmentation retrieves better; editing is not separately demonstrated at
matched retrieval budget."* The formatter's human-readability and verbatim-guardrail results are
unaffected and stay as written.

**Do not touch the white paper or the brief** (§12.10). Report to Shamik; the wording is his
call, and v3 will need an amendment pass he has not yet authorised.

Under every branch, `D_size`, `D_ws` and `D_seam` are reported as first-class results. They are
the reason the experiment exists, and at 768 they are now the only terms with anything in them.

---

## Order from here

1. A-bge. Report in full; not decision-bearing.
2. B-MiniLM. Cache-served only — **halt and ask before any fresh LLM spend.**
3. `Results_v16_SegmentSize.md`: P1–P7 scored line by line, P7 marked conditional-not-met, the
   branch named **KILL**, the recall@5-versus-budget finding given its own section, the
   discordant-pair reading stated in words, the depth-50 parameter recorded, and the
   `D_text`/`D_reseam` disposition stated as above.
4. Stop there. The paper, the brief, and the disclosure decision are Shamik's.
