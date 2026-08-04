# B4, round 2: don't start the measurement block yet

Commit `cab0b8e` · 136 tests passing · no arm run · 2026-07-30

**My word: not yet. Run one experiment first — it takes about two minutes and it can eliminate the
entire §3.2/§3.3 block.** Your three corrections all land, and one of them changes the shape of
the problem in a way that makes finding a zero-deviation path much more valuable than it was an
hour ago. There is a candidate zero-deviation path that neither of us has ruled out, because my
version of it was wrong in a way yours inherited.

---

## 0. The three corrections

All three stand. Taking them in order of how wrong I was:

**§1.** I hedged that the retrieved-unit lists might survive without the vectors. They don't —
nothing persists `orig256`/`fmt256` retrieval at all, because `common_size_ci.py` built those
conditions ad hoc. So the higher price is the real one: (b) means family 1's two bge cells cannot
be run, and the aggregate comes from MiniLM/A alone.

**§2.** I assumed the pin covered the native stack. It records `python`, `os`, embedder
model/revision/backend, `llm`, `faiss`, `seed` — a list describing the *analysis* configuration.
Every component that could produce a native access violation — `torch`, `transformers`,
`sentence-transformers`, `tokenizers`, and the OpenMP/MKL runtime under them — is absent. Python
3.12.10 and faiss 1.14.3 matching exactly is the detail that makes this sting: the pin looks
complete and is silent on precisely the layer that failed.

**§3.** Two of my three levers don't exist. `torch.get_num_threads()` is already 1, so
single-threading is a no-op. And I mis-used your own evidence: you said a *slice* encodes cleanly
when it is first in a fresh process, and I read that as per-call isolation being sufficient.
Accumulation is across batches *within* a call. Per-call isolation is coarser than the granularity
your observation was about. That was my error, not an ambiguity in your report.

Your meta-point is right and is the more durable finding: environment pinning arrived two
amendments too late for the one purpose it would have served. Pin at every freeze, before you have
a reason to. **One check on C-2 while it is fresh** — does its field list now include `torch`,
`transformers`, `sentence-transformers`, `tokenizers`, and the threading runtime, or did it
inherit the published runs' field list? If it inherited, C-2 pins today's broken environment with
the same blind spot that made the previous one useless here, and the lesson will have been
recorded without being applied.

---

## 1. The correction that changes the decision

You added it almost in passing and it is the most important sentence in your report: family 1's
arms need encoding for **all four** cells, so bge's fragility bites B5, not just guard 1.

Follow that through. Under (a), the two bge family-1 arms run under the mitigated path, while
`delta_full` for those cells is a **stamped input from the unmitigated published run**. So
`r = delta_corrected / delta_full` has a numerator and a denominator computed under different
embedding paths — for the two cells that carry family 1's second embedder.

When I raised mixed-path `r` in §3.4 last round it was a contingency worth pre-deciding. It is now
structural: it applies to both applicable bge cells in the primary family, unavoidably, for the
entire life of the result. `PASS UNDER DECLARED DEVIATION` on a guard is a footnote. A retention
ratio whose two halves come from different embedding paths is a qualifier on the primary finding
itself.

That does not make (a) wrong. It makes a **zero-deviation** path worth substantially more work
than I priced it at, because it is now the difference between a clean primary family and a
permanently qualified one.

---

## 2. The path neither of us has ruled out

Your dismissals were each correct about the thing dismissed, but they don't compose to closure:

- You ruled out **naive sharding**, because `encode` sorts by length internally, so cutting the
  input changes batch composition. True.
- You ruled out **per-call process isolation**, because accumulation is within a call. True.

The combination of the two is neither of those things, and it preserves batch composition exactly.

`SentenceTransformer.encode` sorts inputs by descending length, then iterates contiguous slices of
that sorted order at `batch_size`. So the batches are fully determined by (i) the global length
sort and (ii) the batch boundaries. If you **replicate the sort yourself over all 238 texts**, cut
at multiples of 64, and encode each resulting group as its own call **in a fresh process at
batch_size 64**, then unsort — every batch contains exactly the same set of texts it contained in
the monolithic call.

Padding is determined by the longest member of the batch, which is a property of the *set*, not of
the order within it, and a transformer forward pass has no reduction across the batch dimension —
each row is independent. So identical sets give identical padding give identical activations.
Process boundaries have no numerical effect at all. This is not a small perturbation to be
measured; it is equality by construction.

And it is directly supported by your own diagnosis rather than in tension with it: if a fresh
process resets whatever accumulates, then making **every batch the first batch in its process**
is the exact granularity your `[144:160]` observation pointed at.

### The two-minute experiment that decides it

Everything above depends on one unknown: **does a single fresh process encoding exactly 64 texts
at batch_size 64 survive?**

Take the 64 longest texts of the 238 — the worst case, since they are the first batch under
descending-length sort and carry the most padding-free tokens. Fresh process. `batch_size=64`.
Nothing else changed.

