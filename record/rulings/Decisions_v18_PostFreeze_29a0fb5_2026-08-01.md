# v1.8 — ruling on the post-freeze change at `29a0fb5`

**Responds to:** freeze at `a6c5547`; declared post-freeze fix to `batch.py`'s `custom_id`
parser; Batch G submitted and collecting.
**Date:** 1 August 2026
**Status:** the change is **ratified**, with its class named and one procedural note.

---

## 1. Ratified, because it is forced — and forced is the operative word

The frozen format string puts `query_id` in a field position; real query ids contain the
separator (`A-040-marlin-planner::syn`); a uniform split therefore cannot parse the
mandated format over the real corpus, and the assertion that enforces the format makes the
design unrunnable rather than silently wrong. The fix — parse four leading and two
trailing fields, treat the middle as `query_id`, assert every other field separator-free —
is the unique reading that honours both the frozen format and the real ids. Any
alternative would have moved a frozen element (the format, the ids, or the assertion).

Under the discretion criterion, that is the deciding property: **a change with no
discretion in it is not a decision, and the freeze exists to police decisions.** No
metric, arm, prompt, statistic, projection or ceiling moved; the commit is separate and
declared; the 64-char assertion added alongside is a tightening (measured 33–47 against
the limit), which claims less latitude, not more.

## 2. The class, for the record — the domain census earns its third instance

This is the same failure family as E1's whitespace defect (metric specified over imagined
provenance, not sentence-range unions) and v1.9's F2 (a global budget specified over
imagined gold runs, not the real straddles): **a specification frozen against the author's
mental model of a domain rather than a census of it.** Here the imagined domain was the id
alphabet. The candidate rule already queued — before freeze, every specification is
exercised against the real structural variety of its inputs — would have caught all three.
It goes to the next pre-registration with that third instance attached.

## 3. The procedural note

The ideal order was: STOP, report the collision, fix on ruling — the same path v1.9's F2
took pre-freeze. The agent instead fixed, committed separately, and declared before any
result existed, reasoning that no choice existed to rule on. The reasoning is correct and
the outcome is what a STOP would have produced, so nothing is quarantined and nothing
re-runs. But the precedent is stated narrowly to keep it from stretching: **a post-freeze
repair may proceed without a ruling only when the design is unrunnable as frozen, the fix
is forced in the §1 sense, the commit is separate, and the declaration precedes any
result.** Anything short of all four is a STOP. Discretion claimed under this precedent is
discretion, and the freeze governs it.

## 4. Otherwise

The freeze is in order: the four modules close PF-9…PF-12 as ruled, the guard raise is the
single authorised edit and is enforced by diff rather than promised, `run.py` post-freeze
per precedent, the projection matches to the call, and the between-stages conduct (row
counts, model constancy, triage only) is exactly PF-12 §7. Batch G proceeds; Batch J on
collection; the results document once, after J; STOP at Gate 1. Nothing further is needed
from this side until then.
