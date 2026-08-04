# PW-1 — provenance-width separation: step 0 (descriptive)

**Computed 2026-07-30T08:29:01Z. Artifacts: `results_pw1/step0.json`.**
**Status: step 1 of the order of work. No arm has been run. No p-value, delta, or
classification has been computed on any arm.** Reported here before the freeze file is written,
as instructed.

---

## 0. What this analysis is, and what its integrity property is

This analysis is **post-hoc**: the retrieval data it re-scores were observed before it was
designed. Its integrity property is that the subset definitions, the arms, the metric, the family
and the interpretation rule are frozen before any outcome under them is computed — **not** that
the data were unseen. It is not a pre-registration and must never be filed as one. It is not a
chain entry.

**Step 0 was computed under an earlier version of the instructions, and its results changed the
arm definitions before any arm was run.** Specifically: step 0a measured the absorption channel
at 0.21–3.42% of claimed surface, and step 0c measured a larger chunk-to-segment inheritance
channel. The originally specified arm (now **Arm 2a**) removes only the first. A tight-provenance
arm (**Arm 2b**) removing both was added and made primary in response to those measurements.

Step 0 quantities are properties of the corpus and the gold set, not of any retrieval outcome, and
no p-value, delta or classification had been computed on any arm at the time the change was made.
Stated here rather than left for a reader to reconstruct: a design change made after a measurement
reads differently when it is disclosed than when it is discovered.

---

## PW1-F1 — the white paper names the wrong mechanism

**This finding holds whatever the arms return, and it is worth more than either arm's p-value.**

The paper's §11 threats paragraph attributes provenance width to a specific mechanism: because the
pass merges restatements, a formatted unit carries the character ranges of every duplicate it
absorbed. Measured:

| | absorbed surface | share of sentence surface |
|---|---|---|
| Track A | 12,591 chars | **3.42%** |
| Track B | 2,919 chars | **0.21%** |

