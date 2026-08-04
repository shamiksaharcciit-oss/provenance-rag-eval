# v1.9 READING-RESIDUAL — results

**Pre-registration:** `Plan_v19_ReadingResidual_2026-08-01.md`, frozen at
**`5bc4aebea635fdc10d83c349d2a37486d1f337bf`** @ 2026-08-01T14:07:10Z, pre-freeze amendments
PF-G1…PF-G4 in its §0.
**Rulings applied:** `Decisions_v19_Gate0_2026-08-01.md`, `Decisions_v19_ProbeCheckpoint_2026-08-01.md`.
**Generator:** `claude-sonnet-5`, pinned from the plan and asserted against `response.model` on
every call; constant across the whole run.
**Cells:** Track A (n=176), Track B (n=150, **quarantined** — see §1).
**Branch:** targeted repeats — 3× generation with per-query median for **Track A `F768`/`U768`
only**; everything else single-run and carrying the mandatory variance caveat.

---

## 1. PR-0 — the control, scored first

> **PR-0 (control, both tracks):** F1(correct) exceeds F1(mismatched) decisively — mismatched
> median F1 < 0.2 **and** correct − mismatched median gap > 0.3, per track.

30 queries per track, each generated once with its correct `F768` package and once with query
*i*+1's package (successor with wraparound, sample drawn at seed 1337 and frozen at Gate 0).

| track | median F1 correct | median F1 mismatched | gap | criterion | verdict |
|---|---|---|---|---|---|
| **A** | 0.530 | **0.000** | **0.530** | both clauses met | **PASS** |
| **B** | 0.166 | 0.006 | **0.160** | gap clause fails | **FAIL — QUARANTINED** |

**Not an APPARATUS-STOP:** that requires both tracks to fail. Track A carries the experiment.

**Track B is quarantined track-level, exactly as frozen:** no prediction is scored on it, and no
contrast from it appears outside the flagged descriptive table in §6. **PR-4 is contingent on
PR-0(B) and is therefore not scored at all** — not scored-and-failed.

**How Track B failed matters and is recorded, not interpreted.** Its mismatched median is
**0.006** — the generator is demonstrably *not* answering from parametric memory, which is the
risk PR-0 was written to catch. It fails the **gap** clause because correct-package F1 is itself
only 0.166. The control fired for a reason other than the one it exists to detect. No mechanism
is claimed from that here.

## 2. PR-1 — `F_READ2`, the single tested member, Track A

> **PR-1 (Track A, `F_READ2`):** mean token-F1(`F768`) − mean token-F1(`U768`) > 0.

| | mean token-F1 |
|---|---|
| `F768` | **0.601162** |
| `U768` | **0.490581** |
| `U256` (descriptive third) | 0.486828 |

**`F_READ2` = +0.110581**, CI95 **[+0.066042, +0.156719]**, permutation **p = 0.0001**. Holm over
one member is the identity, stated as such.

**PR-1 is positive at p < 0.05. CONFIRMED.**

**Per-query direction counts, descriptive:** `F768` higher **70**, `U768` higher **58**, tied
**48**. The net mean difference rests on a 12-query direction margin with 48 ties; both readings
are reported and neither is tested on.

## 3. PR-2 — exact containment, descriptive

> **PR-2 (Track A, descriptive):** exact-containment count higher for `F768` packages.

| | `F768` | `U768` | `U256` |
|---|---|---|---|
| exact containment | **30** | **34** | 32 |
| `NOT FOUND` | **1** | **15** | 14 |

**PR-2 FAILS.** Containment is *lower* for `F768` (30) than `U768` (34), while token-F1 runs the
other way. The two objective measures disagree in direction on the same arms and the same
answers. Reported as the split it is; no aggregate reconciles them and no test is computed.

The `NOT FOUND` column is recorded beside it because it is the largest single asymmetry in the
run — `F768` abstained once, `U768` fifteen times — and a reader comparing §2 to §3 is entitled
to see it. No attribution is offered.

## 4. PR-3 — judge, descriptive

> **PR-3 (Track A, descriptive):** judge direction agrees with F1's on the primary contrast;
> judge favouring `F768` while F1 does not is the fluency-bias signature, not support.

**Not run.** The judge stage was scoped in §3 as a descriptive secondary on the Track A primary
pair; the judge determinism probe (§5) returned NONDETERMINISTIC, which under the frozen G3
fallback requires 3× judge calls on that pair. **The judge comparison was not executed in this
run**, so PR-3 has no evidence and is **NOT SCORED**. This is a gap against the frozen plan and is
recorded as such rather than presented as a null: the plan asked for it, and it is absent.

## 5. Determinism probes

Both under the ported G2 protocol: repeats bypass the response cache entirely, and the harness
asserts fresh-call count = prompts × repeats.

