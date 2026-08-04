# v1.6 — rulings on Gate 0, and amendments to the handover

**Responds to:** `v16_Gate0_Findings_2026-07-31.md` @ `86dfa07`
**Date:** 31 July 2026
**Status:** decisions. Still no plan, no pre-registration, no script, no arm value.

Gate 0 did its job. Two of the eight answers changed the design, one of them because I got it
wrong, and you stopped rather than absorbing either. Both rulings are below, with the
amendments they force. There are also **two new gate items (G9, G10)** and **one new control
family** that follow from what you found; complete them before writing the plan.

---

## G6 — the gate is weakened. My §15 was overstated, and you were right to say so.

**Ruling: adopt your recommendation.** The G6 assertion becomes:

1. **Whitespace-normalised equality.** Concatenating a document's SEAM units in order and
   normalising runs of whitespace to a single space reproduces the original document under the
   same normalisation, character for character.
2. **Exact coverage of every non-whitespace character.** The union of SEAM `source_ranges`
   covers every non-whitespace character of the document exactly once.
3. **Non-overlap**, unchanged.

That trio is the assertion that actually tests *"no vocabulary changed."* The original gate
tested that plus a join separator, and conflated the two.

**Do not make `_emit` separator-faithful.** It is the tempting fix and it is the wrong one:
`_emit` is on the path of every formatter condition including FULL, so changing it would mean
`F768` no longer reproduces the published C3 corpus, and the reproduction check in §4 is one of
the few things in this experiment that ties it back to the published record. This experiment
measures the published formatter, not a repaired one. Log the artifact; do not fix it.

**On §15.** I wrote that a G6 failure would be "the most important thing this experiment will
have found." That sentence was aimed at a *vocabulary* failure — a changed token, identifier or
number — and I should have scoped it that way instead of attaching it to the whole gate. A join
separator is not a guardrail breach, and letting my sentence stand would have put a whitespace
artifact into the record dressed as one. §15 is narrowed accordingly: the "most important
finding" language applies only to a change in a **token, identifier or number**. You were right
to push back rather than comply, and that is the behaviour I want on every gate in this
experiment, not just this one.

### But the artifact is not free, and it lands on `D_seam`

`_emit` collapses inter-sentence whitespace; the naive UNCUT arm takes verbatim substrings of
`doc.text` and preserves it. So SEAM and UNCUT differ by more than seam placement, and
`D_seam = S(m) − U(m)` carries a whitespace-normalisation component. FULL goes through the same
`_emit`, so **`D_edit` is clean and the decision-bearing quantity is unaffected** — but `D_seam`
is a reported first-class result and needs a control.

**New control family UNCUT-ws.** For each `m`, take the UNCUT units and apply
`re.sub(r"\s+", " ", text)` to the **unit text only**, leaving `source_ranges` untouched.
Segmentation, provenance and unit count are held exactly fixed; only whitespace moves. Then:

```
D_ws(m)   = U(m)-ws − U(m)          the whitespace artifact, measured
D_seam(m) = S(m)    − U(m)-ws       seam placement, whitespace-matched
```

Declare `D_ws` as an **upper bound**, not an exact replication: collapsing `\s+` across the whole
unit also collapses intra-sentence runs, which `_emit` preserves. If `D_ws` comes back at or near
zero, the artifact is verified harmless and `D_seam` needs no correction. Report `D_ws` whichever
way it falls. It costs re-embedding and no LLM.

### One additional check, cheaper than the argument

You argued that scoring is not broken because a gold span crossing two sentences still overlaps
both ranges under any-overlap. I believe you, and I would still rather have the assertion than
the argument: **assert that every gold span in the Track A test set overlaps at least one SEAM
`source_range`, for every document.** It is a few lines, it is decisive, and it converts a
HYPOTHESIS into a VERIFIED under A1g. Add it to the G6 test module and treat a failure as a halt.

---

