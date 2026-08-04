# v1.6 — addendum 01 to the sealed pre-registration: undisclosed prior knowledge

**Responds to:** freeze commit `1b01f9b4c760123eb7a26a713e473ad69346bc8d`, 2026-07-31T10:06:54Z
**Date:** 31 July 2026
**Status:** ruling. **Do this before writing `scripts/segment_size_sweep.py`.** No arm value
exists; that is the only reason this is possible at all.

---

## What is missing

`prior_knowledge_at_freeze` records the three published 768 values and both differences. It
does not record a second body of knowledge that existed in my head, and in conversation with
Shamik, **before** the freeze commit — and that conversation is not itself a committed artifact,
so nothing in the repository would ever reveal it.

Specifically, between `d43063f` and the freeze I reasoned aloud over the published ablation
table and reached a component ledger:

| Published condition | recall@5 | Read as |
|---|---|---|
| C0 | 0.7841 | baseline |
| C3-markeronly (= SEAM) | 0.7955 | seam placement ≈ +0.011 |
| C3-noref | 0.7784 | **below baseline** — removing reference resolution costs ≈ 0.040 |
| C3-nodedup | 0.8295 | **above the full pass** — dedup costs ≈ −0.011 |
| C3 (= FULL) | 0.8182 | full pass ≈ +0.034 over baseline |
| C2 contextual | 0.8523 | **a simpler published method outperforms the formatter** |
| C5 formatter + contextual | 0.8523 | no gain over contextual alone |

and from it a stated expectation: that the formatter's retrieval advantage is small — on the
order of six queries out of 176 — that whatever is real in it is concentrated in **reference
resolution**, that **dedup may cost slightly**, and that `D_edit` may well come back
indistinguishable from zero.

That is a prior belief about the outcome, held by the principal, at freeze time. It is not
recorded anywhere in the sealed file.

---

## Why it has to go on the record

The chronology matters and it is favourable, which is exactly why it should be stated rather
than left to be reconstructed:

- **P6 and P7 were formed at `4851f58`**, before the ablation reasoning existed. They are
  blind in the sense the field claims.
- **The ablation ledger arose after that and before `1b01f9b`.** So it did not inform the
  predictions' formation, but it *was* knowledge held at freeze.
- **No arm value has been computed at any point.** The window is open.

The ledger is not cleanly orthogonal to P7 either. P7 predicts that `D_text` carries the
majority of `D_edit` — a claim that the benefit is text quality rather than boundary movement.
"The benefit is concentrated in reference resolution" leans the same way, since ref-resolution
is the component that most obviously improves text. I do not think it determined P7, but a
reader is entitled to weigh that themselves rather than take my word that the two are
independent.

And the disclosure helps in **both** directions the experiment can fall. If v1.6 lands on KILL,
the record shows we suspected it in advance and ran the test anyway. If it lands on ADOPT, the
record shows the result survived a principal who expected it to fail. Undisclosed, the first
case looks like hindsight and the second looks like luck.

---

## Ruling — an addendum, not an edit

**Do not modify `preregistration_v16.json`.** Its hash and timestamp are the freeze, and
rewriting the file destroys the thing the freeze exists to establish.

Write **`preregistration_v16_addendum_01.json`**, committed separately with its own hash and
UTC timestamp, containing:

1. `supersedes: null`; `augments: "1b01f9b4c760123eb7a26a713e473ad69346bc8d"`.
2. The full ledger above, with each value's provenance per PROC-1 (published, Track A,
   `all-MiniLM-L6-v2`, hybrid, any-overlap, recall@5, from `results/results.md` in the v1.1
   bundle), and the differences marked as **derived by subtraction of published point
   estimates, no CI, not a v1.6 quantity**.
3. The stated expectation, in the principal's words, as `principal_expectation_at_freeze`.
4. The chronology: P6/P7 formed at `4851f58`; ledger formed after `d43063f` and before the
   freeze; no arm value computed at any point.
5. The explicit assertion that this addendum **alters no prediction, no arm, no decision rule,
   no Holm family, no metric and no halt condition.** It adds disclosure and nothing else. P6
   and P7 stand exactly as sealed, still marked BLIND, with this note attached to the marking
   rather than replacing it.

Then record in the plan that the addendum exists and why, so it is discoverable from the plan
and not only from the commit log.

---

## The bound on this precedent, so it is not abusable later

State this rule in the addendum itself:

> A disclosure addendum is permitted **only before the first arm value exists**, and **only to
> add** prior knowledge, expectations or provenance. It may never remove or weaken a
> disclosure. Anything that touches a prediction, an arm, a decision rule, a family, a metric
> or a halt condition is not an addendum — it is a new pre-registration, and therefore a new
> experiment under the one-shot rule.

Without that bound, "we can always add an addendum" becomes a way to keep the pre-registration
negotiable after the fact, which is the failure mode the freeze exists to prevent. With it, the
mechanism can only ever make the record more complete.

---

## Then continue

Commit the addendum. Record its hash and UTC timestamp, and state the interval from the freeze
commit — the same discipline as the freeze-to-first-arm-value interval, and for the same
reason.

Then step 6: `scripts/segment_size_sweep.py`, then the primary cell, recording the interval
from `1b01f9b` to the first arm value. The precedent is 37 minutes and it is quoted whenever
the freeze is questioned; the addendum sits inside that interval and must be visible as such.

Nothing else changes. The freeze holds.
