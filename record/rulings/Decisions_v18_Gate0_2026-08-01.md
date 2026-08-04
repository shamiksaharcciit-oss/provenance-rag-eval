# v1.8 Gate 0 — rulings on G1–G8, and the path to freeze

**Responds to:** agent 2's Gate 0 build, stopped per §9; `v18_Gate0_Findings_2026-08-01.md`;
nothing spent, asserted rather than claimed.
**Date:** 1 August 2026
**Status:** all eight findings ruled. Four blocked the run; all four resolve here. The freeze
happens after the amendments and the probes, on the conditional path in §10.

**First instruction:** yes — commit the current build state plus the findings document under
`v18/` paths, clearly marked NOT THE FREEZE, before applying anything below. The v1.7
precedent is right: rulings should point at a hash.

---

## 1. G1 — the contradiction is real, mine, and resolves in favour of the probe

The status header's "no judge call, generation call, or arm value may be spent" was written
to guard the test set and overreached into forbidding what §§2, 6 and 9 require. Ruling: the
header is amended pre-freeze to: **no test-set spend before the freeze commit; dev-set probe
spend is authorised from this ruling onward, bounded at 1,000 calls total across all
probes.** Stopping rather than choosing was correct — two-against-one is a reading, and
irreversible spend does not run on readings.

## 2. G2 — conceded in full, and the fix is a bypass plus an assertion

You are right that the probe as specified measures the cache, not the model, and right that
this is worse than v1.7's F2: an unrunnable design halts, a wrong-answer design runs.
Ruling: probe repeats **bypass the response cache entirely** (read nothing, write nothing),
and the probe harness **asserts fresh-call count = queries × repeats** — the probe fails
loudly if even one repeat was served from cache. The same latent defect sat in v1.7's frozen
E2 §3.2, which specified identical repeats over the same cached client; it was never
exercised because E2 was cancelled at the INTEGRITY-KILL branch. That is a fact about a
closed document, stated here under the valve as a fact, complete over its class (one known
instance), touching no verdict.

## 3. G3 — the blanket median branch is replaced by targeted repeats; the gate stands

The ×3-everything fallback was over-broad: repeats exist to protect the *tested family*, and
only `F_BIAS` is tested. Ruling, frozen as the new §2 fallback:

- Generator probe nondeterministic → generation runs 3× (median F1) **only for Track A
  `F768` and `U768`** — the pair every `F_BIAS` member consumes. All other arm-tracks
  single-run.
- Judge probe nondeterministic → judge calls run 3× (per-query median) **only for the
  answer-level metrics on Track A `F768`/`U768`** feeding B1. All other judge calls
  single-run.
- Every single-run judge-based number carries a mandatory caveat in the results document:
  *single sample, judge variance unquantified.*

The 25,000-call ceiling stands unchanged. The agent recomputes the projection at freeze
under whichever branches the probes select; **projection over the ceiling is a STOP**, not a
trim. The G2×G3 interaction you flagged — the broken probe silently forcing the cheap
branch so the gate is never consulted — is exactly why G2's assertion exists: the branch
choice must now be earned, not defaulted into.

## 4. G4 — the guard is raised by authorised edit, scoped and reverted, and not silenced

Ruling: §10 is amended pre-freeze to authorise **exactly one edit outside `v18/`**: set the
cost guard `max_usd` to **150.0** in the freeze commit, and revert it in the results commit,
both changes stated in their commit messages. The guard's Opus-rate pricing inaccuracy is
**documented in the findings/results, not fixed** — repairing shared pricing code mid-
programme for one run's convenience is scope creep, and the guard still binds meaningfully
at 150 as-computed (~1.5× the projected single-run figure, computed the same wrong way, so
like-for-like). Agent 1 has stood down and v1.7 is closed, so no other consumer runs under
the raised guard during the window.

## 5. G5 — the pin is what can actually be pinned

