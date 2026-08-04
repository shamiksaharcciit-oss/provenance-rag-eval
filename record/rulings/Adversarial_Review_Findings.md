# Internal adversarial review — verified findings
## When_the_Scoreboard_Lies.pdf · four hostile passes + verification against the programme record · 2 Aug 2026

Verdict format: each finding was checked by me against the paper text and, where applicable,
against the experiment record this paper summarises. CONFIRMED = defect is real as stated.
CONFIRMED-WITH-CORRECTION = real, but the reviewer's framing needed adjusting against the
record. REJECTED = the attack fails on the facts.

---

## TIER 1 — factually false or misleading as written; must fix before anyone else reads it

**1. "Refusing when the answer is present has no benchmark at all" is false. CONFIRMED.**
RefusalBench (arXiv:2510.10390, Oct 2025) measures false refusal on answerable questions in
grounded settings; AbstentionBench (arXiv:2506.09038) measures over-abstention; SQuAD 2.0
has penalised wrong abstention since 2018. Both key papers verified to exist. The narrow
true claim: no prior work measures wrong abstention *as a function of context prose quality
with information held identical by construction*. Rewrite the sentence, cite both.

**2. "No existing evaluation isolates this variable" (Fig 5 caption) is overbroad. CONFIRMED.**
OHRBench / "OCR Hinders RAG" (arXiv:2412.02592, ICCV 2025 — verified) varies text
degradation against clean ground truth and measures cascading impact on retrieval and
generation. What survives for us: information-identity guaranteed by provenance, the repair
(not degradation) direction, and the abstention channel. Cite it; narrow the caption.

**3. The decomposition arithmetic misleads: 23+1+0 = 24, presented as decomposing 38.
CONFIRMED — and the honest fix is stronger than the current text.** The record: the
fixed-k gain was 38; at equal token cost the total gain is 24, and *that* decomposes as
size 23, boundary 1, whitespace 0, editing 0. The missing 14 queries are the metric's size
subsidy itself — they vanish when the accounting is honest. Say exactly that: it accounts
for every query and sharpens the argument. Also: table's "editing: 0 of 38" → "editing: 0
(and a non-significant 7 at the other size)"; soften "almost entirely."

