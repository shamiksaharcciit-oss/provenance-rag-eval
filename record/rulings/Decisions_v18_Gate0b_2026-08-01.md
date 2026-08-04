# v1.8 Gate 0(b) — rulings on G9–G11, the probe's disposition, and the path to freeze

**Responds to:** agent 2's session report — Gate 0 committed at `601d7d5`, amendments
applied but uncommitted, four probe attempts, no valid probe result, three new findings.
**Date:** 1 August 2026
**Status:** G9–G11 ruled; the probe is abandoned by rule rather than repaired; the branch
is selected without it; freeze after the amendments below. One external action is
Shamik's (§5).

---

## 1. G9 — "temperature 0" is restated: determinism is measured or assumed absent, never
## parameterised

The pinned model rejects the parameter, so §2's "temperature 0" specifies a call that
cannot be made. Ruling: the sampling clause is restated pre-freeze to — *sampling
parameters are omitted (the pinned model accepts no temperature); no parameter-based
determinism claim exists anywhere in v1.8; determinism is an empirical property to be
measured, or, where unmeasured, assumed absent.* The silent-retry path that cached a
`t=0.0` record for a call that never sent it is exactly the kind of self-description with
no procedure behind it that item 7 exists for: the v18 client (§2 below) must record the
**actual request payload** in its call records, so the cache and manifest describe calls
that happened rather than calls that were asked for. The same specification sat in
v1.7's frozen E2 §3.2 and was never exercised — a fact about a closed document, stated
under the valve, complete over its class (second known instance, after the probe-cache
defect).

## 2. G10 — no weaker pin, no second edit outside `v18/`: port the v1.9 pattern

The pin is implementable without touching `src/`: v1.9's Gate 0 did precisely this —
`V19Client` subclasses `LLMClient` inside its own directory, overriding the provider call,
*specifically so the cost guard still binds*. Ruling: **`V18Client`, same pattern** —
override `_call_anthropic` to capture `msg.model`, omit the temperature parameter per §1,
and write true request payloads. PF-5's pin then applies as written: `response.model`
logged per call, asserted constant, run window in the manifest. Where the override must
duplicate provider-call code, bind it against drift with a test that hashes the parent
method's source and fails if `src/` changes underneath — identity-over-assertion, adapted
to the one place identity isn't available.

## 3. G11 and the probe — abandoned by rule; the conservative branch is selected without it

Your handling of the wrong-model artifacts is endorsed in full: renamed `INVALID_*` rather
than edited, because `requested_model` is the honest record; "35/60 divergent" withdrawn
with the artifacts rather than quietly; the fix asserting the served model per result.

But the probe itself is not re-run. Ruling, with the reasons in order:

1. **The probe's purpose was branch selection, and the branch can now be selected by
   rule.** Both targeted-repeat branches are affordable inside the frozen ceiling —
   17,642 calls with generation and judge repeats, against 25,000. The probe's only
   remaining value is saving ~4,000 calls if determinism holds; its cost is ~700 calls
   against a bound that may already be breached.
2. **PF-1's 1,000-call probe bound is treated as consumed.** Cumulative probe spend is
   334–1,018 and cannot be computed, because two attempts' consumption was set by credit
   exhaustion rather than by the plan. Spending further against an indeterminate bound is
   what the bound exists to prevent. The range and its cause are recorded in the manifest
   as the honest number: a range, attributed.
3. **Assuming nondeterminism is the safe direction and costs nothing if wrong.** With no
   temperature pin (§1), nondeterminism is plausible a priori. Median-of-3 over a
   deterministic model returns the deterministic value — the conservative branch is valid
   under either truth, just costlier, and the cost fits.

So: **determinism unmeasured, recorded as such; both targeted-repeat branches active**
(generation 3× and judge 3×, Track A `F768`/`U768` only, per PF-3); every single-run
number carries the strengthened caveat — *single sample, sampling nondeterminism
unquantified, temperature pin unavailable.* The 25,000 ceiling stands; 17,642 is the
frozen projection; breach at run time is a STOP.

Config ruling attached to G11: the two model roles are separated explicitly — arm
construction stays at Opus (cached, reproduces v1.6), generation and judging pin to the
§2 model — each in the v18 run config by name, with a per-call assertion that requested
= configured. Config fall-through to a harness default is how this probe burned; no v18
call may ever resolve its model by default again.

## 4. Two operational orders from the wreckage, both cheap

- **A persistent spend ledger inside `v18/`:** a file-based cumulative call counter,
  written per call batch, committed into the manifest at checkpoints. Your per-process
  budget check reset across runs and the credit deaths made spend uncomputable; the
  ledger makes the 17,642/25,000 accounting survive any interruption. In scope, tested.
- **Incremental persistence for the run:** attempt 3 discarded 194 calls of finished work
  by writing artifacts only at the end. The run phase checkpoints per arm-track-stage;
  an interruption resumes from the last checkpoint via cache. The guard-raise window
  (`max_usd` 150 in the freeze commit, reverted in the results commit) is unchanged.

## 5. The external fact — for Shamik, not the agent

Two probe attempts died on **API credit exhaustion**. No harness change fixes that: the
account balance needs to cover the run before it starts — roughly 17,600 calls, true cost
in the neighbourhood of $50–70 at current rates. The freeze may proceed regardless; the
run should not start until the balance is topped up, and the agent verifies affordability
against the ledger's projection before the first test-set call rather than discovering it
mid-run a third time.

## 6. Endorsements that should not go unrecorded

PF-2's assertion firing on attempt 1 — the bypass that isolated the cache directory but
left caching on — is G2 reproduced *inside the fix for G2*, and it was caught by the
guard built for exactly that, on its first opportunity. The commit-ordering correction
(reverting to Gate 0 state so history shows B2 present and then removed by amendment) put
the true sequence in the record at the cost of extra work, which is the right trade. The
error list itself — including the invented 589 MB figure corrected to 736 — is A1f
practised as a habit rather than a rule.

## 7. Freeze instruction

1. Apply G9–G11: sampling restatement, `V18Client` with payload recording and
   parent-source-hash test, model-role separation with per-call assertions, spend ledger,
   incremental checkpointing. Extend the §0 amendments table to PF-1…PF-11.
2. Full suite green.
3. **One freeze commit**: plan + code + prompts + tests + the probe disposition (the
   INVALID artifacts' hashes, the spend range, the branch-by-rule declaration) + the
   17,642 projection + the `max_usd` 150 raise.
4. Run only after the balance check (§5). Then `Results_v18_InstrumentDivergence.md` per
   the plan — three-instrument table, `F_BIAS` = B1 alone with single-member Holm stated
   as identity, descriptive companions with discordant counts, costs actual vs projected
   against the ledger, item-7 self-check with output in the record — and STOP at Gate 1.

No further Gate 0 stop is needed: everything discretionary is now ruled. v1.9 remains
parked at its freeze until v1.8's results commit exists, unchanged.