## G7 — deterministic path, and here is the argument that settles it

**Ruling: SEAM runs the deterministic path.** But not primarily for cost.

You found that with `reference_resolution` and `dedup` both False, `formatter_system_prompt`'s
ops list is empty and `_chunk_llm` still calls `complete()`. That is a **null-op call to a
generative model on text the arm exists to leave untouched.** The cost (45 fresh calls) is the
smaller problem. The real problem is that it puts a model with an empty instruction list in the
path of the one arm whose entire evidential value rests on its text being unchanged, and any
perturbation it introduced would break G6 — non-deterministically, run to run. The deterministic
path is the **correct** implementation of SEAM, not merely the cheap one. Record it that way in
the plan; "we did it to avoid spend" is a weaker and less durable justification than the one that
is actually true.

**Which mechanism — decide it on one fact you can read in a minute.** Your recommendation
(`markers_only: True`) and your alternative (a none-provider `ChunkContext`, as `run.py:186-189`
already does for the dev sweep) are both acceptable, and they differ in one respect that matters:

- **Check whether `markers_only: True` injects boundary-marker strings into `Unit.text`.**
- **If it does not inject:** use `markers_only: True`. One line, and the arm's behaviour is
  visible in its declared parameters, which is worth more than the alternative's tidiness.
- **If it does inject:** use the none-provider context. SEAM declares `boundary_markers: False`
  and must not carry markers into indexed text — that would be a second, larger text difference
  against UNCUT, and it would contaminate `D_seam` far worse than whitespace does.

Whichever you choose: **re-run the G6 test under the exact final SEAM configuration.** You ran it
on the rule-based path deliberately, and separating the questions was the right instinct, but the
gate has to pass on the arm that actually runs.

---

## New gate items

### G9 — does the LLM do the segmenting, or only the editing?

You noted in passing that FULL's prompts do not depend on `soft_target_tokens`, so `F384` and
`F768` share C3's cache entries. That is not a small note. It implies **right-sizing is
deterministic and applied after the LLM stage, and the LLM's only role is reference-resolution
and dedup.**

If that holds, SEAM and FULL share a segmentation engine and differ only in their input text —
which is exactly what makes `D_edit` a clean contrast rather than a confound between editing and
two different segmenters. It is currently the load-bearing assumption of the decomposition and it
is unverified.

**Verify it from the code path** — where `soft_target_tokens` is consumed relative to the
`complete()` call — and label it `VERIFIED` or `HYPOTHESIS` per A1g. If it turns out the LLM
*does* influence segment boundaries, tell me before writing the plan; the decomposition needs a
fourth arm and I would rather redesign than caveat.

### G10 — is SEAM already published as C3-markeronly?

`C3-markeronly` scored **0.7955** at **90 units** on Track A/MiniLM, against C0 at 0.7841 and C3
at 0.8182. Ninety units, not C3-nosize's 1552 — so right-sizing appears to be active under
`markeronly`. If `markers_only: True` is also how we reach the deterministic path, then **the
SEAM arm may be behaviourally identical to an already-published condition, modulo whether markers
enter the text.**

Determine whether it is. This matters for two reasons, in increasing order of importance:

1. If they coincide, most of the primary cell is a re-run of something already measured — cheap,
   and a free reproduction check.
2. **It would mean the published table already contains an approximate decomposition at 768
   under recall@5**, with seam-only sitting roughly a point above naive and the full pass roughly
   two points above seam-only. Both small. That is the direction P3 and P4 predict.

Which raises an integrity point I want handled explicitly rather than quietly: **a prediction
informed by a published number must say so.** Add a `prior_knowledge_at_freeze` field to
`preregistration_v16.json` recording exactly what was known about C3-markeronly, C0 and C3 at
freeze time, and stating that P3 and P4 were formed with those values in view. The predictions
themselves stand unchanged — they were written before Gate 0 and the handover already quoted the
0.7955 in its §2 table — but the record should not let a reader infer they were formed blind.
Sealing a prediction is only worth something if what informed it is also on the record.

