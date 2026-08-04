# B5: go — after four declarations are pinned

2026-07-30 · guard 1 **8/8** · exact reproduction on the unchanged path · pre-arm queue clear

**Run it.** Not this hour, though — spend thirty minutes closing the four declaration-level items
below first, because every one of them is a choice that must be made *before* the numbers exist and
cannot be made after. The one-shot rule is not a formality here: once S1/S2/S3 are computed, any
adjustment to the p-procedure, the Holm scope, the powered predicate or the CI seed is a choice
made under known outcomes, and no amount of good faith repairs that.

Your reading of the guard-1 result is right on every point, including the two I would have argued
for you: this is exact reproduction on the unchanged path rather than `PASS UNDER DECLARED
DEVIATION`, and `run-20260726-191447` is now confirmed by independent execution. The mixed-path `r`
problem is gone rather than mitigated. That is the best available outcome and it was not the likely
one two days ago.

---

## 1. Run S0 as arm zero, and assert it reproduces the stamped `delta_full` exactly

This is the single most valuable thing in this document. Before reading any corrected value:

**Recompute S0 from `_arm_inputs` and assert it equals the stamped `delta_full` and the stamped
levels, per cell, exactly.**

S0 is already published, so recomputing it is a reproduction check rather than an outcome under the
frozen interpretation — it costs nothing in post-hoc integrity and it is the only thing standing
between you and a silent base mismatch. Every arm value is a ratio against `delta_full`. If the
persisted `per_query` rows and `source_ranges` inventories do not reconstruct the published
scoring — an off-by-one in offsets, a unit dropped from an inventory, a different overlap
predicate — then S1/S2/S3 are all measured against a base that the numerator does not share, and
`r` is quietly meaningless while looking entirely reasonable.

It also answers a small ambiguity in your report. You wrote "one build, one retrieval per cell,"
which reads as retrieval being re-executed, and separately that S1/S2/S3 "re-score with no encoding
at all." Both can be true, but the S0 identity check makes the question moot: whatever B5 does to
get to ranked lists, it either reproduces the published S0 to the digit or it halts.

Demonstrate the checker per §A1b before trusting it — perturb one `source_range` by one character
and require the assertion to fire.

**The companion invariant, and it is cheap:** `orig256`'s per-query hit vector must be *identical*
across S0, S1, S2 and S3, cell by cell. `W_index_char` is exactly 1.0000 for `orig256` on both
tracks, so it has no absorbed and no inherited width to strip — the ladder cannot touch it. If
orig's hits move at any rung, the stripping code is reaching the wrong condition, and that is a
defect that would otherwise present as a plausible-looking `r`.

---

## 2. `full_significant` comes from the freeze. It is never recomputed.

`classify_cell` takes `full_significant` as an input, and branch 1 turns on it. The stamped p-values
are Monte-Carlo (errata item 1), so a recomputation with any different seed, iteration count or
procedure can land on a different side of the line. Family 1 bge/B sits at `p_holm = 0.02700`; it is
the closest applicable cell to its threshold, and it is one of the two cells that unblocked today.

Pin it: `full_significant` and `delta_full` are read from `posthoc_PW1_provenance_width.json` and
from nowhere else. Assert that the loaded values match the stamped ones before the run proceeds.
`applicable_cell_counts` (3 / 1 / 0) is the check on that — if the arm run's own count of applicable
cells does not equal the frozen count, halt.

---

## 3. Use the declared p-procedure — and check first that it can actually run

The errata records that §6 declares exact sign-flip enumeration while the carried `p_raw` came from
`paired_permutation_p`. Repeating that divergence *after* documenting it would be a materially worse
defect than inheriting it was: the first was an oversight, the second would be a knowing choice. The
arms use `exact_signflip_p`.

**But check its implementation before pointing it at the arms**, because I think it may not be able
to finish. If it literally enumerates `2^K` over discordant pairs, family 1 MiniLM/A is out of
reach — the net difference is 27 queries out of 176, so `K` is plausibly 40–60 and `2^50` does not
terminate. Family 1 bge/B looks feasible (`b − c = 10`, `p_raw` 0.0135 implies `K` around 16–20),
which is exactly the pattern that lets an infeasibility hide until it meets the biggest cell.

The fix is not an approximation. For equal-magnitude paired differences — which recall@5 per-query
diffs are, being in {−1, 0, +1} — the sign-flip enumeration is *identically* the binomial tail:

    p_one_sided = P(Binomial(K, 0.5) >= b)

where `K` is the discordant count and `b` the count favouring the formatted arm. That is the same
number the enumeration would produce, in closed form, and it is McNemar's exact test. Substituting it
is not a deviation from §6; it is §6 computed correctly. State that equivalence in the errata so the
substitution is visible rather than assumed.

Note this also unblocks errata item 1 — the exact-p table over the published cells has the same
feasibility problem and the same resolution.

---

## 4. Declare Holm's scope, and name the CI with its seed, before the run

Two things `classify_cell` consumes that are not yet pinned in anything I have seen:

**Holm's scope across the ladder.** The freeze says `branch_1_significance = "Holm within the
declared PW-1 family"`, and the family is a set of cells. The arms produce three scorings per cell.
So: does S2 alone enter the family (S1 and S3 being diagnostic), or do all three enter, tripling the
family and moving every threshold? Both are defensible. Only one can be chosen now. My reading of
the freeze is that S2 is the primary scoring and the family is the cells at S2, with S1 and S3
reported as the stress test and the hostile floor rather than as competing hypotheses — but it is
your declaration to make, and it must be made in writing before the run.

