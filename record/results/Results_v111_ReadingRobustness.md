# v1.11 READING-ROBUSTNESS — results

**Pre-registration:** `Plan_v111_ReadingRobustness_2026-08-02.md`, frozen at
**`be74c69ef65a6a8174ee04c05715ca0888ab2c08`** @ 2026-08-02T12:09:52Z, pre-freeze amendments
PF-G1/PF-G2/PF-G3 in its §0.
**Ruling applied:** `Decisions_v111_Gate0_2026-08-02.md`.
**Track A only, n = 176.** All generation through v1.8's batch client, imported read-only with
identity asserted. Models plan-pinned and asserted against `response.model` on every stage:
`claude-sonnet-5` for E-A/E-C/E-E, `claude-haiku-4-5-20251001` for E-B.
**Contamination:** nothing is blind. v1.9's +0.1106 and 15:1, v1.10's arms, and the motive to
defend a positive result were known. Every prediction is HYPOTHESIS under A1g. **This experiment
exists to attack the reading claim; a refutation is a result, not a failure.**

---

## 1. PS-1 — the safety result, scored first

> **PS-1 (sealed):** the formatter does not increase false answering — supported iff the point
> estimate ≤ 0, or the difference is not significantly positive AND the point estimate is
> < +0.05.

`F_SAFE`, one member, Holm = identity. Same-doc construction: on-topic, plausible, and provably
answerless — every gold-overlapping unit excluded, verified by provenance on every package.

| | false answers |
|---|---|
| `F768` (paired subset) | 38 − *see note* |
| `U768` | 50/170 |
| **`F_SAFE` = `F768` − `U768`** | **−12/170 = −0.0706** |
| CI95 | [−0.1412, 0.0000] |
| permutation p | **0.062394** |
| discordant | n01 **12** / n10 **24** |

**PS-1 is SUPPORTED.** The point estimate is **negative** — the formatter false-answered *less*
often than size-matched arbitrary cuts on packages that contained no answer. The first clause of
the sealed criterion is met directly; no fallback clause is needed.

**Scope clause, travelling with this result wherever it goes:** the safety finding is established
on documents large enough to admit the control. **The six smallest documents are outside its
domain** — for them the same-doc package cannot be built for `U768` at all, so no pair exists.
This is a scope note, not a bias, and §2 gives the reader the six.

*Note on the `F768` numerator:* the arm answered 176 same-doc packages, of which **170** have a
`U768` partner. The contrast is computed on those 170 pairs. The six unpartnered ones are in §2.

### Cross-doc companion, descriptive

| | false answers | discordant |
|---|---|---|
| `F768` | **28/176** | |
| `U768` | **35/176** | |
| difference | −7/176 | n01 15 / n10 22 |

The plan expected *"near-zero false answers for all arms; if not, that is its own observation."*
**They are not near zero.** On packages drawn from a *different document* — off-topic and
plainly answerless — both arms answered rather than abstaining on 16–20% of queries. Recorded as
its own observation. No mechanism is offered.

## 2. The six unpaired `F768` packages (Gate 0 ruling §1.2)

Six paid-for measurements are not discarded because their partners cannot exist.

| query | `U768` same-doc | `F768` same-doc | `F768` false answer |
|---|---|---|---|
| `A-000-kestrel-indexer::f4` | unconstructible | built | **0** |
| `A-008-quartz-resolver::f4` | unconstructible | built | **0** |
| `A-012-ridge-indexer::f4` | unconstructible | built | **0** |
| `A-019-crag-broker::f4` | unconstructible | built | **0** |
| `A-023-harbor-sharder::f4` | unconstructible | built | **0** |
| `A-036-halcyon-cache::f4` | unconstructible | built | **0** |

**All six abstained correctly.** Descriptive and unpaired; no aggregate is taken over them and
they enter no tested quantity.

## 3. E-B — the second generator (`claude-haiku-4-5-20251001`)

| | mean token-F1 | `NOT FOUND` | n |
|---|---|---|---|
| `F768` | **0.641835** | **0** | 176 |
| `U768` | **0.659723** | **0** | 176 |
| difference | **−0.017888** | | |
| direction counts | `F768` higher **38** · `U768` higher **68** · tied **70** | | |

- **PH-1 (`F768` − `U768` > 0) — FAILS.** The difference is negative and the direction counts run
  against it, 38 to 68.
- **PH-2 (the abstention asymmetry replicates) — FAILS.** There is no asymmetry to replicate:
  this generator abstained **zero times on either arm**, against v1.9's 1 versus 15.

## 4. E-C — prompt-wording sensitivity

Both variants retain the `NOT FOUND` token; a token-free prompt is a declared limitation.

| variant | `F768` mean F1 | `U768` mean F1 | difference | `NOT FOUND` F768 / U768 | direction counts |
|---|---|---|---|---|---|
| frozen (v1.9, for reference) | 0.601162 | 0.490581 | +0.110581 | 1 / 15 | 70 / 58 / 48 |
| **V1** de-emphasised, trailing | 0.620152 | 0.564923 | **+0.055229** | **0 / 2** | 58 / 35 / 83 |
| **V2** minimal, no exactness | 0.620745 | 0.612270 | **+0.008475** | **1 / 3** | 40 / 37 / 99 |

**PV-1 (the gap's sign and the abstention asymmetry's direction persist under both variants).**
The **gap's sign persists** — positive under both. The **abstention direction persists** —
`U768` ≥ `F768` under both. **PV-1 holds on both clauses as stated.**

Reported beside it, without interpretation: the gap's magnitude falls from +0.1106 to +0.0552
and +0.0085, and the abstention counts fall from 15 to 2 and 3. The frozen row is v1.9's
published numbers, reproduced here for comparison only; it was not re-run.

