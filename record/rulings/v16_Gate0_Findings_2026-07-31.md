# v1.6 — Gate 0 findings

**Date:** 31 July 2026 · **Status:** §12 step 1 complete. **Nothing else has been done.**
No plan, no pre-registration, no script, no arm. **Two gates contradict the handover and I am
waiting**, per §3: *"your reading wins and you must flag the contradiction to Shamik before
freezing anything."*

Every answer below is from source or artifact, with file and line. Nothing is from memory or from
the handover.

---

## Summary

| # | Verdict | One line |
|---|---|---|
| G1 | **CONFIRMED** | C3's published corpus used `soft_target_tokens` **768**, not the 384 in its YAML |
| G2 | **CONFIRMED — the concern is real** | The published C0 **overlap is not recoverable**. Halt condition 7 applies |
| G3 | **CONFIRMED** | The control builds a formatted corpus at 384 — **a different corpus from published C3** |
| G4 | **CONFIRMED** | The C3-* ablations inherit C3's swept 768 |
| G5 | **CONFIRMED genuine** | Not a copied field — `token_mean` differs across the eight 90-unit conditions |
| G6 | **✗ FAILS — 10/10 documents** | But the cause is **whitespace only**. No word is changed. See below |
| G7 | **✗ CONTRADICTS the handover** | SEAM as specified would make **45 fresh LLM calls** on Track A |
| G8 | **CONFIRMED** | Formatter units carry own + absorbed only. No inheritance |

---

## G1 — C3's published soft-target was 768 ✓

`src/run.py:46-48` — `NO_SWEEP_PARAMS = {..., "C3": {"soft_target_tokens": 768}}`.
`src/run.py:126-127` — the live sweep ranges over `sweep.formatter_soft_target`.
`rag-formatter-results.zip::results.json` → `chosen_chunk_sizes = {"C0": 768, "C1": 512, "C3": 768}`.

`config/conditions/C3.yaml` declares 384 and is overridden. The handover is right.

## G2 — the published C0 overlap is NOT recoverable ✓ (concern confirmed)

`chosen_chunk_sizes` records **sizes only**: `{"C0": 768, "C1": 512, "C3": 768}`. There is no
overlap field anywhere in the published `results.json`, and `tracks_meta` carries only
`track, n_test, faithfulness, llm_cost, readability, common_size, llm_model`.

`src/run.py:118-121` shows C0's sweep ranged over `baseline_chunk_tokens × baseline_overlap_frac`,
so an overlap *was* chosen — it was simply never written down.
`NO_SWEEP_PARAMS` records `overlap_frac: 0.0`, but that is the **replay** value, not evidence of
what the live sweep picked.

**→ Halt condition 7 applies.** Do not use published C0 as a comparator. Run our own U768 arm and
record that we did. This is also a finding worth carrying: a swept parameter that changes the
result was not persisted with the result.

## G3 — the control's formatted corpus is not C3's ✓

`src/run.py:312-333`, `_common_size_control`:

```python
fmt = build_chunker({"id": "fmt256", "chunker": "formatted_naive",
                     "params": {"chunk_tokens": 256, "overlap_frac": 0.0,
                                "reference_resolution": True, "dedup": True,
                                "right_size": True, "soft_target_tokens": 384}}, ctx)
```

`soft_target_tokens: 384` is **hardcoded**, then re-chunked at 256/0.0. Published C3 used 768. So
the control's formatted corpus is segmented differently from the corpus C3's headline number
describes. The handover is right, and its §2 third point stands: the docstring claims to isolate
"text-quality from unit-count" and isolates chunk size instead.

## G4 — ablations inherit C3's swept size ✓

`src/run.py:230-232`:
```python
elif cid.startswith("C3-"):
    st = chosen_sizes.get("C3", 384)
    cond_cfg["params"] = {**cond_cfg.get("params", {}), "soft_target_tokens": st}
```
So C3-nosize ran at 768. Its 1552 units come from `right_size: False`, not from a size difference.

## G5 — the 90s are genuine ✓

Track A, published, `chunk_stats.index_units` with `token_mean` beside it:

