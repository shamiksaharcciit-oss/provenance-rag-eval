# v1.9 — probe checkpoint ruling: GO, with one standing order generalised

**Responds to:** agent 1's checkpoint — wrong-model first probe caught by the G5 pin,
fixed by plan-pinned generator; correct-model probe NONDETERMINISTIC (6/20 stable);
targeted-repeats branch selected per the frozen fallback; corrected affordability
($30.01 against the guard's 60); stopped before the remaining ~$30.
**Date:** 1 August 2026
**Status:** GO. Three notes, one order.

---

## 1. GO

Continue exactly as frozen and as reported: judge probe → PR-0 on both tracks before any
test-set scoring is read, with its frozen quarantine consequences → main run under the
targeted-repeats branch → `Results_v19_ReadingResidual.md` (PR-0 scored first, six
imbalanced pairs printed raw, T_a(q) distributions, checklist compiled from the
artifacts, item-7 output in the record, v1.8 Gate 1 §2 cited in the contamination
disclosure, no PD-4 sentence anywhere) → STOP at Gate 1.

## 2. The defect class gets a programme-wide standing order

This is v1.8's G11 recurring in a different runner: model resolved from config, config
falling through to a repo default, and — the sharper edge here — two tracks that would
have run on *different* generators silently, because Track B declares an override and
Track A does not. Nothing in any artifact would have recorded it. Standing order,
generalised from G11's v18-scoped ruling to the programme:

> **No experiment's generation or judge model is ever resolved from configuration.** The
> model is pinned in the frozen plan, constructed from that pin, and asserted at
> construction and against `response.model` on every call. A config default that can
> reach a model call is a defect wherever it exists.

The G5 pin caught this on its first live outing — the ruling that "the pin is what can
actually be pinned" has now paid for itself in one catch.

## 3. Accounting notes, accepted

The void probe kept as `probe_VOID_wrong_model.json` with its 60 billed calls is the
INVALID-preserving practice, correctly applied; $0.75 of waste is recorded as waste. The
corrected guard arithmetic (client pins $5/$25, not Opus list) supersedes the earlier
$37/$66 figures and the guard-abort concern — both mine to withdraw, both withdrawn; no
guard interaction exists on either branch.

## 4. Nothing else moves

The frozen design is unchanged — the runner now conforms to it, which is the correct
direction of repair. PR-0's quarantine consequences, the branch selection, the ceiling,
and the no-interpretation rule at Gate 1 all stand as written.
