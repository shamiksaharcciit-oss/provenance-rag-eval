# v1.7 E1 — span integrity at matched budget

**Pre-registration:** `Plan_v17_ReadingValue_2026-08-01.md`, frozen at `e19dd35` @
2026-08-01T11:40:20Z, with pre-freeze amendments PF-1/PF-2/PF-3 in its §0.
**Cells:** A-MiniLM (decision-bearing, n=176), A-bge (n=176), B-MiniLM (n=150).
**Runner:** `scripts/integrity_sweep.py`, authored after the freeze. Arm construction is
**imported** from `scripts/segment_size_sweep.py`, so plan §2.1's "unchanged" is true by
construction rather than asserted.
**Status:** Gate 1. E1 complete on all three cells. **No E2 work of any kind has been started.**

---

## 0. The one thing a reader must carry into every number below

**`integrity_full` and `integrity_single` require every character of the gold span to be
covered. Naive units cover one contiguous character range; formatter units cover a union of
sentence ranges with the inter-sentence whitespace belonging to no unit.** The metric therefore
charges the formatter arms for whitespace they never claimed, and it does so only where gold
spans cross sentence boundaries.

Measured, not inferred (`Track B`, S768): naive units carry a median of **1** source range and
**0/378** have gaps; formatter units carry a median of **31** ranges and **378/381** have gaps,
**11,137** in total, and a sampled gap is the two characters `'\n\n'`.

This does not touch Track A and it dominates Track B. §6 states the consequence and §7 quarantines
what depends on it. It is reported here, first, because a reader who meets Track B's numbers
without it will draw a conclusion the apparatus does not support.

---

## 1. PE1-4 — the control, scored first

> **PE1-4 (control, A-MiniLM, `integrity_single`):** `D_int_size > 0` — the mechanical size
> effect appears where it must. If it does not, the metric or the apparatus is suspect and
> everything else in E1 is quarantined pending a ruling.

| cell | `D_int_size` (`integrity_single`) | CI95 | p | n01 / n10 |
|---|---|---|---|---|
| **A-MiniLM** | **+65/176 = +0.3693** | [+0.2841, +0.4545] | 0.00010 | 73 / 8 |
| A-bge | +58/176 = +0.3295 | [+0.2386, +0.4205] | 0.00010 | 70 / 12 |
| B-MiniLM | +6/150 = +0.0400 | [−0.0333, +0.1133] | 0.36256 | 18 / 12 |

**PE1-4 HOLDS on its named cell.** The mechanical size effect is present and large. Nothing in
E1 is quarantined by this control. (Track B's `D_int_size` is small and its interval spans zero;
PE1-4 is stated over A-MiniLM alone and is not scored there.)

---

## 2. The apparatus check — v1.6 `recall@budget` reproduction

Plan §2.5 makes a mismatch an APPARATUS-STOP. The check is an executed `assert` inside the
runner, on integer numerators; it would have halted the cell rather than printed a result.

| arm | A-MiniLM v1.7 / v1.6 | A-bge v1.7 / v1.6 | B-MiniLM v1.7 / v1.6 |
|---|---|---|---|
| `U256` | 109 / 109 | 114 / 114 | 65 / 65 |
| `U768` | 132 / 132 | 128 / 128 | 50 / 50 |
| `U768-ws` | 132 / 132 | 128 / 128 | 50 / 50 |
| `S768` | 133 / 133 | 130 / 130 | 51 / 51 |
| `F768` | 133 / 133 | 132 / 132 | 49 / 49 |

**15 of 15 reproduce exactly.** The retrieval apparatus is the one v1.6 published.

---

## 3. Arm levels

Integer numerators; denominator 176 (Track A) and 150 (Track B). Rung S2 primary, S3 reported
(PF-1).

### A-MiniLM (decision-bearing)

| arm | units | `integrity_single` | `integrity_full` | feasible | infeasible | S3 single |
|---|---|---|---|---|---|---|
| `U256` | 238 | 61 | 78 | 123 | 53 | 61 |
| `U768` | 90 | 126 | 128 | 170 | 6 | 126 |
| `U768-ws` | 90 | 126 | 128 | 170 | 6 | 126 |
| `S768` | 90 | 129 | 132 | 172 | 4 | 129 |
| `F768` | 90 | 133 | 133 | 176 | 0 | **41** |

