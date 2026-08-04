# PW-1 arm declarations — pinned BEFORE the arms run

**Dated 2026-07-30, after guard 1 closed 8/8 and before any S1/S2/S3 value exists.**
**Beside the freeze, never inside it.** Nothing here alters a stamped value. Each item is a choice
that must be made before the numbers exist and cannot honestly be made after — raised by review in
`Decision_B5_go_2026-07-30.md`.

No arm has been run. No corrected delta, ratio or classification exists.

---

## D-1 — `full_significant` and `delta_full` are READ from the freeze, never recomputed

Both are loaded from `posthoc_PW1_provenance_width.json` and from nowhere else. The runner asserts,
before computing anything, that the values it loaded match the stamped ones, and that its own count
of applicable cells equals the frozen `applicable_cell_counts` — **3 / 1 / 0** for family 1,
family 2 and the secondary family. A mismatch halts.

**Why this is not paranoia.** The stamped `p_raw` values are Monte-Carlo (errata E-1), so a
recomputation under a different seed, iteration count or procedure can land on the other side of α.
Family 1 bge/Track B sits at `p_holm = 0.02700` — the closest applicable cell to its threshold, and
one of the two that only unblocked today. Recomputing significance would put that cell's
applicability in the hands of an arbitrary seed.

---

## D-2 — the arms use `exact_signflip_p`, and it is already the closed form

§6 of the freeze declares exact sign-flip enumeration. E-1 records that the *carried* `p_raw` values
came from `paired_permutation_p` instead. Repeating that divergence after documenting it would be
worse than inheriting it: the first was an oversight, the second would be a knowing choice. **The
arms use `exact_signflip_p`.**

Review flagged a feasibility risk — that literal `2**K` enumeration would not terminate on the
largest cell, where `K` may be 40–60. **It does not arise.** The implementation is `O(K)` over
binomial coefficients:

```python
extreme = sum(comb(K, j) for j in range(K + 1) if abs(2 * j - K) >= abs(S) - 1e-9)
```

which *is* the closed form review proposed substituting. Verified two ways: it agrees with the
two-sided binomial tail `min(1, 2·Σ_{j≤min(b,K−b)} C(K,j) / 2^K)` on **300 random (K, b) cases with
zero disagreements**, and it returns in under a millisecond at `K = 400`. The largest real cell,
family 1 MiniLM/A at `K = 47`, computes in 7 ms.

So no substitution is made and none is needed; the equivalence is recorded here because review was
right that it had to be established rather than assumed. `p_mc_10k` is retained beside every exact
value, as §6 requires.

---

## D-3 — Holm's scope: **the family is the cells at S2**

S2 is the primary scoring. Holm within a PW-1 family corrects across the **cells** of that family at
**S2 only**:

| Family | Holm family size at S2 |
|---|---|
| family 1 | 4 cells |
| family 2 | 2 cells |
| secondary | 2 cells |

S1 and S3 are **not** competing hypotheses and do not enter the family. S1 is the stress test
(absorption stripped, a channel the paper defends) and S3 is the hostile floor (both channels
stripped); their `r` and CI are reported descriptively. Tripling the family to nine would penalise
by family size rather than by evidence, and would apply a multiplicity correction across three
*views of the same comparison* rather than across distinct comparisons.

This follows the freeze's own `arm_semantics` — S2 is a correction, S1/S3 are a stress test and a
floor — and it is the reading review proposed. Declared here so it is a written choice.

---

## D-4 — the CI procedure, named, with its seed

`src/stats/tests.py::paired_bootstrap_diff` — **paired bootstrap percentile interval**, resampling
query indices with replacement.

| Parameter | Value |
|---|---|
| `iters` | **10000** |
| `seed` | **1337** |
| `ci` | **0.95** |
| zero rule | frozen `boundary_rule`: a bound of exactly 0.0000 does **not** exclude zero |

A bootstrap CI without a recorded seed is not reproducible, and `ci_corrected` binds on
classification through branches 2 and 3.

### D-4b — the combination rule when the CI and the Holm-p disagree

**The CI governs branches 2 and 3; the Holm-p governs branch 4. Neither is overridden by the
other, because they gate different branches, and the branch order resolves any apparent conflict.**