| condition | units | token_mean |
|---|---|---|
| C0 | 90 | 609.84 |
| C2 | 90 | 659.91 |
| C3 | 90 | 583.52 |
| C4 | 90 | 583.52 |
| C5 | 90 | 633.19 |
| C3-noref | 90 | 582.21 |
| C3-nodedup | 90 | 612.44 |
| C3-markeronly | 90 | 609.84 |
| C1 | 354 | 155.05 |
| C3-nosize | 1552 | 33.84 |

Eight identical unit counts with **eight different token means** is not what a copied field looks
like. The handover was right to ask.

*(`units_per_doc` is `None` in the published JSON; the handover's 2.0 is 90/45 and is correct as
arithmetic, but it is derived, not stored.)*

## G8 — no inheritance in formatter units ✓

`src/chunkers/formatter.py:306-313`, `_emit`: `raw = [(st.start, st.end) for st in g]` then
`raw.extend(st.absorbed)`. Own + absorbed, nothing else. Measured over Track A:

| arm | units | claimed chars | own text | width |
|---|---|---|---|---|
| SEAM (no dedup) | 90 | 367,729 | 372,939 | **0.9860** |
| FULL (dedup on) | 90 | 367,729 | 361,319 | **1.0177** |

Both ≈ 1.0. The inheritance channel is `src/chunkers/formatted.py:86-94`, which **no v1.6 arm
exercises** — confirming PW-1's finding that C3 shows no inflation.

---

# The two contradictions

## G6 — the verbatim-partition gate FAILS, and the cause is whitespace

**10 of 10 Track A documents fail both halves**, with `reference_resolution: False`,
`dedup: False`, on the rule-based path.

First divergence, `A-000-kestrel-indexer` at character 17:

```
concatenated : '# Kestrel indexer The Kestrel indexer'
original     : '# Kestrel indexer\n\nThe Kestrel indexe'
```

**Cause, and it is one line.** `src/chunkers/formatter.py:302` — `_emit` builds unit text as
`" ".join(st.text for st in g)`. Original inter-sentence separators — `\n\n`, indentation,
multiple spaces — are normalised to a single space. Separately, `sentence_spans` returns sentence
extents only, so `source_ranges` cover **367,729 of 378,239 characters (97.2%)**; the missing
10,510 are inter-sentence whitespace. Ranges do **not** overlap (0/10) — the partition is
non-overlapping but neither exhaustive nor byte-verbatim.

**What this does and does not mean, stated precisely because §15 invites over-reading.**

- **No word, identifier, number or domain term is changed.** The standing editorial rule is not
  violated. `do_ref` and `do_dedup` are both False on this path, so `st.text` is never reassigned
  and `st.kept` is never cleared. The failure is entirely in the *join separator* and in
  whitespace that no sentence span claims.
- **Scoring is not broken by the coverage gap.** Gold spans are character ranges; a span crossing
  two sentences still overlaps both sentences' ranges, and `is_hit` uses ANY-overlap with
  `min_overlap = 1`. A gold span lying *entirely* inside inter-sentence whitespace is not a
  meaningful annotation.
- **But the embedded text does differ from the original**, because embedding runs on
  `unit.text` and that text has normalised whitespace. SEAM is therefore "unedited vocabulary
  with normalised whitespace", not "change no character at all".

So §15's framing — *"if it does not pass trivially, that is itself the most important thing this
experiment will have found"* — **overstates this particular failure**, and I would rather say so
than let a whitespace artifact be recorded as a guardrail breach. It is a real blocker for the
gate **as literally specified**, and it is not evidence that the formatter edits vocabulary.

**Three ways forward, all yours to choose:**

1. **Weaken the gate to what the arm actually needs** — assert the concatenation matches the
   original *after whitespace normalisation on both sides*, and that `source_ranges` cover every
   non-whitespace character exactly once. This is the assertion that tests "no vocabulary
   changed", which is the property SEAM depends on.
2. **Make `_emit` separator-faithful** — reconstruct units by slicing `doc.text` between sentence
   boundaries instead of joining. That would make the gate pass literally, but it **changes the
   production formatter's output** and therefore is not something I would do inside an experiment
   that is meant to observe it.