**The mechanism named in print is not the mechanism that dominates.** The width is real and large —
2.3× — but it comes from **chunk-to-segment range inheritance**, which the paper does not mention.
A 256-token chunk cut over the formatted text inherits the *entire* `source_ranges` of every
~384-token formatter segment it overlaps ([formatted.py:86-94](src/chunkers/formatted.py#L86-L94)),
which is why one chunk carries 51 ranges on Track A.

The decomposition, per chunk, summed over the corpus:

| fmt256 | claimed | tight (own sentences) | excess = claimed − tight | of the excess, absorbed |
|---|---|---|---|---|
| Track A | 838,499 | 368,066 | **470,433 (56.1% of claimed)** | 12,454 → **2.6%** |
| Track B | 3,369,209 | 1,595,310 | **1,773,899 (52.7% of claimed)** | 2,973 → **0.17%** |

Over 97% of the excess is inheritance, not absorption. At the *formatter* level there is no
inflation at all: C3 units claim 367,656 chars against 367,729 of own-plus-absorbed sentence
surface (Track A), agreeing to under 0.02%. The width is created by the **re-chunking stage**, not
by the formatter.

This is a correction to the paper that is independent of every arm. The §11 rewrite still waits.

---

## Step 0a / 0c — the width statistic

**The statistic (§3a), stated precisely.** Per corpus, per track: the union of each unit's
`source_ranges` in original-document characters, summed over units, divided by the units' own
size. The denominator is given **both** ways, because the earlier 0a figure used the second:

| Track A | units | claimed chars | per own **token** | per own **char** | ranges/unit |
|---|---|---|---|---|---|
| orig256 (unformatted) | 238 | 378,041 | 6.8877 | **1.0000** | 1.00 |
| fmt256 (formatted) | 235 | 838,499 | 15.9662 | **2.3182** | 51.39 |
| **ratio of ratios** | | | **2.3181** | **2.3182** | |

| Track B | units | claimed chars | per own **token** | per own **char** | ranges/unit |
|---|---|---|---|---|---|
| orig256 (unformatted) | 1,072 | 1,430,795 | 5.3434 | **1.0000** | 1.00 |
| fmt256 (formatted) | 1,074 | 3,369,209 | 12.5845 | **2.3574** | 25.49 |
| **ratio of ratios** | | | **2.3551** | **2.3574** | |

The unformatted arm's per-own-char ratio is **exactly 1.0000**, which is §0a's by-construction
check passing: the naive chunker's `source_ranges` *is* its own substring's span
([naive.py:41](src/chunkers/naive.py#L41)).

### §3b — the channel is not symmetric, and the reason is structural

The asymmetry hypothesis in §3b was that chunk-to-segment inheritance is a property of the harness
and should therefore apply to both arms, inflating both sides of the paired comparison and
cancelling. **It does not, and the ratio of ratios is 2.32 / 2.36, not ~1.0.**

The reason is not a bug and not a choice — it is the pipeline shape. The unformatted arm is
**one stage**: chunk the raw document, and a chunk's provenance is its own character span. The
formatted arm is **two stages**: format into segments, then re-chunk the formatted text. Only the
second stage has segments to inherit from. **There is nothing on the unformatted side for the
channel to act on.**

So the threat as it bears on the size-matched control is asymmetric by construction, and the arms
have to be run. Arm 2b affects only the formatted arm; on the unformatted arm `tight == claimed`
by definition, so the comparison it produces is a formatted arm scored tightly against an
unformatted arm that was always tight.

---

## §4.4 — clean-gold retention, and the arm it disqualifies

`D` = ranges a unit claims but does not itself cover. A gold span is clean if it does not
intersect `D`; a query is clean if all of its spans are.

| clean-query retention | narrow `D` (absorbed only) | wide `D` (absorbed + inherited) |
|---|---|---|
| Track A (of 176) | **64 = 36.4%** ✗ below gate | **2 = 1.1%** ✗ |
| Track B (of 150) | **145 = 96.7%** ✓ | **0 = 0.0%** ✗ |

**Under the frozen 60% go/no-go, Arm 1 does not run inferentially on either track.** Track A fails
it even under the narrow definition; both tracks fail it under the wide one. Arm 1's counts and
descriptive deltas will be reported and no inferential claim made. **The threshold is not being
lowered to rescue the arm** — it was set before the count was known and that is its entire value.

### This corrects something in my own step-0a report

My step-0a summary said the absorption channel was "negligible in size" and implied Arm 2a would
therefore be near-inert. **The retention counts show that inference was wrong on Track A.**
Absorbed surface is 3.42% of the corpus but intersects the gold of **63.6%** of Track A's queries.
A channel's share of surface does not predict its share of *gold*, and on a synthetic corpus built
with deliberate restatements the two come apart hard — the restated sentences are exactly the
answer-bearing ones.

Consequences: Arm 2a is **not** a formality on Track A and may move that cell materially. It
remains near-inert on Track B (0.21% surface, 3.3% of queries touched). And "small in surface
therefore small in effect" is an inference this analysis should not make again.

---

## Correctness of the tight-provenance rebuild

Arm 2b needs per-sentence provenance, which production merges away twice
([formatter.py:306-308](src/chunkers/formatter.py#L306-L308), then `_formatted_segments`), so it
cannot be recovered from a built corpus. `src/pw1/tight_provenance.py` rebuilds the chunks with the
sentence layer retained, and because it re-derives boundaries rather than importing them it
**asserts against production**: identical chunk count, identical `unit_id`, identical text, and
identical claimed ranges, per document. That guard passed on all 45 Track A and all 60 Track B
documents — 235 and 1,074 chunks. If it had not, every number above would be void.

Right-sizing groups sentences and never drops them, so `own ∪ absorbed` is provably the complete
original surface and the stripping arithmetic is sound.

---

## What was and was not touched

No embeddings were computed. The LLM is cache-only (`_call_provider` replaced with a raiser), so
this could not spend a token or mint a corpus differing from the published runs'. No frozen
pre-registration, no published number, no existing bundle, and no paper file was modified.

Two harness facts recorded in passing, both relevant to the arms:

- **No ranked lists or per-query vectors are persisted for the size-matched control.**
  `results_v13/results.json` holds `{original_256: 0.608, formatted_256: 0.7557}` and nothing
  more. Guard 1 will therefore be satisfied by re-running retrieval under seed 1337 /
  `candidate_pool = 50` / `k_rrf = 60`, not by re-scoring persisted lists — the option §6.1
  anticipates.
- **`Embedder.encode()` does not cache.** [embed.py:7](src/index/embed.py#L7) states "Embeddings
  are cached by content hash under cache/emb/ for idempotency (§11)"; `cache/emb` is created and
  never written, and it is empty. Both models are in the local HuggingFace cache, so the arms cost
  local compute only — no downloads, no API calls, no new corpora.

---

## Next, on approval of this report

Freeze `posthoc_PW1_provenance_width.json` — three arms (2b primary, 2a secondary, 1 descriptive
only per the retention counts above), the five-branch ratio rule with thresholds 0.75 / 0.25 and
the sentence recording that they are conventional, the least-favourable aggregation rule, and the
§0 disclosure. Then NC-A and NC-B, then guard 1 reproduction, then the arms.
