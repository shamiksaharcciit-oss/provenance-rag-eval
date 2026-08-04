# Experiment Plan Amendment v1.4 — Small-to-big / parent-child retrieval (M7)

**Owner:** Shamik Saha · **Date:** 27 July 2026 · **Amends:** v1.1 base plan.
**Status: DRAFT — NOT FROZEN, NOT RUN. Sent for review before freezing.**
**Criteria template:** `Amendment_Criteria_Template.md` v1.0 (four-branch, mandatory).

---

## 1. Why this, and why now

Next on the retrieval-stack roadmap, and the v1.3 diagnosis promoted it. Reranking harm
concentrated where first-stage recall was already high (r = −0.853 with baseline recall),
which says the remaining headroom is in the **first stage**, not in post-hoc reordering.
Small-to-big targets the first stage directly: index small, precise child units; hand the
generator their larger parent.

## 2. Headroom analysis — done BEFORE writing the hypothesis

Small-to-big improves retrieval by finding gold that current units miss. Its addressable pool
is therefore the **ceiling gap** (1 − recall@10): queries whose gold is not in the top-10 at
all. Measured on v1.3 (`results_v13/results.json`, bge-base):

| Track | Conditions | recall@5 | **ceiling gap (1 − r@10)** | ranking headroom (r@10 − r@5) |
|---|---|---|---|---|
| A | C0/C2/C4/C5 | 0.790–0.852 | **0.119 – 0.153** | 0.023 – 0.057 |
| A | C3 | 0.773 | 0.165 | 0.062 |
| A | C1 | 0.540 | 0.381 | 0.080 |
| B | C0–C5 | 0.353–0.400 | **0.493 – 0.553** | 0.067 – 0.120 |

**Conclusion, stated plainly:** on Track A's strong conditions only **12–15% of queries** have
gold outside the top-10, so the mechanism has very little to work with — the same ceiling that
made the reranker look harmful. On Track B **half the corpus** is unretrieved. Track A cannot
express a success criterion for this treatment; Track B can.

**Therefore the primary hypothesis is scoped to Track B**, with Track A as a secondary
**no-harm check**. This is declared here, before any run, rather than discovered afterwards.

## 3. Design

Small-to-big is a **retrieval-unit** change, so it composes with the corpus-side conditions the
way reranking did — an orthogonal axis, not a new condition. Every comparison is paired
within-run on identical queries.

**Applied to:** C0 (naive), C2 (contextual), C4 (formatted+naive). C1 is excluded (its
semantic chunker already sets its own boundaries); C3 and C5 are excluded from the primary
comparison for the reason in §5.

### Child/parent construction, per condition

| Condition | Child (indexed, scored) | Parent (returned for context) |
|---|---|---|
| C0 | naive cut of raw text at `child_tokens` | the enclosing 768-token naive chunk |
| C2 | naive cut of raw text at `child_tokens` | enclosing naive chunk **+ its contextual blurb** |
| C4 | naive cut of **formatted** text at `child_tokens` | the enclosing formatter-marked section |

**Child size is pre-registered, not swept.** Primary `child_tokens = 128`; `child_tokens = 256`
is a pre-declared robustness variant reported alongside. Both are declared now because
**Track B has no dev split** (`dev_fraction: 0.0` — all 150 queries are test), so sweeping on
Track B would contaminate the test set, and transferring a Track-A-swept size to Track B would
be an untested assumption. Reporting both pre-declared sizes avoids post-hoc selection.

## 4. The metric trap — provenance rule (MANDATORY)

**Hits are scored on the CHILD's `source_ranges` — the unit retrieval actually found — never
on the parent's.**

If hits were scored on parent ranges, returning a larger parent would mechanically increase
overlap with any gold span, and the metric would reward dilution: the widest parent always
"wins". This is the small-to-big equivalent of the merged-unit provenance fix in v1.1.

Enforcement: the retrieved unit carries child provenance; the parent is attached as a separate
`context` field and is **never** passed to `hit_flags`. A test asserts that widening the parent
leaves every recall number unchanged.

**Secondary, descriptive only:** "parent contains gold" is reported as a context-sufficiency
statistic. It is inflation-prone by construction, carries no decision weight, and must never
be quoted as a recall number.