Published values are **motivation and disclosure only**. They are not comparators, they do not
enter any arm, and no v1.6 number is computed from them.

---

## Amendments to `Handover_v16_SegmentSize.md`

Carry these into `Experiment_Plan_v1.6_SegmentSize.md`; the plan supersedes the handover
wherever they differ.

| § | Amendment |
|---|---|
| §3 | Add **G9** and **G10**. Record G2 as *not recoverable*; halt condition 7 applies and the U768 arm stands in — that is now a design fact, not a contingency |
| §4 SEAM | Add the deterministic-path mechanism chosen under G7, with the injection check recorded |
| §4 | Add control family **UNCUT-ws**, and the revised `D_ws` / `D_seam` definitions |
| §4 | `D_total = D_size + D_ws + D_seam + D_edit` |
| §6 | Add the gold-span-overlap assertion |
| §8 | Predictions unchanged. Add `prior_knowledge_at_freeze` per G10 |
| §10.1 | Replaced by the three-part G6 above |
| §10.3 | **Reworded.** You are right that the identity telescopes by construction. Keep the assertion — it catches a mis-wired arm or a transposed variable — but describe it as a **wiring check, not a validity check**, so that nobody downstream cites it as evidence the decomposition is sound. It is evidence that the same point estimates were used in both places, and nothing more |
| §10.5 | Retained, and should now be unreachable on Track A. If it fires anyway, that is a finding about the deterministic path, not a budgeting problem |
| §15 | Narrowed to a change in a **token, identifier or number** |

Everything else in the handover stands: no writes to `results/`, PW-1 untouched and its
conclusion not revisited, arms defined inline rather than in `config/conditions/`,
`recall@budget(1920)` primary with recall@5 secondary, S2 primary with S3 cross-check, the Holm
families as enumerated, the one-shot rule, and the freeze-before-first-arm-value ordering with
the interval recorded.

---

## The four files in `86dfa07`

Those are mine — `Semantic_Formatter_WhitePaper_v3.html/pdf` and
`Semantic_Formatter_Brief_v2.html/pdf` were written into the working directory deliberately and
belong in the repo. **Keep the commit; do not revert.** No harm done.

You are still right about the discipline, and I would rather you flagged it than not. Stage
selectively from here — in a programme where "which commit was this computed under" is load-
bearing, a commit containing files the committer cannot account for is a small hole in exactly
the thing the commit exists to establish. Nothing turns on it this time because the four files
are accounted for now.

## On v3 and the PW-1 §7 hand-off list

Go ahead and open `Semantic_Formatter_WhitePaper_v3.pdf` and the brief. Yes — v3 incorporates the
PW-1 corrections, including the family-1 NOT SEPARATED result, so your suspicion is right and the
§7 hand-off list in `Results_PW1_ProvenanceWidth.md` is at least partly stale.

**Record the reconciliation in a new note; do not edit `Results_PW1_ProvenanceWidth.md`.** The
distinction I want held: PW-1's *results* are closed and untouchable, and its §7 list is a
to-do list rather than a result — but the cost of getting that boundary wrong is much higher than
the cost of an extra file. A new note loses nothing.

This is a side task. It does not block v1.6 and it does not go into the v1.6 record.

---

## Order from here

1. G7's injection check → fix the SEAM arm definition.
2. G9 and G10.
3. Re-run the G6 test, in its weakened three-part form, under the final SEAM configuration; add
   the gold-span assertion.
4. **If G9 comes back `HYPOTHESIS` or contradicts the assumption — stop and tell me.** Otherwise
   continue.
5. Write the plan and `preregistration_v16.json`, with `prior_knowledge_at_freeze` populated.
6. Commit them. Record hash and UTC timestamp.
7. Then the script, then the primary cell.