| probe | prompts × repeats | fresh calls | identical | verdict |
|---|---|---|---|---|
| generator | 20 × 3 | **60/60** | 6/20 | **NONDETERMINISTIC** |
| judge | 20 × 3 | **60/60** | 15/20 | **NONDETERMINISTIC** |

Both on Track A dev only; the verdict extends to Track B as the declared sampler-property
assumption (G6), not as a measurement there. All finish reasons `end_turn`; no truncation or
length anomaly. Probe spend 120 of the 500-call bound.

**A voided third probe.** The first generator probe ran on **`claude-opus-4-8`**, not the plan's
`claude-sonnet-5`: the runner resolved the model from configuration, the repo default is Opus 4.8,
and Track A declares no override. G5's `response.model` pin caught it. Its record is preserved as
`probe_VOID_wrong_model.json` with its 60 billed calls; **$0.75 is recorded as waste.** The
generator is now pinned from the plan and asserted at construction and against `response.model` on
every call.

## 6. Track B — flagged descriptive table, quarantined, not evidence about reading

| | `F768` | `U768` | `U256` |
|---|---|---|---|
| mean token-F1 | 0.139737 | 0.140094 | 0.142383 |
| `F768 − U768` | **−0.000357**, CI [−0.0307, +0.0292], p 0.9817 | | |
| direction counts | 33 / 32 / **85 tied** | | |
| exact containment | 0 | 0 | 0 |
| `NOT FOUND` | 67 | 60 | 60 |

**Quarantined by PR-0(B). No prediction is scored on this track and nothing here is evidence about
reading.** Zero exact containments across all three arms and 60–67 abstentions of 150 are recorded
as run facts.

## 7. The six imbalanced pairs, printed raw

Every Track A package short of B2(q), one row each, **cause recorded**. No aggregate is taken over
them and no second test is computed on `F_READ2` — A5b holds because no quantity acquires a second
procedure.

| query | B2(q) | `F768` tokens | `U768` tokens | F1 `F768` | F1 `U768` | difference | cause |
|---|---|---|---|---|---|---|---|
| `A-036-halcyon-cache::f4` | 1111 | 1058 | 1111 | 0.6364 | 0.2353 | **+0.4011** | document_exhausted |
| `A-012-ridge-indexer::f4` | 1152 | 1124 | 1152 | 0.6286 | 0.2222 | **+0.4063** | document_exhausted |
| `A-000-kestrel-indexer::f4` | 1105 | 1058 | 1105 | 0.6286 | 0.2222 | **+0.4063** | document_exhausted |
| `A-023-harbor-sharder::f4` | 1346 | 1300 | 1346 | 0.6286 | 0.2222 | **+0.4063** | document_exhausted |
| `A-008-quartz-resolver::f4` | 1444 | 1368 | 1444 | 0.5161 | 0.1818 | **+0.3343** | document_exhausted |
| `A-019-crag-broker::f4` | 1247 | 1199 | 1247 | 0.5455 | 0.6250 | **−0.0795** | document_exhausted |

Six of 176 queries, 3.4% of the track. **Document exhaustion is the only cause recorded, which is
the only cause permitted**; a shortfall with units left unused would have raised
`ShortfallCauseUnknown`. Per the Gate 0 ruling the direction of this imbalance is **UNKNOWN, not
conservative**: five pairs run strongly in `F768`'s favour and one against, and the reader has the
rows.

## 8. `T_a(q)` — gold-delivery cost, declared descriptive companion

Tokens each arm needs to cover the gold. Values and attribution only; no test.

| track | `F768` min/median/max | `U768` min/median/max | `U256` min/median/max |
|---|---|---|---|
| A | 272 / **762** / 768 | 332 / **768** / **1444** | 128 / 256 / 768 |
| B | 531 / 765 / 3820 | 400 / 768 / 3840 | 256 / 512 / 3584 |

**Budget escalation, with attribution:** Track A **6/176**, set by `U768` in all six. Track B
**65/150**, set by `U768` 54, `F768` 11, `U256` 2. On Track A, `F768` never exceeds 768 tokens to
deliver the gold while `U768` reaches 1444 — the compactness fact in the units this experiment
measures.

## 9. Costs, actual against projected

| stage | calls | est_usd |
|---|---|---|
| generator probe (void, wrong model) | 60 | 0.7533 |
| generator probe (valid) | 60 | 0.7767 |
| judge probe | 60 | 0.1701 |
| PR-0 control, both tracks | 120 | 1.5147 |
| main, Track A | 1232 | 15.4811 |
| main, Track B | 450 | 6.2220 |
| **total** | **1982** | **≈ 24.92** |

Projected at freeze: 1,334 single-run / 2,390 targeted repeats, ceiling 5,000. **Actual 1,982
calls — under both the selected branch's projection and the ceiling.** The guard's `max_usd` 60.0
was never approached and **was never edited**. The judge stage's absence (§4) accounts for part of
the gap to 2,390.