### What this experiment does and does not measure

It measures the **retrieval half** of small-to-big: whether indexing smaller child units finds
gold that current units miss. The generation-side benefit — that the model receives coherent
parent context rather than a fragment — is **asserted, not measured**; this harness has no
generation metric. Stated here so no reader infers otherwise.

## 5. Known structural advantage — declared, not hidden

For C4 the natural parent is a **formatter-marked section**: a semantically coherent unit the
formatter produced. For C0/C2 the parent is an arbitrary 768-token window. If C4 outperforms,
part of that advantage is that *the formatter supplies better parent boundaries* — which is a
real property of the treatment, but it is not the same claim as "small-to-big helps".

Mitigation and reporting rule:
- C0/C2 vs C4 differences are reported with this asymmetry restated at the point of comparison.
- The **primary** hypothesis is within-condition (X+s2b vs X), which is immune to it.
- C3/C5 are excluded from the primary comparison because their units are already
  marker-delimited, making "child of a marked section" partly circular.

## 6. Pre-registered hypotheses

**H7 (primary, Track B).** For each condition X ∈ {C0, C2, C4}, small-to-big at
`child_tokens=128` improves recall@5 (hybrid, `any`) versus X, paired over queries.

**H7a (secondary, Track A).** No-harm check: small-to-big does not significantly *reduce*
recall@5 on Track A. Track A is not expected to gain (§2).

**H7b (robustness).** H7 at `child_tokens=256`, reported alongside 128; no selection between
them after the fact.

**H7c (descriptive).** Parent context-sufficiency rate and mean parent token count, as a cost
figure. No decision weight.

## 7. Decision rules — four branches (template v1.0)

| Branch | Condition |
|---|---|
| **ADOPT** | H7 significant positive (paired CI excludes 0 after Holm within {C0, C2, C4}) on Track B for `child_tokens=128`, **and** H7a shows no significant harm on Track A |
| **ADOPT_SCOPED** | H7 significant positive on a *pre-named* admissible scope only — admissible scopes are: a single condition family (C0/C2 vs C4), or one child size but not the other. Any other scope is a hypothesis, not a verdict |
| **KILL (null)** | H7 not statistically distinguishable from zero on Track B |
| **REJECT_HARM** | Significant **negative** effect on any primary condition on either track, same rule as ADOPT with sign reversed. Takes precedence over KILL |

`REJECT_HARM` is present because the v1.3 gap showed a plan that cannot name harm will be
forced to mislabel it. Small-to-big can plausibly harm: smaller units carry less context and
may embed worse.

## 8. Statistics

- Primary metric recall@5, hybrid, `any` overlap. Secondary: recall@{1,3,10}, nDCG, MRR, strict variant.
- Paired bootstrap (10k) for the mean difference and CI; paired permutation (10k) for p.
- **Holm families:** H7's three conditions on Track B form one family. Track A's no-harm checks
  form a separate family. Neither is merged with v1.1's H1–H4 or v1.3's H6.
- Child-size variants are reported separately, not pooled.

## 9. Environment pins (template §B)

| Pin | Value |
|---|---|
| `embedding.model` | **`BAAI/bge-base-en-v1.5`** — pinned explicitly, not inherited |
| `embedding.revision` | `main` |
| LLM | `claude-opus-4-8` (Track A) / `claude-sonnet-5` (Track B), cache-served |
| `run_id` | must be populated |
| output | `--out results_v14` — never `results/` |

**Comparability note:** v1.1's published numbers used `all-MiniLM-L6-v2`. v1.4 pins bge-base,
so v1.4 absolute numbers are comparable to **v1.3's**, not to v1.1's. Only within-run paired
deltas are quotable across amendments.

## 10. Cost

No LLM calls beyond cache (C2/C4 corpora already built). Child re-chunking and re-embedding
only. Track B's larger child counts at 128 tokens are the main cost — estimated 3–5× the
current unit count, so indexing time rises correspondingly.

## 11. What this does not test

- Generation quality or answer faithfulness with parent context (no generation metric).
- Child sizes other than 128 / 256.
- Track C (blocked on v1.2's open design items).
- Interaction with reranking — that axis is spent on this split.