**The CI procedure, named.** Errata item 2 exists because §5 asserts three criteria agree while
specifying two. Do not let the arms inherit that: state `paired_bootstrap_diff`, percentile method,
iteration count, and **the seed**. A bootstrap CI without a recorded seed is not reproducible, and
`ci_corrected` binds on classification.

And state the combination rule: `classify_cell` takes both `ci_corrected` and `p_holm_corrected`.
If they disagree on a cell — which they already did once, on secondary bge/B — which one governs?
Conjunction, or p governs with CI descriptive? That is an §A5 item: one quantity, one procedure,
exhaustive and disjoint.

---

## 5. What does `aggregate()` mean by "powered"?

`aggregate()` takes the least favourable label among applicable, **powered** cells. I have never seen
the powered predicate defined. If it is a declared threshold computable from frozen inputs, fine —
name it and check it. If it depends on arm outputs, it is still fine, but only if it is fully
specified now. If it is neither, then after the arms run it becomes a judgement about which cells
count, made by someone who can already see which cells are unfavourable. That is the exact failure
the pre-registration exists to prevent, and it would be a shame to walk into it on the last step.

This is the item I would most expect to be under-specified, and it is the cheapest to close today.

---

## 6. `r > 1.0` now has exactly one meaning — which upgrades A7

Worth writing down, because the interpretation has changed under you.

Retrieval is unchanged across the ladder; only provenance attribution narrows. Narrowing
`source_ranges` can remove overlaps and never add them, and `orig256` has no width to narrow. So
`delta_corrected <= delta_full` holds **structurally**, for every cell, on the unchanged path.

Consequently `r > 1.0` is now impossible absent a defect. Under the mitigated path it would have been
ambiguous — deviation artifact or code error — and §3.4 existed to pre-decide the diagnostic order.
That ambiguity is gone. A7 is no longer a diagnostic; it is an assertion, and its firing means the
scoring code is wrong. Record it in those terms, and delete the §3.4 diagnostic order rather than
leaving it to imply a possibility that no longer exists.

The other end needs a word too: `r < 0` is legitimate and reachable — it means the formatted arm
falls below `orig256` once the width is stripped. It must classify (below `R_NOT_SEPARATED`, the
hostile reading) and must not halt. Confirm no floor guard catches it.

---

## 7. The record: state the path difference, then state why it is inert

"No deviation to declare" is the correct disposition and it is not the same as "nothing to write
down." The encode ran on the sharded path; the published run ran monolithically. A reader six months
out *will* notice that, and if the only trace is an absence they will reasonably wonder what was not
disclosed.

Write it positively in the guard-1 disposition: the path differed, bit-identity was established by
construction (replicated global length sort, cut at multiples of the published `batch_size`,
identical batch sets, no reduction across the batch dimension) and demonstrated by `np.array_equal`
on MiniLM across six tests including the tie-split and row-order cases — and is now independently
corroborated for bge by exact reproduction of all four family-1 levels. That is a stronger statement
than silence and it costs one paragraph.

**On the three-tier framing, do not over-claim in the direction of relief.** Tier 3 closes
completely — family 1's bge cells are obtained. Tier 2 narrows a great deal but does not formally
close: the composition cells (C0–C5) use different chunkings, and their encodes were not themselves
re-executed. What you have is bge demonstrated deterministic and correct on this stack for two of
the corpus's text sets, plus the mechanism argument that an allocation failure cannot perturb a
completed encode. Say exactly that. The discipline that made "no bge number is established" an
over-correction cuts symmetrically, and the record is more credible for marking the one thing that
is still inference.

The rest of the record pass stands as written yesterday: `BLOCKED / ENVIRONMENT` moves to resolved
with the diagnosis, `BLOCKED / PLATFORM SUSPECT` is retired, E-5 gets its final version, and my
thermal hypothesis is labelled per A1g.

The checkpointing detail is worth keeping visible, by the way — Track B resuming from 12 banked
batches, and no retry firing once memory was freed, is a clean confirmation of the diagnosis rather
than a workaround masking it. That belongs in the record as evidence, not just as narrative.

---

## 8. Still outstanding, still not mine

The note to your approver naming PW1-F1 and PW1-F3. It has now been carried across four of these
documents. It is the only item on the whole list with another person's time running against it, and
guard 1 closing removes the last reason to think anything else needs to land first.

---

## In order

1. Pin §2 (`full_significant` from the freeze), §4 (Holm scope, CI procedure, seed, combination
   rule) and §5 (the powered predicate) **in writing**, dated, beside the freeze.
2. Check `exact_signflip_p` terminates on the largest cell; substitute the binomial closed form if
   it does not, and record the equivalence.
3. Run S0 as arm zero. Assert reproduction of the stamped values and the orig-invariance across the
   ladder. Demonstrate both checkers failing first.
4. Then B5, all cells, all three arms, in one pass. Classify with `classify_cell`, aggregate with
   `aggregate()`, and read the output once.
5. B6 with every guard's disposition recorded, including the resolved blocks.

If (3) reproduces, the rest is arithmetic on data that is already on disk, and the fault-exposed
part of this project is behind you.