## 10. Limitations

- **Nothing here is blind.** Two prior kills and this programme's motive to find a surviving
  channel were known before the predictions were written. Every prediction is HYPOTHESIS under
  A1g.
- **Contamination of priors, not of design.** Per `Decisions_v18_Gate1_2026-08-01.md` §2, the
  v1.8 outcome that section governs became known **after** this plan was frozen at `5bc4aeb`. The
  design predates that number; the priors do not. §2 is cited here as the frozen plan requires,
  and nothing further about it is stated — attribution belongs to the ruling, not to this report.
- **PR-3 was not executed** (§4). The judge secondary is missing from a run whose plan declared
  it. Recorded as a gap, not a null.
- **PR-2 fails while PR-1 confirms** (§3). Two objective measures disagree in direction; this
  document reports both and reconciles neither.
- **Single judge** was the declared design risk for PR-3; it is moot here since PR-3 did not run.
- **The Track B parametric-knowledge risk PR-0 exists to catch did not materialise** — mismatched
  median 0.006. Track B is quarantined for a different reason (§1).
- **Six pairs carry a token imbalance of unknown sign**, bounded at 3.4% of the track, disclosed
  per pair in §7.
- **Non-repeated arms carry unquantified variance.** The generator is nondeterministic; only Track
  A `F768`/`U768` were repeated. Every other number in this document is a single sample.
- **`P`-arm-style lexical neutrality does not apply here**; this experiment has no padding arm.

## 11. What this document does not do

No interpretation beyond the scoring lines above. No E3 work, no internal-report drafting, no
packaging or sequencing recommendation — §5 of the frozen plan holds report language for **when
Shamik commissions that document**, and this is not that document. No external claim. No closed
verdict revisited. Nothing under `v17/`, `v18/` or `v110/` modified.

## 12. PR-3 — judge secondary. EXECUTED POST-STOP BY RULING

**Executed after the Gate 1 STOP, by order of `Decisions_v19_Gate1_2026-08-02.md` §4 as amended
by `Decisions_v19_PR3_2026-08-02.md` §3.** §4's order was outcome-independent and would have
issued identically had PR-1 failed.

### 12.1 The answer set is DISJOINT from PR-1's draws

The main run persisted only each arm's median F1 and rep 0's text, discarding the other two
repetitions' text. That **persistence defect** made rep-pairing by index impossible from the
record, so this supplement **regenerated** Track A `F768`/`U768` at 3 reps per arm, persisting
every rep's text (1,056 calls), then judged each rep-pair once by index (528 calls).

**PR-1 is untouched and was not re-scored.** Its +0.110581 stands exactly as scored in §2. The F1
values below exist **solely as PR-3's reference**, because the sealed agreement comparison must
run on identical answers and these are new draws.

**Reproduction observation across independent draws, descriptive.** Supplement mean token-F1:
`F768` 0.594546, `U768` 0.476653, difference **+0.117893**, against PR-1's **+0.110581** — a gap
of +0.007312. The generator is nondeterministic (§5), so the frozen expectation was that this
would not be exactly zero, and it is not. No test is computed on it and it revises nothing.

### 12.2 PR-3 scored as sealed

> **PR-3 (Track A, descriptive):** judge direction agrees with F1's on the primary contrast;
> judge favouring `F768` while F1 does not is the fluency-bias signature, not support.

Per-query judge direction = median of the three pairwise verdicts. Blinded to arm, candidate
order randomised per call, frozen prompt, model asserted against `response.model` on all 1,584
calls (constant `claude-sonnet-5`, all finish reasons `end_turn`).

| judge ↓ / F1 → | `F768` | `U768` | TIE |
|---|---|---|---|
| **`F768`** | **17** | 3 | 0 |
| **`U768`** | 1 | **7** | 0 |
| **TIE** | 50 | 48 | **50** |

| reading | value |
|---|---|
| judge direction counts | `F768` **20**, `U768` **8**, TIE **148** |
| overall agreement (diagonal) | **74/176 = 42.0%** |
| agreement where **both** express a direction | **24/28 = 85.7%** |
| **bias signature** (judge favours `F768`, F1 does not) | **3/176** |

**Both readings are reported and neither is presented as the headline.** The overall 42% is
dominated by the judge returning TIE on **148 of 176** queries — it declined to distinguish the
arms far more often than it chose between them. Restricted to the 28 queries where both
instruments express a direction, they agree 24 times.

**PR-3 HOLDS in the conditional reading and is uninformative in the raw one**, and the difference
between those two sentences is the judge's tie rate, not the formatter. The bias signature is
**3 of 176** — the pre-declared fluency-bias pattern is present but small on this answer set.

Descriptive throughout. No test is computed on any quantity in this section.

---

**STOP at Gate 1 for the ruling.**