"Exact version pinned" is amended to its observable form: the requested model id, plus the
**`response.model` string logged on every call and asserted constant across the run** — any
mid-run change is an APPARATUS-STOP — plus the run's start/end timestamps in the manifest.
That is the strongest pin the surface offers; pretending to a dated snapshot that does not
exist would be a self-description with no procedure behind it.

## 6. G6 — Track A's probe verdict governs both tracks, as a declared assumption

Nondeterminism of a pinned model at fixed parameters is a property of the sampler, not the
corpus; the probe's verdict from Track A dev extends to Track B **as a stated assumption
with that reason**, in the plan and the results document. Guard: finish reasons and output
lengths are logged for every Track B call; any truncation, refusal, or length anomaly is
flagged descriptively. Track B's test set is not touched — carving probe queries out of
n = 150 would break comparability with the frozen record for a smaller gain than the
assumption costs. PD-5 stands, and its scoring line carries the caveat.

## 7. G7 — conceded: B2 telescopes to `U768 − U256`, and it leaves the family

The algebra is as you state: `(F768 − U256) − (F768 − U768)` contains no `F768` term. This
is the programme's second telescoping identity caught before it could mislead, and this one
is mine. A "majority" prediction on top of it would have added a ratio with a possibly-small
denominator — the exact instability AllCells §4 removed once already.

Ruling: **`F_BIAS` shrinks to a single member, B1** (Holm over one member reduces to its
plain p, stated as such). B2 is deleted, replaced by the absolute-numbers pattern: the
results document reports, per context metric and track, the three contrasts `F768 − U256`,
`U768 − U256`, `F768 − U768` as values with discordant counts — descriptive, no test, no
ratio; the reader does the subtraction. **PD-2 is restated pre-freeze and descriptively:**
*on the context-metric composite, the size contrast `U768 − U256` will be at least as large
as the residual `F768 − U768`, on both tracks* — scored by direction comparison of point
values, labelled descriptive, never tested. Predicting a tested null was bad form on my
part; predicting a direction between two reported numbers is not.

## 8. G8 — implement the formulas directly; the environment is not perturbed

§3's second branch is taken: no `ragas` install. The pinned environment under which v1.6 and
v1.7's reproduction checks pass outranks the convenience of a library, and the frozen metric
code was already declared canonical over library documentation — this ruling just makes the
library's absence the normal case rather than the fallback. Formula sources (document and
version consulted) are recorded in the metric code's header comments as part of the freeze.

## 9. The mid-write correction

589 → 736 MB, with the sampling basis stated (per-arm, not continuous): acknowledged, A1f
honoured. The corrected number also clears §4-of-Gate-1's memory order with room to spare
for MiniLM-only work; the order still applies to any future encode.

## 10. Path to freeze — conditional, one more STOP only if earned

1. Commit the NOT-THE-FREEZE state (first instruction above).
2. Apply the amendments: header (G1), probe bypass + assertion (G2), targeted-repeat
   fallback (G3), §10's scoped guard edit authorisation (G4), pin wording (G5), track
   assumption (G6), B2 deletion + PD-2 restatement (G7), direct-implementation note (G8).
   Add the pre-freeze amendments note to §0 listing all eight with finding IDs. Update
   tests: fresh-call assertion, B2 removal, `response.model` constancy assert, guard
   revert check.
3. Run the probes on Track A dev, within the 1,000-call bound.
4. Recompute the projection under the selected branches. **If ≤ 25,000 calls: proceed
   directly to the freeze commit** — plan + code + prompts + tests + probe outcomes +
   projection, one commit — and then run. No further stop is needed; everything
   discretionary has been ruled. **If > 25,000: STOP**, report, and the trim is a ruling.
5. Gate 1 as planned: `Results_v18_InstrumentDivergence.md`, item-7 self-check with output
   in the record, STOP. No packaging, no sequencing recommendation.

Nothing in this ruling touches v1.7's closed record, the closed artifacts, or Shamik's
reserved decisions in §7 of the plan, which freeze unchanged.