### A-bge

| arm | units | `integrity_single` | `integrity_full` | feasible | infeasible | S3 single |
|---|---|---|---|---|---|---|
| `U256` | 238 | 64 | 80 | 123 | 53 | 64 |
| `U768` | 90 | 122 | 126 | 170 | 6 | 122 |
| `U768-ws` | 90 | 122 | 126 | 170 | 6 | 122 |
| `S768` | 90 | 126 | 130 | 172 | 4 | 126 |
| `F768` | 90 | 132 | 132 | 176 | 0 | **40** |

### B-MiniLM

| arm | units | `integrity_single` | `integrity_full` | feasible | infeasible | S3 single |
|---|---|---|---|---|---|---|
| `U256` | 1072 | 21 | 23 | 48 | 102 | 21 |
| `U768` | 378 | 27 | 30 | 89 | 61 | 27 |
| `U768-ws` | 378 | 27 | 30 | 89 | 61 | 27 |
| `S768` | 381 | **1** | **1** | **3** | 147 | 1 |
| `F768` | 381 | **1** | **1** | **3** | 147 | 1 |

**Feasibility attribution (§2 of the Gate 1 instructions).** The infeasible column is the count
of queries no unit in that arm's *entire inventory* can satisfy. On both Track A cells the
ceiling falls monotonically with unit size and reaches 0 at `F768`. On Track B it collapses in
the opposite direction for the formatter arms only — 3/150 feasible against `U768`'s 89 — which
is §0's artifact, not a property of the formatter's boundaries.

**The S2→S3 drop at `F768` is large on both Track A cells** (133→41, 132→40) and absent
everywhere else. S3 strips absorbed ranges, so this is dedup/absorption carrying most of `F768`'s
claimed coverage. Reported descriptively; no test, no mechanism claimed.

---

## 4. Decomposition

Every contrast carries `n01`/`n10` beside the net, descriptively, never tested on (R3/A5b). The
lattice identity `size + ws + seam + edit == total` is an **executed check**
(`assert_decomposition`) on integer numerators, run once per metric per cell — 6 executions, all
passed, with the summed numerators shown.

### `integrity_single`

| contrast | A-MiniLM | A-bge | B-MiniLM |
|---|---|---|---|
| `D_int_size` | +65/176 · n01 73 n10 8 | +58/176 · n01 70 n10 12 | +6/150 · n01 18 n10 12 |
| `D_int_ws` | **0/176 · n01 0 n10 0** | **0/176 · n01 0 n10 0** | **0/150 · n01 0 n10 0** |
| `D_int_seam` | +3/176 · n01 5 n10 2 | +4/176 · n01 6 n10 2 | **−26/150 · n01 1 n10 27** |
| `D_int_edit` | +4/176 · n01 12 n10 8 | +6/176 · n01 12 n10 6 | 0/150 · n01 0 n10 0 |
| `D_int_total` | +72/176 | +68/176 | −20/150 |
| lattice | 72 == 72 ✓ | 68 == 68 ✓ | −20 == −20 ✓ |

### `integrity_full`

| contrast | A-MiniLM | A-bge | B-MiniLM |
|---|---|---|---|
| `D_int_size` | +50/176 · n01 60 n10 10 | +46/176 · n01 58 n10 12 | +7/150 · n01 20 n10 13 |
| `D_int_ws` | **0/176 · n01 0 n10 0** | **0/176 · n01 0 n10 0** | **0/150 · n01 0 n10 0** |
| `D_int_seam` | +4/176 · n01 6 n10 2 | +4/176 · n01 6 n10 2 | **−29/150 · n01 1 n10 30** |
| `D_int_edit` | +1/176 · n01 9 n10 8 | +2/176 · n01 8 n10 6 | 0/150 · n01 0 n10 0 |
| `D_int_total` | +55/176 | +52/176 | −22/150 |
| lattice | 55 == 55 ✓ | 52 == 52 ✓ | −22 == −22 ✓ |