3. **Halt v1.6.** Defensible under a strict reading and, in my view, disproportionate to a join
   separator.

I recommend (1) and have not implemented anything.

## G7 — SEAM as specified would make 45 fresh LLM calls on Track A

`src/chunkers/formatter.py:184`:

```python
if self.llm is not None and not self.llm.is_none and not p.get("markers_only"):
    return self._chunk_llm(doc)
```

The LLM path is gated on **`markers_only`** — **not** on `reference_resolution` or `dedup`. The
SEAM arm sets neither, so it takes the LLM path, and `_chunk_llm` calls
`self.llm.complete(prompt, system=sys)` **unconditionally**, before any operation is applied.

Worse, the system prompt is built by `formatter_system_prompt(do_ref, do_dedup, do_identity)`
(`src/chunkers/prompts.py:35-49`), whose `ops` list is **empty** when both are False. That is a
different system prompt, hence a different cache key. Measured against `cache/llm`:

| prompt | cached, of 45 Track A docs |
|---|---|
| FULL family (`ref + dedup`) | **45 / 45** |
| SEAM family (neither) | **0 / 45** |

**→ SEAM as written triggers 45 fresh LLM calls on a track that declares
`requires_llm: false`** (`config/tracks/A.yaml`, `params.requires_llm`). That is **halt condition
5**, and it would also make SEAM's segmentation depend on a model response that was never needed.

**Two fixes, both one line, both yours:**

1. **`markers_only: True`** on the SEAM arm. `_chunk_rulebased` (`formatter.py:204-205`) computes
   `do_ref` and `do_dedup` as `params.get(...) and not markers_only`, so this forces the
   deterministic path *and* disables both operations — exactly SEAM's intent, with no LLM call.
   Note it also implies `boundary_markers` handling; verify the emitted text is unaffected.
2. **Build the SEAM arm with an `is_none` LLM.** Cleaner semantically, but it needs a separate
   `ChunkContext`, and mixing two contexts in one script is a footgun.

I recommend (1), and I verified G6 above using the rule-based path precisely so the two questions
stayed separate.

---

## Two smaller notes, not gates

**The decomposition identity is sound.** `D_size + D_seam + D_edit = (U(m) − U256) + (S(m) − U(m))
+ (F(m) − S(m)) = F(m) − U256 = D_total` telescopes by construction. §10's halt 3 will hold
trivially on point estimates; it is still worth asserting, since it would catch an arm being
mislabelled.

**FULL is fully cache-served.** The system prompt does not depend on `soft_target_tokens`, and the
user prompt depends only on the document's sentences — so `F384` and `F768` share `C3`'s cache
entries. 45/45 cached. No LLM spend for the FULL family on Track A.

---

## What I have not done

No plan. No `preregistration_v16.json`. No `tests/test_v16_seam_partition.py`. No
`scripts/segment_size_sweep.py`. No arm value, no run, no output directory. Nothing under
`results/`, `results_pw1/`, `posthoc_PW1_*` or any `preregistration_*.json` was opened for writing
or modified.

**Waiting on G6 and G7.**

---

# Gate 0, round 2 — G7 resolved, G10 resolved, G2 recovered, **G9 CONTRADICTS**

**31 July 2026, after `Decisions_v16_Gate0_2026-07-31.md`.** Still no plan, no
pre-registration, no script, no arm value.

## G7 — `markers_only: True`, and it injects nothing ✓

`markers_only` appears at exactly four lines of `src/chunkers/formatter.py` — 184 (forces the
deterministic path), 204 and 205 (`do_ref` / `do_dedup` both become False), and 243 (forces
`_right_size`). **No code path injects a marker string into `Unit.text`**; `boundary_markers` is
never read in `formatter.py` at all. So the first branch of the ruling applies: **use
`markers_only: True`**, and the arm's behaviour stays visible in its declared parameters.

Note the side effect, which is load-bearing for G10: **line 243 forces right-sizing even when
`right_size: False`.**

## G10 — SEAM *is* the published `C3-markeronly` ✓

`config/conditions/C3-markeronly.yaml` declares exactly the SEAM parameter set —
`markers_only: true`, `reference_resolution: false`, `dedup: false` — and `run.py:230-232`
overrides its `soft_target_tokens` to C3's swept **768**. Rebuilt at that inherited size:

