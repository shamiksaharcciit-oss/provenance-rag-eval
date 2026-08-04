# v1.6 — rulings on Gate 0 round 2: the G9 falsification and the fourth arm

**Responds to:** Gate 0 round 2 @ `4851f58`
**Date:** 31 July 2026
**Status:** decisions. Still no plan, no pre-registration, no script, no arm value.

You were told to stop if G9 came back contradicted. It did, you did, and the stop was
correct — but the damage is smaller and more interesting than it looks, and it is contained
to exactly one term. This document rules on all four findings, adds the fourth arm, and
restates the decomposition. Work resumes at §7 below.

---

## G7 — accepted. Plus one side effect that must go in the plan.

`markers_only: True` injects nothing; `boundary_markers` is never read on that path. First
branch of the ruling applies, SEAM is deterministic, and G6 re-runs under that configuration.

**The side effect is not incidental and must be recorded as a finding, not a footnote.**
Line 243 forces right-sizing even when `right_size: False`. That means a declared parameter
is silently overridden on a path where somebody could reasonably expect it to be honoured.
Two consequences:

1. **It explains the published table.** `C3-markeronly` lands on 90 units rather than
   `C3-nosize`'s 1552 *because of line 243*, not because its declared parameters ask for
   right-sizing. Anyone reading `C3-markeronly.yaml` alone would predict the wrong unit count.
2. **It is a trap for the next arm anyone declares.** Record it in the plan under Gate 0 with
   file and line, in the form *"on the `markers_only` path, `right_size` is not honoured;
   right-sizing always runs."* Do not fix it — same reasoning as `_emit`: this experiment
   measures the published formatter, not a repaired one.

---

## G10 — accepted. `prior_knowledge_at_freeze` is now a substantial field, not a formality.

SEAM *is* `C3-markeronly`, reproduced at 90 units and `token_mean` 609.84. So the entire
768 row of this design is already on the published record:

| Arm | Published as | recall@5 |
|---|---|---|
| `U768` | C0 | 0.7841 |
| `S768` | C3-markeronly | 0.7955 |
| `F768` | C3 | 0.8182 |

Seam ≈ **+0.011**, edit ≈ **+0.023**. Both small, both in P3/P4's direction.

**Record all three values, both differences, and the fact that P3 and P4 were formed with
them in view.** Do not paraphrase this as "some published values were known." Name the
conditions, quote the numbers, state the arithmetic. A sealed prediction whose informing
knowledge is not itself sealed is worth very little, and the cost of over-disclosing here is
zero.

**One consequence you should state plainly in the plan, because it changes what the
experiment is for.** Under `recall@5` at 768, this experiment is a reproduction check — the
answer is already published. The genuinely new information is in three places and nowhere
else: the `recall@budget(1920)` metric, the sizes other than 768, and the fourth arm added
below. Say that in §0 of the plan. It is a strength — a design whose known row reproduces is
a design you can trust on its unknown rows — but only if it is declared rather than
discovered by a reader.

**Reproduction is void across embedders.** These are `all-MiniLM-L6-v2` numbers. If the
primary cell runs MiniLM the reproduction check is live; if any cell runs bge, absolute
levels are not comparable (Template §B) and no reproduction claim may be made from it. State
which, explicitly, next to the check.

---

## G2 — accepted, with a tightening and a standing correction

Recovering the overlap from a conservation identity rather than a stored field is good work,
and the inference is sound: overlap > 0 double-indexes overlapped text, so a ratio of 1.0000
excludes it.

**Tighten it before it goes in the plan.** You computed the published side as
90 × 609.84 = 54,886. That is a rounded mean multiplied by a count, and it reproduces the raw
total only to the precision of the printed mean (90 × 609.84 = 54,885.6). Under A1f, redo it
from **integer token counts summed over units**, and report the identity as an exact integer
comparison or as an explicit residual. State the assumptions the inference rests on: one
tokenizer (`count_tokens`) on both sides, and no other mechanism in the pipeline that could
add or drop text and coincidentally restore the ratio. Then label it `VERIFIED`.

**Run your own `U768` anyway — and the reason is stronger than "nearly free."** A
decomposition whose base term is imported from a different run, under a different
environment, is not a decomposition; it is a comparison across two records. `D_size(m) =
U(m) − U256` requires every U term to come from this run, on this split, under this pinned
stack. The published C0 is now a **reproduction target**, not a comparator, and that is how
the plan must describe it.