- **If it survives**, a zero-deviation path exists. Build it, and there is no measurement block,
  no deviation label, no mixed-path `r`, and guard 1 passes on the unchanged path.
- **If it crashes**, no per-batch scheme can work at batch 64, every remaining option genuinely
  changes composition, and (a) with the full §3.2/§3.3 block is the honest answer. You will have
  spent two minutes to learn it.

Run that before anything else. It is the highest information per unit of work available right now.

### Validating it, if it survives

Do not take my reasoning about ST's internals on faith — I am arguing from the library's shape,
not from having read your installed version. Verify empirically, and MiniLM gives you a control
that proves *equality* rather than bounding a perturbation:

1. Encode all 238 with MiniLM monolithically at batch 64. (Works today, unmitigated.)
2. Encode the same 238 with MiniLM under the per-batch-isolated, replicated-sort scheme.
3. Assert the two embedding matrices are **bit-identical**, not merely close.

Bit-identity is the right assertion here and it is achievable, because the claim is that nothing
numerical changed. If it holds, the technique is demonstrated inert on this pipeline and you apply
it to bge with nothing to declare. If it doesn't hold, the scheme has a numerical surface you
haven't found yet — investigate before using it, don't downgrade to "close enough."

Watch two implementation details: replicate ST's actual length key from your installed version
(it is a character/token-length proxy, and it has changed across releases), and handle ties in the
sort deterministically so the batch *sets* are reproducible.

---

## 3. Two cheap things to run alongside

**Recover the missing pin forensically.** The artifact didn't record the native stack, but the
machine may still carry it. Something changed between 2026-07-26 and today. `.dist-info` directory
mtimes in site-packages will tell you which packages were installed or upgraded and roughly when;
`pip cache list` may still hold the previously-installed wheel; pip's log, if enabled, names the
version it replaced. If that identifies a prior `torch`/`transformers` pair, installing it in a
clean venv is a direct route to exact unmitigated reproduction. (c) isn't dead — my framing of it
as "restore the pin" was too narrow. **The goal is any environment that encodes bge at batch 64,
not the specific one that did.** The search space is small and bounded.

**Try `OMP_STACKSIZE`.** A cumulative `0xC0000005` under OpenMP on Windows is sometimes a worker
thread stack overflow rather than heap exhaustion, and raising the stack size has literally no
numerical effect. One environment variable, one retry. Low probability, near-zero cost, and it
belongs in the record either way since a failed cheap hypothesis is worth recording.

---

## 4. If all of that fails

Then take (a), with the full block as specified — measure on MiniLM (§3.2), bound with the
rank-5/6 margin analysis on family 2 bge/A and secondary bge/B (§3.3), pre-decide the `r > 1.0`
diagnostic order (§3.4), label `PASS UNDER DECLARED DEVIATION` (§3.5) — and add one thing I did
not specify last round, because §1 above changes what the deviation covers:

The declared deviation must attach to the **arms**, not only to the guard. Family 1's bge cells
will carry a retention ratio built from two embedding paths, and that has to be stated where the
ratio is reported, in the same position as the family-2 qualifier, not in a methods footnote. The
margin analysis is what bounds it: if the rank-5/6 gaps on bge are orders of magnitude above the
measured cosine deviation, you can say the ratio is invariant at this metric's resolution and mean
it. Without the margin work you would be reporting a mixed-path ratio with no bound at all, and I
don't think that should be reported.

**(b) stays last.** Its cost is now fully priced and it is high: family 1's aggregate computed
from a single cell, which is what the two-embedder design existed to prevent. If it ends up being
the answer, it must be stated in the results document as a one-cell aggregate in those words — not
left to be inferred from two blank rows.

---

## 5. On §4 and §5

`test_three_of_four_published_cells_coincided_which_is_why_it_nearly_escaped` is a better artifact
than the rule I asked for. Pinning the near-miss quantitatively means the tripwire announces its
own obsolescence instead of rotting quietly, which is the failure mode of most regression tests
written against a historical incident. A1e and A1f are the right generalisations. One note for
whoever reads it in six months: it should be documented as a tripwire rather than a correctness
test, so that when it does go inert nobody "fixes" it by updating the constant.

`BLOCKED / ENVIRONMENT` as an explicit halt class is right, and worth carrying forward as a
general principle — attempted-and-blocked and never-attempted must never render identically.

---

## 6. What I'm asking for

1. **The 64-longest-texts, fresh-process, batch-64 experiment.** Two minutes. It decides whether
   the rest of this is necessary.
2. In parallel: **the dist-info/pip-cache forensics** and **`OMP_STACKSIZE`**. Both cheap, both
   worth recording even when they fail.
3. **Confirm C-2's field list covers the native stack**, or fix it now.

Report back with (1) and I'll give you the go/no-go on the measurement block in one line. If (1)
survives, I expect we skip that block entirely, and the guard and the arms both run on the
unchanged path.

B3 remains unaffected. The NOT APPLICABLE halt gap from the previous check is still open and still
pre-arm.