`D_int_ws` is **exactly zero with zero discordant pairs in all six cell-metric combinations**. The
whitespace control has now come back empty in two consecutive experiments.

---

## 5. `F_INT` — the only tested family

Two members, `integrity_single`, Holm-corrected within the declared family only.

| cell | `D_int_seam` p_raw → p_holm | `D_int_edit` p_raw → p_holm |
|---|---|---|
| **A-MiniLM (decision-bearing)** | 0.447355 → **0.89471** | 0.501050 → **0.89471** |
| A-bge | 0.283872 → 0.472352 | 0.236176 → 0.472352 |
| B-MiniLM | 0.000100 → 0.000200 | 1.000000 → 1.000000 |

**On the decision-bearing cell, neither member of `F_INT` is positive with `p_holm < 0.05`.**
Against the frozen gate rule in §5 of the plan, that is the **INTEGRITY-KILL** condition as
written. The branch is the ruling's to declare; this document states which condition the numbers
meet and stops there.

B-MiniLM's `D_int_seam` is significant and **negative**, and it is the quantity §0's artifact
dominates. It is not evidence about boundary placement. See §7.

---

## 6. Sealed predictions

Scored against the frozen text, on named cells only. All HYPOTHESIS under A1g.

| id | cell | sealed claim | evidence | verdict |
|---|---|---|---|---|
| **PE1-4** | A-MiniLM | `D_int_size > 0` (control) | +65/176, p=0.00010 | **HOLDS** |
| **PE1-1** | A-MiniLM | `D_int_seam > 0` | +3/176, CI [−0.0114, +0.0455], p_holm 0.89471 | **NOT SUPPORTED** — direction positive, interval spans zero |
| **PE1-2** | A-MiniLM | `D_int_edit ≥ 0` | +4/176, non-negative | **HOLDS** |
| **PE1-3** | A-MiniLM | `F768 ≥ U768` on `integrity_full` (direction only) | 133 ≥ 128 | **HOLDS** |
| **PE1-5** | B-MiniLM | sign of `D_int_seam` matches Track A's | Track A +3/176, Track B −26/150 | **FAILS — on an artifact-dominated quantity (§7)** |

PE1-1 is the prediction the experiment was built to test, and it is not supported on its own
cell. PE1-2 and PE1-3 hold but are the weak forms: non-negativity and a direction.

---

## 7. What §0's artifact quarantines, and what it does not

A diagnostic was run after the cells completed, to characterise the artifact rather than to
re-score anything. **The frozen numbers in §§1–6 stand as the result; nothing below replaces
them.** It recomputes arm feasibility with gaps that contain *only whitespace* bridged:

| cell / arm | feasible as scored | whitespace gaps bridged | delta |
|---|---|---|---|
| Track A `S768` | 172/176 | 172/176 | **+0** |
| Track A `F768` | 176/176 | 176/176 | **+0** |
| Track B `S768` | 3/150 | 93/150 | **+90** |
| Track B `F768` | 3/150 | 91/150 | **+88** |

**Track A is untouched by the artifact — delta exactly zero on both formatter arms.** Its gold
spans are short (median 69 chars) and sit inside single sentences, so no gold span crosses a
whitespace gap. **The decision-bearing cell, `F_INT`, PE1-1..PE1-4 and the whole of §§1–5 for
Track A are unaffected.**

**Track B's formatter arms are dominated by it.** Its gold spans are long (median 843 chars,
max 3868) and cross many sentence boundaries. `S768` and `F768` scoring 1/150 is very largely the
metric charging them for `'\n\n'`.

**Therefore quarantined, pending a ruling:** B-MiniLM's `D_int_seam` (both metrics),
`D_int_total`, the `S768`/`F768` levels and feasibility ceilings on Track B, and **PE1-5's
failure**. None of these is evidence about the formatter, and none should be quoted as such.

**Not quarantined:** everything on both Track A cells, and Track B's `U256`/`U768`/`U768-ws`
arms, whose units are contiguous and carry no gaps.

