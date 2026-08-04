# v1.6 — the empty-segment test, and go for steps 5–7

**Responds to:** Gate 0 steps 1–4 @ `d43063f`
**Date:** 31 July 2026
**Status:** decision + authorisation. Still no plan, no pre-registration, no script, no arm value.

---

## The empty-segment test — split it in two

You are right that this is a design call, and you are right about the defect. But the fix is
not to choose between "hard assertion" and "report and continue." The test is currently
asserting **two different claims under one name**, and that is the thing to repair.

The two claims:

1. **A behavioural invariant, corpus-independent:** when a segment *is* empty, the code
   reports it and does not pad, merge, force or silently drop it. This is what the test's name
   promises. It is true or false about the implementation, not about Track A.
2. **A corpus fact, Track-A-specific:** Track A, under this formatter, at these sizes, yields
   zero empty segments. That is a measurement, and pinning it is worth doing — but it is a
   regression pin, not a gate.

Right now the name states claim 1 and the assertion tests claim 2. That mismatch is the real
problem, and it is worse than either choice you offered: the name is what a reader sees when
it fails, so the first Track B run would produce a failure whose message says the code padded
something when in fact the code behaved correctly and the corpus simply differed.

**Ruling — both tests, named for what they assert:**

- `test_empty_segment_is_reported_not_padded` — construct a fixture where dedup empties a
  segment. Assert the reporting path fires, the segment is not padded or merged, downstream
  scoring proceeds, and the count appears in the arm's recorded output. **Hard, on every
  corpus, forever.** Build the fixture; do not wait for a corpus to supply one.
- `test_track_a_has_no_empty_segments` — the current assertion, renamed, explicitly scoped to
  Track A, with the observed zero recorded as a pinned value. **Hard on Track A only.** If it
  ever fires, something changed underneath us — dedup behaviour, the corpus, the tokenizer —
  and I want that loudly, because it would also mean the published `C3` corpus is no longer
  what it was.
- **Track B and any other corpus: report and continue.** The empty-segment count is a recorded
  field of every arm, reported whichever way it falls, exactly as `D_ws` is.

Record the reasoning in the plan, not only in a failure message. A failure message is a good
place for a hint and a bad place for a design decision — it is only read by someone who has
already hit the wall.

---

## One addition to `preregistration_v16.json` before you freeze it

Gate 0 changed this design. G9 falsified the stated basis of the decision-bearing quantity and
added a whole arm; G2 reversed a halt condition; G10 established that the 768 row is already
published. All of that happened **on code and artifact facts, with no arm value in existence** —
which is the only reason the freeze is worth anything. That fact is currently implicit in the
commit history and needs to be explicit in the sealed file.

Add a field — `design_amendments_before_freeze` — recording, for each amendment: what changed,
what caused it, and the commit it was established at. `86dfa07`, `4851f58` and `d43063f` are
the audit trail; name them. Close it with the assertion, stated plainly, that **no arm value
had been computed at the time of any amendment**, and that the arm set was final at the freeze
commit.

Without it, a later reader sees a design that moved and has to take on trust that it moved for
the right reasons. With it, the amendment history stops being a liability and becomes part of
the evidence — it shows a design that was corrected by scrutiny before it could be corrected
by results, which is the distinction the whole gate structure exists to produce.

Keep `prior_knowledge_at_freeze` as already ruled: the three published 768 values, both
differences, P3/P4 marked sighted, P6/P7 marked blind.

---

## Go

Steps 5–7 are authorised. Plan, then `preregistration_v16.json`, then commit with hash and UTC
timestamp, then `scripts/segment_size_sweep.py`, then the primary cell — in that order, and
record the interval between the freeze commit and the first arm value (the programme's
precedent is 37 minutes).

Everything in the two prior decision documents stands. Nothing in the plan may be softened
against them without coming back to me first — in particular the relabelling of `D_edit`, the
rule that a null `D_edit` is not decomposed, and P7's pre-committed failure branch.

Your pin that `F@S` differs from `F` on 45/45 documents is the right thing to have checked and
it earns its place in the plan: it means `D_reseam` is not zero by construction anywhere, so if
it comes back at zero that is an empirical result about retrieval rather than an artifact of the
arm. That is the difference between a measurement and a tautology, and it is exactly the check
that halt condition 3's wiring-check status leaves uncovered.
