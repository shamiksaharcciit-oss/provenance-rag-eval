# B4 decision: the two blocked bge family-1 cells

Commit `4addd64` · 6 of 8 guard-1 cells pass · asked 2026-07-30

**Short answer: neither (a) nor (b) yet. Try (c) first — rebuild the pinned environment — because
the artifact you added one step ago probably contains the fix, and if it does there is no
deviation to record and no decision to make.**

If (c) fails, take (a), but not in the form you proposed: unbundle the mitigation, measure the
perturbation on MiniLM, and bound it with a margin analysis before accepting it. **(b) is very
likely not available at all**, for a reason I think is the most important thing in this note, so
I have put it first.

---

## 1. Check whether (b) is an option before weighing it

You wrote, in the guard-1 artifact for family 1, that the cells needed a **re-run** because *"no
persisted per-query vectors exist for the size-matched control."*

If that is true — and it was true for MiniLM — then it is true for bge, and it has a consequence
that reaches past the guard: **the S1/S2/S3 arms for those two cells need the same artifacts the
blocked re-run would produce.** Re-scoring is what makes the composition cells cheap; it works
because the retrieval results are on disk. For the size-matched control they are not.

So (b) as stated — "record unverified and proceed to B5" — may not be a choice about how much
verification family 1 carries. It may be a statement that **family 1's two bge cells cannot be
run at all**, which is a different and much larger thing:

- Family 1 has four cells, three applicable (MiniLM/A, bge/A, bge/B; MiniLM/B is NOT APPLICABLE).
- Both blocked cells are applicable.
- `aggregate()` takes the least favourable label among applicable, powered cells. With bge/A and
  bge/B absent, family 1's aggregate label is computed from **one cell**: MiniLM / Track A.
- PW-1's primary family would then be a single-embedder, single-track result — which is precisely
  what running two embedders across two tracks was designed to prevent. The second embedder is
  not decoration on this design; it is the control for the possibility that the formatter's
  advantage is an artifact of one encoder's geometry.

**Please verify this before anything else**, because it decides the shape of the problem. The
question is narrow: do the S1/S2/S3 arms for family 1 require encoding, or can they be computed
from anything already persisted for `run-20260726-191447`? Check what that run wrote for the
size-matched control specifically — the arms need per-unit `source_ranges` and the per-query
retrieved-unit lists, not the vectors themselves. If the retrieved-unit lists survive even
though the vectors don't, the arms are re-scorable and (b) really is only a guard-coverage
question. If they don't, (b) is not "family 1 rests on fewer verified cells," it is "family 1
has one cell," and the cost is much higher than you priced it.

I am not certain which it is. You can settle it in a few minutes and it changes my recommendation
only in strength, not in direction.

---

## 2. (c): rebuild the environment that ran bge

The published bge numbers came from `run-20260726-191447`, in an environment that demonstrably
encoded bge to completion on both tracks. You now have that environment pinned — that is exactly
the C-2 item from last step, and you are right that it is what makes this legible rather than
mysterious. But it is more than diagnostic. It is a candidate fix, and it is the only candidate
that costs nothing in interpretation.

A `0xC0000005` access violation that is **cumulative rather than data-dependent**, model-size
dependent, and reproducible across two shells is the signature of a native-layer problem — an ABI
mismatch between `torch` and a compiled dependency, or an allocator/threading-library conflict
(MKL, oneDNN, OpenMP). It is not the signature of a corpus problem, and your diagnosis correctly
ruled out the data-side explanations one at a time. That class of fault is usually version-bound,
which is why the same code ran two days earlier and does not run now.

So: diff this environment against the pin. `torch`, `transformers`, `sentence-transformers`,
`tokenizers`, `numpy`, and the OpenMP/MKL runtime are the ones that matter. If anything moved,
restore the pinned versions in a clean virtualenv and retry unmitigated.

If that works, guard 1 passes on the unchanged path, the arms run on the unchanged path, nothing
is recorded as a deviation, and the decision you asked me to weigh evaporates. That is worth an
hour before accepting a permanent asterisk on two cells.

If it does not work, the diff is still the right thing to record: a blocked cell whose
environment delta is documented is a very different artifact from a blocked cell that just
failed.

