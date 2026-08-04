# PW-1 post-arm findings — PA series

**Recorded 2026-07-30, AFTER the arms ran.** Deliberately numbered **PA-n**, not `PW1-F*`.

The freeze carries `findings_recorded_pre_arm` = [PW1-F1, PW1-F2, PW1-F3, PROC-1]. Anything
surfacing during or after B5 belongs to a different epistemic class: it was found with the outcome
visible. Putting it in the same sequence would let a reader assume it was pre-registered, and the
distinction is small to make now and impossible to reconstruct later.

Ordering is checkable rather than asserted: the declarations were committed at
**`d68c0a6`, 2026-07-30 23:09:16 +0200**; the first arm value existed at
**`0eb04d3`, 23:46:00 +0200** — 37 minutes later.

---

## PA-1 — absorption is inert for retrieval scoring; the entire effect is inheritance

`S0 ≡ S1` and `S2 ≡ S3` **in outcome on all eight cells**: the absorbed channel never changes a
hit at k=5.

It is not a collapsed ladder, and that was checked rather than assumed — identical hit vectors are
also exactly what a broken pipeline produces. The rungs genuinely differ in **ranges**: on Track A's
fmt256, **132 of 235** chunks have `S2 ≠ S3` at the surface level and **184 of 235** have
`S0 ≠ S1`. Absorbed ranges change claimed surface and never change an outcome.

**Consequence, and it is the strongest defensive point in the result.** The four-rung ladder has
exactly two distinct levels: *with* inherited provenance and *without*. So:

- **The primary scoring coincides with the hostile floor.** S2 carries the headline and S3 is the
  most hostile reading anyone can ask for, and they agree on every cell. "You chose a harsh
  correction" has no purchase — the harshest available correction gives the same answer.
- **And a lenient one fails symmetrically**, since `S1 ≡ S0`.

The whole design therefore reduces to **one binary: does inherited provenance count as a hit?**
Every other choice in the ladder turned out inert. That is the sentence the results document should
be built around.

It also sharpens what the paper is missing. The channel carrying the entire measured effect is the
one at [formatted.py:86-94](src/chunkers/formatted.py#L86-L94), which the paper never describes.
The accurate claim is not "the effect shrank under a correction" but **"the measured benefit on the
size-matched control was mediated by an indexing behaviour the paper does not document."**

---

## PA-2 — the reported `r` was computed from rounded inputs (fourth A1f instance, first in output)

Every delta is a difference of recall@5 over a fixed query set, so `delta × n` is an integer and
`r` is a ratio of small integers. The first B5 run reported `r` from 4-dp values on **both** sides:

| cell | exact | first reported |
|---|---|---|
| family 1 MiniLM/A | 15/27 = **0.555556** | 0.5554 |
| family 1 bge/A | 16/26 = **0.615385** | 0.6154 |
| family 1 bge/B | −2/10 = **−0.200000** | −0.1994 |
| family 2 MiniLM/A | 1/44 ÷ 5/88 = **0.400000** | 0.3996 |

`−2/10` is the tell: no full-precision computation yields −0.1994.

Worse than a rounding wobble — **`stats.r` and `classification.r` disagreed on all eight cells**,
two values for one quantity, because the stats path used a full-precision numerator against a
stamped denominator while the classifier used rounded on both sides.

**Fixed at the source rather than tolerated.** `r`'s denominator is now the **D-7-verified
full-precision S0 delta**, asserted to round to the stamped figure — the same quantity at more
digits, which is precisely what D-7 licenses. `R_TOLERANCE` is tight again at 1e-9, and an
assertion requires `classification.r == stats.r` exactly.

An intermediate fix widened the tolerance to `|5e-5 / delta_full|`. It worked and was wrong twice:
it made A7 roughly **6× weaker** on Track B's small-delta cells than on Track A's, and it accepted a
precision defect instead of removing it.

**No classification moved.** Headlines are identical before and after.

---

## PA-3 — A7's coverage gap recurred one level up: rungs, not branches

The first run computed and reported `r` at S0, S1 and S3 but only ever called `retention_ratio` for
S2, so the halt could not fire on three of four rungs. **This is C-1 in a different costume**: a
guard declared over a quantity must run **wherever that quantity is computed**, not where it happens
to be consumed. C-1 closed branch coverage; this is rung coverage, and the frozen `halt_conditions`
says *"any cell"* — a surface of four rungs × eight cells.

Now fixed: `retention_ratio` runs on every rung. Recorded as the **general form**, because it has
recurred once.

**A correction that belongs to review, labelled per A1g.** The claim that `r > 1.0` is structurally
impossible absent a defect was right about the mathematical quantity and wrong about the computed
one, because it did not carry the denominator's rounding through. Tightening the tolerance on the
strength of that argument would have *built* the false halt rather than found it. Hypothesis, not
verified — the same status as the thermal hypothesis in E-5.

---

## PA-4 — an empty family and an underpowered one were rendering identically

`aggregate()` returns UNDERPOWERED both when an arm ran and could not discriminate **and** when no
cell was ever applicable. The secondary family is the second case: zero applicable cells, so the
correction arm was never exercised there at all.

That is the `BLOCKED / ENVIRONMENT` principle exactly — **attempted-and-blocked must never render
identically to never-attempted.** The reporting layer now distinguishes them and the frozen
vocabulary is not stretched to cover it: the label is **NO APPLICABLE CELLS**, introduced here and
named as a post-arm reporting distinction rather than as a frozen branch.

The predicates are now printed with every headline rather than left to be reconstructed:

- **applicable** — branch 1 did not fire, i.e. `delta_full` is significant under the frozen
  `branch_1_significance`. Computable from the freeze alone.
- **powered** — branch 2 did not fire, i.e. the S2 CI does not contain **both** zero and
  `delta_full`.

---

## PA-5 — the third silent-mutation instance

`pw1_f1_refers_to` dropped during an A4b fold-in; NUL bytes written by a patch script; and a
`str.replace` that matched nothing while printing success. One class: **a mutation that reports
success without verifying it occurred.** Now template rule **A1h**.

The uncomfortable corollary was faced while it is cheap: one instance of this class reached the
stamped freeze undetected. A hash proves the text has not changed since stamping; it cannot prove
the text is *complete against what was intended*.

**Referential-integrity sweep on `freeze_text_verbatim`, run and recorded:** 49 declared fields, 8
backtick-quoted identifiers, **0 file paths absent from the repo**. Six identifiers do not resolve
within the freeze text — `absorbed`, `excess`, `p_holm`, `prose_rule`, `significant_definition`,
`top_hit_provenance` — and all six resolve *externally* and correctly: to the v1.1 pre-registration,
the v1.5 pre-registration, the published `pairwise` block, the `per_query.jsonl` schema, and §2's own
surface components. **No dangling internal pointer.**

---

## What did NOT change

The p-procedure was `exact_signflip_p` throughout, as declared in D-2. No Monte-Carlo substitution
was made under time pressure; `p_mc_10k` is retained beside every exact value as §6 requires. D-1's
`full_significant` and `delta_full` were read from the stamped freeze and never recomputed, and the
run asserted its applicable-cell counts against the frozen **3 / 1 / 0** before computing anything.