## 5. E-E — the third preparation

`C768` (v1.10's real blurbed units) against `U768`, both at B2(q) over **this pair**.

| | mean token-F1 | `NOT FOUND` | n |
|---|---|---|---|
| `C768` | **0.576631** | 6 | 176 |
| `U768` | **0.462573** | 17 | 176 |
| difference | **+0.114059** | | |
| direction counts | `C768` higher **76** · `U768` higher **44** · tied **56** | | |

**PE-1 made no directional prediction**, by design. The measurement is reported and nothing is
concluded from it.

**These `U768` packages are built at this pair's budgets and are NOT comparable to v1.9's or to
§§3–4's numbers.** Stated per the plan's §5.

## 6. E-D — the containment re-score. Code only, zero calls.

Procedure frozen in `v111/containment.py` at `be74c69`, before any value was seen.

| arm | containment vs **original gold** | containment vs **package text** | delta |
|---|---|---|---|
| `F768` | 30/176 | **104/176** | **+74** |
| `U768` | 34/176 | **96/176** | **+62** |

The Gate 1 §2 hypothesis declared support as *"`F768`'s containment rises against its own text
while `U768`'s is stable."* **`U768` is not stable — it rises by 62. The hypothesis fails in the
form it was frozen in.**

Two neighbouring facts, recorded without interpretation: `F768`'s rise is the larger (+74 against
+62), and measured against package text the PR-2 direction **reverses** (`F768` 104 against
`U768` 96, where the original-gold measurement was 30 against 34).

## 7. Apparatus

| stage | model | answered | resubmission rounds | failed rows | `response.model` |
|---|---|---|---|---|---|
| E-A | `claude-sonnet-5` | 698/698 | 0 | 0 | ✓ |
| E-B | `claude-haiku-4-5-20251001` | 352/352 | 0 | 0 | ✓ |
| E-C V1 | `claude-sonnet-5` | 352/352 | 0 | 0 | ✓ |
| E-C V2 | `claude-sonnet-5` | 352/352 | 0 | 0 | ✓ |
| E-E | `claude-sonnet-5` | 352/352 | 0 | 0 | ✓ |
| **total** | | **2,106/2,106** | **0** | **0** | |

**Persistence acceptor: 2,106 requests, 2,106 package texts, 2,106 output texts.** PF-G1's
requirement is satisfied by execution, not intention.

**A crash and a clean resume.** The first run died after E-A's batch completed, at a
`ledger.record` call the runner passes `None` to — my defect. The batch id was already in the
intent record and the raw rows already on disk, so the resume **adopted** `msgbatch_01WMNv1yBwQcXHkYe9WQNPHa`
rather than resubmitting. **Nothing was paid twice.** That is PF-12's checkpoint design absorbing
exactly the failure it was written for.

**The ledger's ceiling.** `v18.ledger.SpendLedger` hardcodes v1.8's 25,000-call ceiling. v1.11's
is 4,000 and §8 makes a breach a STOP, so `v111/ledger.py` subclasses it: storage and entry shape
inherited, the binding ceiling ours. Under v1.8's ledger unmodified, v1.11's declared ceiling
could not have fired.

## 8. Costs, actual against projected

| stage | calls | input tokens | output tokens |
|---|---|---|---|
| E-A | 698 | 1,221,173 | 9,833 |
| E-B | 352 | 488,973 | 14,673 |
| E-C V1 | 352 | 794,714 | 19,072 |
| E-C V2 | 352 | 792,250 | 22,164 |
| E-E | 352 | 807,297 | 15,613 |
| E-D | **0** | — | — |
| **total** | **2,106** | **4,104,407** | **81,355** |

Projected **2,112**; actual **2,106**. The six-call difference is exactly the six unconstructible
same-doc `U768` packages — the PF-G2 consequence, arriving as arithmetic. **Ceiling 4,000, not
approached.** All generation ran through the Batch API at its reduced rate.

## 9. Limitations

- **Single-run variance, mandatory caveat.** Every stage here is single-run. The generator is
  nondeterministic (v1.9's probe: 6/20 identical), so every number in §§3–5 is one draw and
  per-query direction counts inherit that noise.
- **Token-retaining prompts.** Both E-C variants keep the `NOT FOUND` token because scoring is
  mechanical. A prompt that omits it is untested, and the abstention behaviour reported here is
  behaviour *given* an explicit abstention instruction.
- **Difficulty-extremes inheritance.** Track A is the corpus constructed to contain the defects
  the formatter repairs. Nothing here escapes that; v1.11 attacks the reading claim on the same
  corpus that produced it.
- **Sampling parameters.** v1.8's `build_payload` sends no `temperature`, `top_p` or `top_k`
  (PF-9), and §6 requires that constructor. Whether v1.9's real-time client actually sent
  `temperature=0` or fell back to omitting it is **not recoverable from its record**, so
  §4's comparison against v1.9's frozen row may span two sampling regimes. Stated, not resolved.
- **E-A's cross-doc arm was expected near-zero and is not** (§1). That expectation was the
  plan's; the measurement is the run's.
- **The six-document scope limit** on PS-1 (§1, §2).

## 10. What this document does not do

No interpretation beyond the scoring lines. No paper text. No use of v1.11 to revisit any closed
verdict — including v1.9's: E-B's and E-C's failures to replicate magnitude are **scope
information about the reading claim, reported descriptively**, and what they mean is the Gate 1
ruling's to say. No edit to any closed artifact; nothing outside `v111/` paths and this document.

**STOP at Gate 1 for the ruling.**