| | units | token_mean |
|---|---|---|
| rebuilt SEAM(768) | **90** | **609.84** |
| published `C3-markeronly` | **90** | **609.84** |

**`S768` is already published, at recall@5 = 0.7955.** Reason 2 of the ruling therefore holds: the
published table contains an approximate decomposition at 768 under recall@5 —
`U768 = 0.7841`, `S768 = 0.7955`, `F768 = 0.8182`, i.e. seam ≈ **+0.011** and edit ≈ **+0.023**.
Both small, both in the direction P3 and P4 predict. `prior_knowledge_at_freeze` must record this.

## G2 — the overlap IS recoverable, by arithmetic ✓ VERIFIED

Not from a stored field, but from a conservation identity. `count_tokens` over the raw Track A
documents gives **54,886** tokens. Published C0 is 90 units at `token_mean` 609.84 =
**54,886** indexed tokens. Ratio **1.0000**.

Overlap > 0 indexes the overlapped span twice, so the ratio would exceed 1. It does not, to four
decimal places. **Published C0 used `overlap_frac = 0.0`**, and it therefore *is* `U768`.

Halt condition 7 does not fire. I would still run our own U768 arm — it is nearly free and keeps
every arm inside one run — but the published C0 is now a legitimate cross-check rather than an
unusable comparator, and the finding is worth carrying: *a swept parameter was not persisted, and
was recovered only because the metric happened to admit a conservation check.*

## G9 — **CONTRADICTS. Stopping, per the order of work, step 4.**

**The claim to verify:** right-sizing is deterministic and applied after the LLM stage, so SEAM
and FULL share a segmentation engine and differ only in input text.

**Half of it is true.** `_chunk_llm` calls `complete()` at line 345 and `_place_boundaries` at
385, and `_right_size` (268-269) is pure arithmetic over `soft_target_tokens`. The LLM does not
choose boundaries.

**The consequence does not follow, and it is what matters.** `_right_size` groups `kept`
sentences by `count_tokens(st.text)` — and the LLM sets *both* inputs: reference resolution
rewrites `st.text` (lengthening it), dedup clears `st.kept` (removing sentences from the
sequence). Boundary placement is deterministic **given** the sentence list; the LLM supplies the
sentence list.

**Measured, not argued** — SEAM(768) against FULL(768) over all 45 Track A documents:

| | |
|---|---|
| documents with identical boundaries | **0 / 45** |
| units | SEAM 90, FULL 90 |

Example, `A-000-kestrel-indexer`: SEAM cuts at `[(0, 5329), (5331, 7706)]`, FULL at
`[(0, 5612), (5614, 7706)]` — the interior boundary moves **283 characters**.

**So `D_edit = F(m) − S(m)` is not a clean editing contrast.** It confounds the edits with the
boundary shift those edits cause. The decomposition's decision-bearing quantity is the one
affected. This is exactly the case the ruling reserved: *"if it turns out the LLM does influence
segment boundaries, tell me before writing the plan; the decomposition needs a fourth arm and I
would rather redesign than caveat."*

Labelled **HYPOTHESIS → FALSIFIED** per A1g.

### One observation for the redesign, offered but not acted on

The boundary shift is a *downstream consequence* of editing, not an independent variable — you
cannot edit the text and hold the cuts fixed without choosing which to privilege. A fourth arm
would have to pin one of them:

- **F(m) with SEAM's boundaries** — edit the text, then cut at the positions SEAM chose. Isolates
  editing at fixed seams, but the seams are then wrong for the edited text.
- **S(m) with FULL's boundaries** — unedited text, cut where the edited text made the formatter
  cut. Isolates seam placement, but the boundaries are informed by edits the arm does not have.

Both are constructible from existing machinery. Neither is obviously the right one, and choosing
is a design decision, not an implementation one — which is why this is where I stop.

---

# Gate 0, round 3 — steps 1–4 of the post-G9 order. No stop warranted.

**31 July 2026, after `Decisions_v16_Gate0_Round2_2026-07-31.md`.** Still no plan, no
pre-registration, no sweep script, no arm value. Nothing scored, retrieved or embedded.