**4. The paper's own origin story for the reading test is backwards — and the truth is
better. CONFIRMED against the record.** The paper says the control anomaly (+0.13) led us
to "build the missing test." The record shows the reading test was designed and frozen
*before* the anomaly's result existed (v1.9 froze at 14:07; v1.8's results landed after).
The dramatic order invites a "hypothesis drawn from data" attack that the real chronology
defeats. Fix the narrative to the true sequence; rename the "+0.12 replication" a
"regeneration stability check" (same queries, fresh draws — the record's own term).

**5. Fig 6 caption contradicts the body: "disappears entirely" vs "reversed outright."
CONFIRMED.** The record says reversed (−0.018). Fix the caption.

**6. The summary table's arrow renders as "15fi1" in extracted text — a glyph/ligature
corruption. CONFIRMED in the artifact.** Replace the arrow with words.

## TIER 2 — presentation choices a reviewer will punish; fix in this revision

**7. Metric coupling between +0.11 and 15:1 presented as two findings. CONFIRMED.**
NOT FOUND scores 0, so the ~14 extra abstentions mechanically contribute roughly a third
to half of the +0.11. The record always treated abstention as "a component, not an
artifact" — the paper should too, at the point of first presentation, not in §7.

**8. Absolute-gap claims need repositioning against a fuller related-work base. CONFIRMED.**
Verified-real works the paper must cite and position against: KILT (provenance vocabulary),
HOPE/SIGIR-2025 (evaluates transforming chunkers, non-exact), a Jan-2026 fill-to-budget
chunking study (budget matching precedent), the semantic-chunking null (NAACL Findings
2025), and the judge-bias literature (SOS-Bench, "Judging the Judges", format-restriction
work). What survives, per the novelty agent's own negative searches: char-offset provenance
scoring of rewritten text, the matched-length filler control on contextual retrieval, the
information-identical reading-test construction, and the parse-failure-censors-hard-cases
corollary. Those four are the paper's honest novelty perimeter.

**9. −3 on the second embedder used rhetorically while +3 is dismissed as noise. CONFIRMED.**
Same lattice, opposite treatment. Fix: "the gain failed to replicate on a second embedding
model" — which is the defensible claim.

**10. Boundary-null generalised beyond its design ceiling. CONFIRMED.** Our own arithmetic
caps the detectable boundary effect at roughly 12–20 queries at this chunk size. Condition
the verdict: "at 768-token chunks with sentence-scale answers."

**11. Judge findings generalised from one judge, one family, one setting. CONFIRMED —
plus one reviewer point that is statistically right:** many per-pair differences are tiny
(48 pairs tie on F1 itself), so per-pair ties are not automatically "timidity." Scope §5's
claims to the measured judge; report tie analysis beside per-pair effect sizes; add the
single-vendor limitation and an independence/COI line. F1-vs-judge symmetry point
(span-F1 penalises fluent paraphrase) goes into limitations honestly.

**12. Methods are unnamed in the body — models, embedders, k, budget, stats. CONFIRMED.**
Add a compact methods box: generator claude-sonnet-5; judge same family; second model
claude-haiku-4.5; embedders MiniLM-L6-v2 and bge-base-en-v1.5; k=5; budget 1,920 tokens;
paired bootstrap + permutation, Holm correction; corpus sizes 45 docs/176 queries and
150 queries. Fixes the "decorative statistics" charge in one stroke.

**13. Reproducibility claims currently point at nothing. CONFIRMED.** "Accompanies this
paper" with no URL; "pre-registered" meaning self-hosted git. Fix: "will be released with
the public repository at [URL]" + describe the practice as internally pre-specified with
hash-chained history — accurate and still unusual. Add counts behind every percentage
(148/176, 24/28, 28 and 35 of 176) to honour the paper's own integer-count pledge.

**14. AI-involvement disclosure is one oblique clause. CONFIRMED — Shamik's wording to
choose.** Recommended: a short statement that experiments were executed by AI coding
agents under human direction, with adversarial cross-checking between agents and human
rulings on every deviation; prose drafted with AI assistance; every number verified
against artifacts. The current single clause is a pile-on vector; a plain statement makes
the process a strength.

## TIER 3 — judgement calls; recommended but Shamik decides

**15. Title/subtitle.** Keep the narrative title for the white-paper genre if desired, but
change "the measuring instrument the field is missing" → "a measuring instrument the field
lacks", and expect the title criticism at any formal venue. REVIEWER-VALID, GENRE-DEPENDENT.
**16. "$55" placement in the standfirst** invites toy-study pattern-matching; either keep
(genre) or move to §10. **17. "What to do differently on Monday"** → retitle "Practical
implications" and hedge each directive with its evidentiary scope. **18. Standfirst's
"contextual retrieval is genuinely effective"** → add "where it works — the effect is
corpus-dependent." **19. "Information, not length" (Fig 3)** → "content, not length": the
control rules out length, not topical-vocabulary effects; a generic-on-topic filler arm is
honest future work. **20. "A few hundred queries each"** → "176 and 150 queries."

## REJECTED after verification

- "The +65 vs +3 comparison is not apples-to-apples": REJECTED on the facts — both are the
  same experiment, same metric, at matched budget (the record's integrity experiment). The
  paper's error is only that it doesn't *say* so; one clause fixes it.
- "Pre-registration claim is undermined by exploratory origin": REJECTED as an attack on
  the record (the freeze genuinely predates the anomaly result) — but CONFIRMED as an
  attack on the paper's telling of it (finding 4).
- "Reproducibility of deterministic pipelines is tautological, judges reproduce fine at
  temperature 0": REJECTED in our stack — the measured judge/generator rejects the
  temperature parameter and was measured nondeterministic (6/20 stable). The paper should
  state that basis instead of the current unqualified dichotomy.
