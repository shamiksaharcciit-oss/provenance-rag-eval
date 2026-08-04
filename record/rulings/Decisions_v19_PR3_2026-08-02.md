# v1.9 PR-3 — ruling on the supplement STOP: option (a), with the self-consistency
# requirement, and the cause named

**Responds to:** the supplement STOP — reps 1 and 2's answer texts were never persisted
(scores kept, texts discarded), so §4's rep-pair judging cannot run from the record; a
void fallback attempt was killed mid-flight (<$1, nothing invalid persisted).
**Date:** 2 August 2026
**Status:** option (a) is ordered, amended for self-consistency. The cost premium's cause
is mine and is classified below.

---

## 1. The cause, first: the census family's seventh instance, and it is the ruling side's

§4 specified "the three generation reps per arm paired by index" against an artifact I
never opened. `main_A.json` stores rep-0's text and the three scores; my order assumed
three persisted texts. That is a specification written from an imagined artifact rather
than the artifact — the exact failure the enumerate-from-the-artifact rule names, by the
author who wrote that rule down. The 5× cost premium is the price of that instance, and
it lands on the ruling side's account, not the agent's: keeping scores and discarding
texts was a reasonable reading of "repeats protect the tested family" under a persistence
rule the programme did not yet have.

That rule now exists as a candidate, adopted from the agent's framing verbatim: **when a
stage repeats, persist every repetition's output, not just its summary** — a summary
suffices for the stage that made it and forecloses every stage that comes after.

## 2. Why (a) and not (b)

The generator is measured nondeterministic at 6/20 stable. A single-draw PR-3 under that
instability is a coin-flip presented as a scoring line — it could mislead in either
direction with no variance protection, on a secondary whose entire value is
corroboration. A misleading corroborator is worse than an absent one, and (b) would also
quietly reinstate the single-draw reading G13 rejected for v1.8. If PR-3 is worth
executing — and §4's completion principle says it is — it is worth executing validly.
Costs remain inside every bound: ≈ $15 for this stage, cumulative ≈ $40 against the
untouched $60 guard, 3,566 of 5,000 calls.

## 3. The order, amended for self-consistency

1. **Regenerate** Track A `F768`/`U768`, 3 reps per arm per query, same frozen prompt,
   plan-pinned model asserted per the standing order — **persisting every rep's text**
   (1,056 calls).
2. **Score token-F1 on the regenerated answers** (local, free, frozen normalisation) —
   because PR-3's agreement comparison must run on identical answers, and the
   regenerated draws are new draws. **PR-1 is untouched**: its scores stand as scored,
   no re-scoring, one procedure per quantity. The supplement's F1 values exist solely as
   PR-3's reference and are so labelled.
3. **Judge each rep-pair once** — pair by index, 3 judge calls per query (528), blinded
   to arm, order randomised, no score content in prompts, fresh-process scoring.
4. **PR-3 scored as sealed** on the supplement's own answer set: per-query judge
   direction = median of the three pairwise verdicts; agreement with the per-query F1
   direction *of the same answers*; judge-favours-`F768`-while-F1-does-not recorded as
   the bias signature. Descriptive; no test.
5. The supplement section declares, prominently: its answer set is **disjoint from
   PR-1's draws** (a persistence defect made the original reps unrecoverable — stated,
   with this document cited); its F1 numbers corroborate but do not touch PR-1; and the
   PR-1-vs-supplement mean difference, whatever it is, is a reproduction observation
   across independent draws, reported descriptively — which the nondeterminism verdict
   predicts will not be exactly zero.
6. Item-7 self-check over the amended final text, output in the commit; ledger updated;
   one commit. **v1.9 closes on that commit** per Gate 1 §7 unless this supplement
   surfaces a further STOP.

## 4. Endorsements

Killing the run mid-flight on reading your own code — after launch, at your own expense
in time and under $1 in spend — rather than letting a void `pr3.json` enter the record;
classifying your fallback as exactly the G13-rejected reading; and declining to choose
between options whose cost difference the sanctioning ruling had not seen. All three are
the STOP discipline working at its terminal position: the last stage of the last
experiment, with the finish line visible.