---

## 3. If (c) fails: (a), but restructured

I would take (a) over (b) — the cost of (b) is too high, per §1 — but not in the form you
described, because "batch 4, single-threaded, gc between calls" bundles three changes and only
some of them are suspect, and none of them needs to be argued about when all of them can be
measured.

### 3.1 Unbundle. Only one of the three touches batch composition.

- **`gc` between calls** cannot affect numerics. It changes when memory is released, nothing else.
- **Single-threading** can, marginally — intra-op threading changes float reduction order in some
  kernels, so it is not free, but it does not change what any batch contains.
- **Batch size** is the one that changes padding, and therefore the one your instinct is
  correctly flagging.

Test them in that order: gc alone, then gc + single-thread, then add the batch change only if the
first two do not survive. If gc alone holds for 10 minutes where the unchanged path died in one,
you have a mitigation with **zero** numerical surface and there is nothing to record beyond a
note. Given that the fault is cumulative, gc alone is a plausible fix on its own.

Process-sharding is the other zero-batch-change option — encode in fresh subprocesses and
concatenate — and your own diagnosis points straight at it ("the slice that crashed at [144:160]
encodes cleanly when it's the first call in a fresh process"). One caveat that makes it less free
than it looks: `SentenceTransformer.encode` sorts inputs by length before batching and unsorts
afterwards, so sharding changes which texts share a batch unless you replicate the sort over the
full corpus and cut shards at batch boundaries. Doable, but it is fiddly and version-sensitive;
try gc first.

### 3.2 Measure the perturbation on MiniLM, where both paths run.

You have a free control and should use it. MiniLM completes family 1 on both tracks under the
unchanged path and passes exactly. Re-run those same two cells under whichever mitigated path you
end up with, and record three things:

1. Whether the levels still reproduce to the published digit.
2. Max absolute deviation in the embeddings between paths, and the resulting max cosine deviation.
3. Rank churn — how many (query, position) pairs in the top-k differ.

This is evidence, not proof, for bge: different model, different width, different padding
behaviour. But it converts "batch size can perturb padded-attention numerics" from an unmeasured
worry into a measured quantity on this exact pipeline, and if the answer is that MiniLM's levels
are identical and cosine deviation is ~1e-6, the worry is correctly sized rather than dismissed.

### 3.3 Bound it properly with a margin analysis — this is the part that can actually settle it.

`recall@5` is quantised on a 1/176 grid and depends only on **ranking**, not on scores. A
perturbation of magnitude ε can only change the metric if it flips a rank across the k=5
boundary, which requires two candidates separated by less than ~ε in fused score.

So compute, on bge, the distribution of the **rank-5 / rank-6 gap** per query. You can do this on
the cells that re-scored cleanly — family 2 bge/A and secondary bge/B — because their retrieval
results are persisted. If the minimum gap across queries is orders of magnitude larger than the
cosine deviation measured in §3.2, then no rank can flip and `recall@5` is invariant to the
perturbation **as a bound, not as an observation.** That turns the deviation from something you
accept into something you have shown cannot matter at this metric's resolution.

Note the RRF fusion helps you here: `k_rrf = 60` maps scores to rank-derived contributions, so a
perturbation must move a *rank* in the dense list before it can move the fused list at all. The
margin argument therefore applies at the dense-rank level, which is where it is easiest to check.

### 3.4 One consequence to anticipate, because it can produce a false halt

If the arms run under a mitigated path while `delta_full` is a stamped input from the unmitigated
published run, then `r = delta_corrected / delta_full` has a numerator and a denominator computed
under different embedding paths. Any path difference enters `r` directly.

On the 1/176 grid a single flipped query moves a delta by 0.0057, which on family 1 bge/A
(`delta_full` = 0.1477) moves `r` by about 0.039. That is small against the 0.75 and 0.25 band
boundaries but not invisible. The sharper risk is the A7 halt: if the mitigated path yields one
*more* hit than the published path on an S2 arm, `r` can exceed 1.0 and stop the run for a reason
that has nothing to do with scoring — the exact false halt the guard is not meant to produce.

So if you go this route, decide **now**, before the arm runs, that an `r > 1.0` on a mitigated-path
cell is investigated as a path artifact first and a scoring defect second, and write that into
the halt's handling. Do not let it be decided in the moment by whoever is looking at the traceback.
The stamped rule stays as it is; what you are adding is a diagnostic order for one specific,
foreseeable case.

### 3.5 Label the result honestly

If a mitigated run reproduces, the cell is not "PASS". It is **PASS UNDER DECLARED DEVIATION**,
with the deviation named, the mechanism recorded, and the §3.2/§3.3 measurements attached. A
distinct label matters because a reader scanning a column of PASSes should not have to read the
footnotes to learn that two of them mean something weaker. That is the same principle as
`family_2_labels_carry_a_qualifier`: the qualifier travels with the label, not in a note beside it.

---

## 4. Your checker bug, and the pattern it makes

Differencing rounded levels and comparing to a delta that was rounded once is a clean instance of
a general rule: **compare at full precision, round exactly once, at the point of display.**
147/176 − 139/176 = 8/176 = 0.045454…, and there is no ordering of round-then-subtract that is
safe in general.

The halt was correct behaviour and you read it correctly — it caught the checker, not the data.
But I want to name the near-miss, because it is the third checker defect in two steps and they
are starting to form a shape.

The first (guard 4) scanned only the top 5 and reported a rate. The second (this one) rounded
before differencing. In both cases the checker was less reliable than the thing it was checking,
and in both cases discovery was partly luck: here, *"three of the four cells coincided, so only
one surfaced it."* Consider the counterfactual where the arithmetic had coincided on all four.
The checker would have reported four passes, would have been trusted, and would have been carried
forward into B5 — where the arms produce deltas on a different scale and the same bug would bite
somewhere less visible.

That is §A1b, applied one level up. The template already requires every guard to be demonstrated
failing against a deliberate violation. The guards' **checkers** are not currently held to that,
and they should be: for each checker, feed it a synthetic cell that is wrong by exactly one query
on the grid and confirm it halts. A checker that has only ever been observed agreeing is
indistinguishable from a checker that agrees by construction.

Combined with the guard-4 lesson from last step — a guard whose correct behaviour is exact
equality must assert equality, never report a rate — that gives two checker rules worth adding to
the template beside §A1b.

---

## 5. On the escalation question

Your reading is right, and I would keep it. `guard_1_escalation` covers failing to regenerate a
published number; here no number was produced, and the difference is real rather than lawyerly —
a mismatch is evidence about the analysis, an environment failure is evidence about the machine.
The published bge retrieval is independently corroborated by the two composition cells that
re-scored exactly, and re-scoring never touches the embedder, so nothing about bge's published
retrieval is in question.

One addition: record it as an explicit halt class — `BLOCKED / ENVIRONMENT`, with the diagnosis,
the attempt count, and the environment diff from §2 — rather than as an absence. Cells that were
attempted and blocked and cells that were never attempted look identical in a table that only
records passes, and six weeks from now nobody will remember which these were.

---

## 6. Recommendation, in order

1. **Settle §1.** Do the family-1 bge arms need encoding, or are they re-scorable from what
   `run-20260726-191447` persisted? This decides whether (b) is even on the table.
2. **Try (c).** Diff against the C-2 pin, restore the pinned versions in a clean environment,
   retry unmitigated. Best case: exact reproduction, no deviation, no decision.
3. **If (c) fails, take (a) restructured.** gc alone → gc + single-thread → batch change, in that
   order, stopping at the first that survives. Measure on MiniLM (§3.2), bound with the rank-5/6
   margin analysis (§3.3), pre-decide the `r > 1.0` diagnostic order (§3.4), and label the cells
   PASS UNDER DECLARED DEVIATION (§3.5).
4. **Take (b) only if both fail**, and if you do, say plainly in the results document that family
   1's aggregate rests on a single applicable cell. That is a real result and it can be reported
   honestly — but it must be reported, not left to be inferred from a table of eight rows where
   two are blank.

B3's outcome is unaffected by all of this, and the two pre-arm code items from the last check
(the NOT APPLICABLE halt gap, and now the checker tests in §4) can proceed in parallel with the
environment work.