**Halt condition 7 does not fire.** Amend it to: *published C0 is established as `U768`
(overlap 0.0) by the G2 conservation check; it is used as a reproduction target only, and
every decomposition term is computed from arms run in this experiment.*

**The process finding is real and I want it recorded.** A swept parameter went unpersisted
and survived only because the metric happened to admit a conservation check. That is luck,
and the next unpersisted parameter may not be so obliging. Record it in the plan as a
process finding, and write the candidate rule now — *"every parameter a sweep selects is
persisted in the run manifest, alongside the value it beat"* — but **do not amend
`Amendment_Criteria_Template.md` mid-experiment.** Governing documents do not change while an
experiment that cites them is in flight. It goes to the template after v1.6 closes, and it is
my call to make then, not a side effect of this run.

---

## G9 — the ruling. `D_edit` is not invalid. It is mislabelled.

Your finding: `complete()` at 345, `_place_boundaries` at 385, `_right_size` pure arithmetic —
so the LLM does not choose boundaries. But `_right_size` groups by `count_tokens(st.text)`
over `st.kept`, and the LLM sets both. 0/45 Track A documents share boundaries between
SEAM(768) and FULL(768); `A-000-kestrel-indexer` moves its interior boundary 283 characters.

That is a clean falsification of the claim as I stated it, and the label `HYPOTHESIS →
FALSIFIED` is right. But read what it actually falsifies.

**It does not falsify `D_edit` as a measurement.** It falsifies my description of `D_edit` as
*"editing, holding seams and size."* The boundary shift is not an outside variable
contaminating the contrast — it is, as you say, a **downstream consequence of the treatment.**
Editing the text is what causes the cuts to move. A quantity that includes the consequences of
the treatment is not confounded; it is the **total effect of the treatment as deployed**, and
it is the quantity a reader who is deciding whether to switch the formatter on actually needs.

So:

- **`D_edit = F(m) − S(m)` stands, unchanged, as the decision-bearing quantity**, and the
  decision rules in §9 of the handover are unaltered. It is relabelled **"the total effect of
  enabling the editing pass, including the boundary shift the editing induces."**
- The question your finding opens is a **different** one, and a secondary one: *of that total,
  how much comes from the text being better, and how much from the cuts landing elsewhere?*
  That is a mechanism question. It needs the fourth arm.

Two things follow that I want stated in the plan in these words, because both will otherwise
be got wrong downstream. First: **`D_size` and `D_seam` are untouched by this finding.** Both
run on unedited text, both take the deterministic segmenter's output on an identical sentence
list; nothing in G9 reaches them. The damage is contained to one term. Second: **the mechanism
split cannot rescue a null.** If `D_edit` comes out indistinguishable from zero, the branch is
KILL and the decomposition of a null into two components is not a finding — it is arithmetic
on noise. Freeze that now, before we know, because after the fact it will be tempting.

---

## The fourth arm: `F@S` — edited text, SEAM's boundaries

You framed the choice exactly right: you cannot edit the text and hold the cuts fixed without
privileging one arm, and choosing is a design decision. Here is the choice, and the reasoning,
so that it is on the record as a decision and not a preference.

**Ruling: build `F@S(m)` — FULL's edited sentence list, grouped at SEAM's boundaries.** Do not
make `S@F` the pre-registered arm. Three reasons, in increasing order of weight:

1. **It is the conservative direction.** `F@S` denies the edited text the boundaries the
   right-sizer would have chosen for it. If right-sizing helps at all, this handicaps the
   treatment arm. A positive `F@S − S` therefore reads as *editing helps even when it is
   denied its preferred seams* — a claim that survives its own worst case.
2. **It does not leak the treatment into a control.** `S@F` would hand unedited text a set of
   boundaries computed with knowledge of the edit — where the deduplicated, reference-resolved
   text wanted to split. That is treatment-derived information inside a control arm. It would
   inflate the apparent boundary effect and deflate whatever residual is left to attribute to
   the text, which is the direction that flatters the thesis. Arms that flatter the thesis by
   construction do not go in the primary family.
3. **It is the quantity that answers the question we are asking.** "Is it the text?" is a
   direct-effect question: apply the treatment's text, hold the mediator at its control value.
   That is `F@S`. `S@F` holds the text at control and moves the mediator — a different
   estimand, and not the one in §0 of the handover.