I did not change the metric. The definition is frozen and the numbers it produced are reported as
it produced them; whether E1 on Track B should be re-run under an amended metric is a new
pre-registration question and not mine.

---

## 8. Controls that earned their place by coming back empty

- **Multi-document gold: 0/176 and 0/150.** No query's gold spans span two documents, so
  `integrity_single` is never unsatisfiable for a structural reason. Defined and tested in code
  anyway, because a metric must be total over its input domain.
- **Zero-length gold spans: 0/176 and 0/150**, confirmed per arm in every cell
  (`degenerate_gold_spans = 0`, 15/15 arms). The vacuous-coverage branch never executed.
- **`D_int_ws` = 0/176, 0/176, 0/150** with zero discordant pairs, both metrics.

---

## 9. Run parameters and provenance

Retrieval unchanged from v1.6: dense + BM25, RRF `k_rrf=60`, `candidate_pool=50`, seed 1337,
depth 50, budget 1920, take units in rank order and include the unit crossing the budget.
Realised k stayed under depth on every arm (R4 assert). Statistics: `paired_bootstrap_diff`
percentile CI + `paired_permutation_p`, 10,000 iterations, seed 1337, ci 0.95.

**A-bge ran with `--sharded-encode`** — process-isolated per-batch encoding, bit-identical and
pinned by `tests/test_pw1_safe_encode.py`. Every batch restored from checkpoint (2/2 on each of
five arms); PROC-1 records checkpoint counts and content hashes in the manifest. Free memory was
488 MB at launch against PW-1's ~393 MB bge failure point, which is why it was used.

**Memory margins per arm** (free MB after each arm, against the 393 MB known failure point):
A-bge 432 / 498 / 455 / 604 / **394**; B-MiniLM 700 / 862 / 735 / 804 / 516. A-MiniLM ran before
the margin recorder existed and has none — stated rather than back-filled. **A-bge's `F768`
margin of 394 MB is one megabyte above the known failure point**; that cell completed and every
arm reproduced, but the margin is thin enough to record prominently.

No LLM call was made by E1. `F768` formatter output came entirely from cache — verified before
each track by a guard that raised on any cache miss: Track A 45/45 documents, Track B 60/60,
zero misses. **Nothing was spent.**

---

## 10. Limitations

- **Contamination, restated from the frozen plan.** Strict-containment cross-checks
  (`strict_containment: 0.5`) were computed in prior runs and may have been partially observed by
  both sides before E1's hypotheses were written. Every E1 prediction is HYPOTHESIS under A1g and
  none is VERIFIED-in-advance. All arm values here are fresh runs under the v17 ID; no prior
  strict-containment number was quoted or checked against.
- **The whitespace artifact (§0, §7)** is the largest limitation and was not anticipated at
  freeze. It is a defect in the metric's definition, not in its implementation.
- **Pre-freeze probe numbers do not reconcile with anything here, by design.** The F2 probe gave
  Track B 61 (max over `U768` alone) and the freeze exercise 65 (max over three arms, `F768`
  excluded because it needs the LLM). The feasibility ceilings in §3 are a third quantity again —
  computed over the arm's whole inventory at rung S2 under the frozen procedure. Three
  definitions, three numbers; they are not meant to agree and are not reconciled here.
- **`integrity_single` is size-sensitive by declaration** (plan §2.2), which is why no headline is
  taken from `F768 − U256` and why `D_int_seam` and `D_int_edit` — which hold size fixed — are the
  family.
- A-MiniLM has no memory margins recorded; the recorder was added before A-bge.

---

## 11. What this document does not do

No E2 work of any kind was started — no determinism probe, no package built, no prompt rendered,
no generation. No v1.7 number is used to revisit v1.6 or PW-1. No closed artifact, the white
paper or the brief was touched. The branch is not declared here; §5 states which frozen condition
the decision-bearing cell's numbers meet, and the ruling declares the branch.

Rule-shaped observations this run surfaced are recorded in the Gate 1 report as candidates for
the next pre-registration. None is applied here.