Concretely, as implemented in `classify_cell` and evaluated first-match-wins:

- branch 2 (UNDERPOWERED) — **CI only**
- branch 3 (NOT SEPARATED) — `r` **or** CI
- branch 4 (SEPARATED) — `r` **and** Holm-p
- branch 5 — residual

So a cell whose CI excludes zero but whose Holm-p does not clear α cannot reach SEPARATED; it lands
in branch 5, PARTIALLY SEPARATED. That is the disagreement case, it is decided by the ordering, and
the ordering is frozen. This is the §A5 answer: one procedure per branch, exhaustive and disjoint,
no analyst choice at the point of conflict.

---

## D-5 — "powered" is already fully determined; recorded so it cannot drift

`aggregate()` takes the least favourable label among **applicable and powered** cells. Both
predicates are computable and neither requires a judgement after the numbers exist:

- **applicable** — branch 1 did not fire, i.e. `delta_full` is significant under the frozen
  `branch_1_significance`. Computable from the freeze **alone**, before any arm runs. Already fixed
  at 3 / 1 / 0.
- **powered** — branch 2 did not fire, i.e. the S2 CI does **not** contain both zero and
  `delta_full`. Computable from the S2 CI plus the frozen `delta_full`.

Implementation: `_ORDER` contains only NOT SEPARATED, PARTIALLY SEPARATED and SEPARATED, so NOT
APPLICABLE and UNDERPOWERED cells are excluded from the aggregate by construction rather than by
inspection. If no cell in a family is both applicable and powered, that family's headline is
UNDERPOWERED.

---

## D-6 — `r > 1.0` is now an ASSERTION, not a diagnostic

The interpretation changed when guard 1 closed on the unchanged path.

Retrieval is identical across the ladder; only provenance attribution narrows. Narrowing
`source_ranges` can remove overlaps and never add them, and `orig256` has **no** width to narrow —
`W_index_char` is exactly 1.0000 on both tracks. So `delta_corrected ≤ delta_full` holds
**structurally**, for every cell.

Under a mitigated encode path `r > 1.0` would have been ambiguous — deviation artifact or code
error — which is why a diagnostic order was pre-decided. **That ambiguity no longer exists.**
`r > 1.0` now means the scoring code is wrong, full stop. The pre-decided diagnostic order is
**retired** rather than left to imply a possibility that cannot occur.

**The other end must not be caught.** `r < 0` is legitimate and reachable: it means the formatted
arm falls below `orig256` once width is stripped. It must classify — below `R_NOT_SEPARATED`, the
hostile reading — and must **not** halt. Confirmed: `retention_ratio` guards only the upper bound,
and `test_sign_flip_gives_negative_r_and_does_not_halt` pins it.

---

## D-7 — S0 runs as arm zero, and must reproduce the stamped values exactly

Before any corrected value is read, S0 is recomputed from `_arm_inputs` and asserted equal to the
stamped `delta_full` **and** the stamped levels, per cell.

S0 is already published, so this is a reproduction check rather than an outcome under the frozen
interpretation — it costs nothing in post-hoc integrity and it is the only thing standing between
the analysis and a silent base mismatch. Every arm value is a ratio against `delta_full`; if the
persisted `per_query` rows and unit inventories do not reconstruct the published scoring — an
off-by-one in offsets, a unit missing from an inventory, a different overlap predicate — then
S1/S2/S3 are measured against a base the numerator does not share, and `r` is meaningless while
looking entirely reasonable.

**Companion invariant.** `orig256`'s per-query hit vector must be **identical across S0, S1, S2 and
S3**, cell by cell. The unformatted arm has no absorbed and no inherited width, so the ladder cannot
touch it. If orig's hits move at any rung, the stripping is reaching the wrong condition — a defect
that would otherwise present as a plausible-looking `r`.

Both checkers are demonstrated failing before they are trusted, per §A1b: one `source_range`
perturbed by a single character must fire the S0 assertion, and a deliberately mis-targeted strip
must fire the orig-invariance assertion.

---

**Declared before the arms. Nothing above is revisable once a corrected value exists.**