### Construction

```
F@S(m):  take FULL(m)'s kept sentences, each with its source_ranges in original coordinates.
         Assign each sentence to the SEAM(m) segment containing the start of its first
         source range. Concatenate in order within each segment, using the same _emit path
         FULL uses. A unit's source_ranges are the union of its sentences' ranges — the same
         rule FULL applies, so the scorer sees nothing new in kind.
```

Verify, do not assume: that assignment rule needs `_emit` and the sentence→ranges mapping to
behave as I have described. **If the code does not support it as written, stop and tell me
what it does support** rather than substituting a rule of your own — the assignment rule *is*
the arm definition, and a different rule is a different experiment.

### Gates on the new arm

- **Regrouping gate.** `F@S(m)`'s concatenated text must equal `F(m)`'s concatenated text
  under whitespace normalisation, per document. The transplant is a pure re-grouping: no
  sentence gained, none lost, order preserved. This is the `F@S` analogue of G6 and it is
  decisive — it fails if the assignment rule drops or duplicates anything. Halt on failure.
- **Segment-count report.** `F@S(m)` should have SEAM(m)'s segment count. Dedup can empty a
  segment. If any segment is empty, **report the count and the documents affected; do not
  force, pad, or merge.** An empty segment is data about what dedup removed, and suppressing
  it would hide the one thing that makes the two arms differ.
- **S2 ≡ S3 does not hold here.** `F@S` inherits FULL's dedup and therefore has absorbed
  ranges. Halt condition 2 applies to the no-dedup arms only — UNCUT, UNCUT-ws, SEAM. State
  that explicitly; as written it would fire spuriously on `F@S`.

### `S@F` — permitted, bounded, secondary

You may build `S@F` as a **declared secondary** on one condition, stated in the
pre-registration before any value: its only reported use is the **magnitude of the interaction**
between text and boundary placement. It is never reported as an alternative estimate of the
editing effect, it never enters a decision rule, and if it disagrees with the `F@S` path that
disagreement is reported *as the interaction*, which is what it is. If that constraint feels
like it needs relaxing once you see the numbers, the answer is no — that is precisely the
moment the constraint exists for. If you would rather not carry it, drop `S@F` entirely; it
costs the experiment nothing.

---

## The revised decomposition

At matched nominal size `m` ∈ {384, 768}:

```
D_size(m)   = U(m)    − U256        cutting geometry alone, no editing
D_ws(m)     = U(m)-ws − U(m)        the _emit whitespace artifact (upper bound)
D_seam(m)   = S(m)    − U(m)-ws     seam placement, whitespace-matched, no editing
D_edit(m)   = F(m)    − S(m)        TOTAL effect of enabling editing, boundary shift included
D_total(m)  = F(m)    − U256

and, splitting the treatment term:

D_text(m)   = F@S(m)  − S(m)        editing's effect at SEAM's seams  (direct)
D_reseam(m) = F(m)    − F@S(m)      the boundary shift editing induces (indirect)
D_edit(m)   = D_text(m) + D_reseam(m)
```

Both identities — the outer one and the split — telescope by construction. Assert them to
exact equality on the point estimates and describe them, per the round-1 ruling, as **wiring
checks, not validity checks.** They catch a transposed variable. They are not evidence that
the decomposition means anything.

### Holm families — revised

- `F_EDIT` = { `D_edit(384)`, `D_edit(768)` } in cell A-MiniLM — **decision-bearing**, unchanged.
- `F_MECH` = { `D_text(384)`, `D_text(768)`, `D_reseam(384)`, `D_reseam(768)` } in cell
  A-MiniLM — **new family**, corrected within itself, **not decision-bearing**.
- `F_CONFOUND` = { `D_size`, `D_ws`, `D_seam` at both sizes } — reported, corrected within
  itself, not decision-bearing.
- `S@F`, if built, is in **no** family and carries no p-value that anyone acts on.

---

## New predictions — seal with the rest, before any value

P1–P5 stand as written. Add:

| ID | Prediction | Falsified if |
|---|---|---|
| P6 | `D_reseam(768)` is **small and non-negative** under `recall@budget` — denying FULL its own seams costs it a little or nothing | it is significantly negative, or exceeds `D_text` in magnitude |
| P7 | `D_text(768)` carries **the majority** of `D_edit(768)` under `recall@budget`, conditional on `D_edit(768)` being distinguishable from zero | `D_text` is less than half of `D_edit`, or is itself indistinguishable from zero while `D_edit` is not |

P6 and P7 are formed **blind** — no published number decomposes the editing effect, and
`prior_knowledge_at_freeze` must say so, distinguishing them from P3 and P4, which are not
blind. That distinction is the reason the field exists.

**P7 is the uncomfortable one now, and it is deliberately uncomfortable.** If `D_edit` is
positive and `D_text` is not — if the whole of the editing benefit turns out to sit in
`D_reseam` — then the honest statement is *"the editing pass helps, and it helps by changing
where the cuts fall rather than by improving the text."* That is a genuinely important result
and it is the opposite of what this programme has been claiming. **It is reported at the same
prominence a confirmation would receive**, under the same `reporting_rule` and
`harm_reporting_rule` already frozen in §9. Writing that down before the run is the only thing
that makes the prediction worth sealing.

---

## Amendments to the handover — carry into `Experiment_Plan_v1.6_SegmentSize.md`

| § | Amendment |
|---|---|
| §0 | Add: under recall@5 at 768 this design reproduces published values; the new information is `recall@budget`, the non-768 sizes, and `F@S` |
| §3 | G2 **recovered** (conservation identity, integer-tightened). G7 resolved, `markers_only: True`, plus the line-243 right-size override recorded as a Gate-0 finding. G9 **FALSIFIED**. G10 confirmed: SEAM ≡ C3-markeronly |
| §4 | Add arm family **`F@S`** with the assignment rule and its three gates; `S@F` optional secondary, interaction-only |
| §4 | `D_edit` relabelled **total effect including induced boundary shift**; add `D_text`, `D_reseam` and the split identity |
| §6 | S2 ≡ S3 assertion scoped to **no-dedup arms only** (UNCUT, UNCUT-ws, SEAM); `F@S` and FULL are excluded |
| §8 | Add P6, P7. `prior_knowledge_at_freeze` records the three published 768 values, both differences, that P3/P4 saw them, and that P6/P7 are blind |
| §9 | Decision rules unchanged — `D_edit` remains the treatment. Add `F_MECH` to the families. Add: **a null `D_edit` is not decomposed**; KILL is KILL |
| §10.2 | Scoped to no-dedup arms |
| §10.3 | Add the split identity; still a wiring check |
| §10.7 | Rewritten — published C0 established as `U768`; reproduction target, not comparator; all decomposition terms from this run |
| §10 | New: **halt if the `F@S` regrouping gate fails**, or if the sentence→segment assignment rule is not constructible as specified |
| §13 | Add `tests/test_v16_fas_regrouping.py`; `F@S` arms in the sweep script |

Everything else stands: no writes to `results/`, PW-1 untouched and its conclusion not
revisited, arms inline rather than in `config/conditions/`, `recall@budget(1920)` primary with
recall@5 secondary, S2 primary with S3 cross-check, the one-shot rule, and the
freeze-before-first-arm-value ordering with the interval recorded.

---

## On stopping

Three of the four round-2 findings contradicted something I wrote, and one of them killed the
stated basis of the decision-bearing quantity. You found that, labelled it against A1g, and
stopped at the step where stopping was expensive rather than at the step where it was cheap.
That is the behaviour the gate structure exists to produce, and it has now paid for itself
twice. Keep doing it — including on this document.

---

## Order from here

1. Build `F@S(m)` per the assignment rule; **stop and report if the code does not support it
   as specified.**
2. Write the `F@S` regrouping gate and run it. Report the segment-count and empty-segment
   findings whichever way they fall.
3. Re-run the weakened three-part G6 under the final `markers_only: True` SEAM configuration,
   with the gold-span-overlap assertion.
4. Tighten the G2 conservation check to integer token counts; label `VERIFIED`.
5. Write `Experiment_Plan_v1.6_SegmentSize.md` and `preregistration_v16.json`, with
   `prior_knowledge_at_freeze` fully populated per G10 and P6/P7 marked blind.
6. Commit both. Record the hash and the UTC timestamp.
7. Then `scripts/segment_size_sweep.py`, then the primary cell.

No further gate stop is anticipated. If one is warranted anyway, take it.
