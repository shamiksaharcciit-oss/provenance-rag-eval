# v1.6 — step 6 authorised, with four requirements for the sweep script

**Responds to:** addendum 01 @ `74d741e`, 2026-07-31T10:15:08Z (freeze `1b01f9b` + 8.2 min)
**Date:** 31 July 2026
**Status:** authorisation + implementation requirements. No arm value exists.

Go for step 6. Four things go into `scripts/segment_size_sweep.py`, all of them consequences of
your own integer-count work, plus one check on myself at the end.

---

## Your ledger improvement changes what v1.6 should report

You did something better than I asked for: you recovered exact integer query counts rather than
transcribing 4-dp decimals, on PW-1 PA-2's precedent. That has a consequence for this
experiment's own outputs, not just for the disclosure.

Track A's test set is **176 queries** and per-query recall is binary. So every rate this
experiment reports is `n/176`, and **every difference between two arms is an exact multiple of
1/176 ≈ 0.005682**. A reported difference of 0.0034, or 0.0080, or anything not on that lattice,
is not a small effect — it is an arithmetic or pairing bug wearing the costume of one.

**Requirement 1 — report integer numerators everywhere.** Every arm value, for every metric
including `recall@budget`, carries its integer hit count beside the rate. Every difference
(`D_size`, `D_ws`, `D_seam`, `D_edit`, `D_text`, `D_reseam`, `D_total`) carries its integer
numerator over the denominator. Track B is `n/150`; state the denominator per track rather than
hardcoding 176.

**Requirement 2 — assert the lattice.** Every point-estimate difference must equal
`k / n_queries` for integer `k`, to float tolerance. This catches misaligned pairing, a dropped
query, a wrong denominator and an accidental re-split — a whole class of failures that a
plausible-looking decimal would otherwise carry straight into the results document. It is the
same class of check as the telescoping identity in §10.3 and carries the same status: a
**wiring check, not a validity check.**

---

## Requirement 3 — record the discordant pairs, and do not test on them

`D_edit(768)` on the published record is +6/176. Six queries. But six *net*: the informative
sample is the queries where the two arms disagree, and that number is currently invisible in
every result this programme has published.

For every contrast, record `n01` and `n10` — queries the first arm hit and the second missed,
and the reverse — alongside the net difference. A net +6 built from 8 and 2 is a different
object from a net +6 built from 40 and 34, and only the second is plausibly noise. This is the
single most informative diagnostic available for effects this small, and it costs nothing: the
per-query vectors are already persisted under §A2.

**Report it descriptively. Do not compute a test from it.** The frozen procedure is
`paired_bootstrap_diff` plus `paired_permutation_p`; adding McNemar or any other test on the
same quantity is a second procedure for one quantity and violates A5b. The counts are context
for reading the interval, not an alternative to it.

---

## Requirement 4 — the retrieval budget must not be truncated by the candidate pool

`recall@budget(1920)` takes units in rank order until the cumulative token count reaches 1920.
At `m = 768` that is roughly 3 units; at `m = 128` it is roughly 15. The retrieval stage draws
`candidate_pool = 50`.

Fifty is comfortably enough on Track A as currently configured — but if any arm's realised `k`
ever reaches the pool ceiling, that query's budget was **not met**, and the arm is silently
disadvantaged in exactly the direction that flatters the large-unit arms. Which is the
programme's existing bias, and therefore the one place a silent truncation would be hardest to
notice.

**Assert that realised `k` is strictly less than `candidate_pool` for every query, every arm,
every cell.** Record the maximum realised `k` per arm in the output regardless. If it ever
fires: stop and report, do not raise the pool — changing the pool changes retrieval for every
arm and is a design change, not a fix.

---

## A check on myself, since I wrote the rule eight minutes ago

Addendum 01 says anything touching a prediction, arm, decision rule, family, metric or halt
condition is a new pre-registration. Requirement 4 stops a run when it fires, which looks like a
new halt condition, and I am not going to route around my own rule by not mentioning it.

The distinction I am relying on, stated so you can reject it: these four are
**implementation-correctness assertions, not pre-registered halt conditions.** They verify that
the metric was computed as the sealed specification already requires — §5 pins `B = 1920`, the
inclusion rule and the token-counting procedure — rather than deciding anything about an
outcome. An assertion that an existing commitment was actually met adds no new commitment. It
is the same class as `assert len(a) == len(b) == len(test_q)` in `common_size_ci.py`, which
nobody would call a halt condition.

If Requirement 4 fires, the stop follows from the sealed metric definition being unsatisfiable
as specified, not from a new rule I added after the freeze. Requirements 1 and 3 add reported
fields, and `reporting_rule` is a floor rather than a ceiling. Requirement 2 is arithmetic.

**None of this touches a prediction, an arm, a decision rule, a Holm family, the metric
definition, or any of the ten halt conditions.** If you think any of the four does, say so
before you implement it — you have overturned three of my rulings so far and the count is
evidence the mechanism works, not evidence anything is wrong.

---

## Then the primary cell

Record the UTC timestamp of the first arm value and the interval from `1b01f9b`. Addendum 01 at
`74d741e` sits inside that interval and must be visible as sitting inside it. The programme's
precedent is 37 minutes.

Persist `arm_inputs` — per-query vectors and per-unit `source_ranges` — at the moment each arm
completes, not at the end of the run (§A2). Every arm in this experiment must be re-scorable at
S2 and S3 without re-encoding.

Pin the embedder on the command line and in the output, never from `config/default.yaml`
(Template §B). `--out results_v16_A_minilm/`, never `results/` (§A4).