## Step 1 — `F@S` is constructible exactly as specified ✓

`src/v16/regroup.py`. FULL's kept sentences are captured at `_emit`, assigned to the SEAM
segment containing the start of each sentence's first source range, concatenated in order within
each segment, and emitted through **FULL's own `_emit`** — so unit `source_ranges` are the union
of their sentences' ranges by the same rule FULL applies, and the scorer sees nothing new in kind.

No substitution was needed. The assignment rule is the arm definition and it is implemented as
written.

## Step 2 — the regrouping gate passes, and there are no empty segments ✓

`tests/test_v16_fas_regrouping.py`, all 45 Track A documents at m = 768:

| | |
|---|---|
| regrouping gate (pure re-grouping of `F`) | **45 / 45 PASS** |
| `F@S` units | **90** |
| SEAM segments | **90** |
| **empty segments** | **0** |

Dedup emptied no SEAM segment on this corpus, so nothing had to be reported-and-not-forced. The
gate is demonstrated failing in both directions (§A1b) — a dropped unit and a duplicated one —
so a passing result is evidence rather than a green light.

Also pinned: `F@S` differs from `F` on **45/45** documents. Had it not, `D_reseam` would be zero
by construction wherever they agreed.

## Step 3 — the weakened three-part G6 passes under the final SEAM configuration ✓

`tests/test_v16_seam_partition.py`, run under `markers_only: True` — the arm that actually runs,
not the rule-based probe used in round 1.

| Part | Result |
|---|---|
| 1. whitespace-normalised equality | **PASS**, all 45 documents |
| 2. every non-whitespace character covered exactly once | **PASS**, all 45 |
| 3. non-overlap | **PASS**, all 45 |
| **gold-span overlap** | **PASS** — every gold span in the Track A test set overlaps ≥ 1 SEAM range |

The gold-span assertion converts round 1's argument into a check. It was HYPOTHESIS; it is now
**VERIFIED**. Part 1 is demonstrated failing against a single substituted word, and the gate is
re-checked at m = 384 so the partition property does not depend on the size dial.

## Step 4 — G2 tightened to integer token counts ✓ **VERIFIED**

Redone per A1f, with no rounded quantity anywhere in the inference:

| arm | units | indexed tokens | residual vs corpus | ratio |
|---|---|---|---|---|
| corpus (integer sum over raw docs) | — | **54,886** | — | — |
| U768 @ overlap **0.0** | **90** | **54,886** | **+0** | **1.000000** |
| U768 @ overlap 0.1 | 91 | 58,428 | +3,542 | 1.064534 |
| U768 @ overlap 0.2 | 95 | 62,586 | +7,700 | 1.140291 |

Published C0 is **90 units**. So the inference no longer rests on the token identity alone —
**the unit count discriminates independently**: 90 matches overlap 0.0 and not 0.1 (91) or 0.2
(95). Two signals, both exact integers.

The earlier `90 × 609.84 = 54,885.6` gave a −0.4 residual; that was the printed mean's rounding,
not the data's. It is superseded by the integer identity above.

**Assumptions, stated as the ruling requires:** (a) one tokenizer, `src.textutil.count_tokens`,
on both sides; (b) the naive chunker adds and drops no text, so indexed tokens equal corpus
tokens exactly at overlap 0 and exceed them otherwise; (c) no other pipeline stage could add or
drop text and coincidentally restore a ratio of exactly 1.000000 *and* a unit count of exactly 90.

**Published C0 is `U768` with `overlap_frac = 0.0`.** It is a **reproduction target**, not a
comparator: every decomposition term will be computed from arms run inside this experiment.

## What is still not done

No `Experiment_Plan_v1.6_SegmentSize.md`. No `preregistration_v16.json`. No
`scripts/segment_size_sweep.py`. No output directory. No arm value. Nothing under `results/`,
`results_pw1/`, `posthoc_PW1_*` or any `preregistration_*.json` was opened for writing.

Steps 5–7 remain: write the plan and the pre-registration with `prior_knowledge_at_freeze`
populated, commit them and record hash and timestamp, then the script, then the primary cell.
