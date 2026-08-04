# Experiment Plan v1.1 — Semantic Formatter Retrieval Evaluation

**Owner:** Shamik Saha · **Version:** 1.1 · **Date:** July 2026
**Supersedes:** v1.0 (executed as `run-20260723-223653`, Track A complete, verdict PARTIAL)
**Audience:** the autonomous coding agent that built and ran v1.0 in `rag-formatter-eval/`.

---

## Changelog v1.0 → v1.1 (read first)

1. **Two new conditions (composition cells):** C4 = formatted corpus + naive chunking, C5 = formatted corpus + contextual retrieval (stacked). These test whether the formatter *improves existing chunking strategies* rather than merely competing with them. New hypothesis **H4 (complementarity)** pre-registered in §2.
2. **Track B is now REQUIRED**, not best-effort. It is the second track needed for any VALIDATE verdict, the fix for the readability-rubric floor (real prose), and the realistic-index-size control.
3. **Provenance for merged units (dedup fix):** when the formatter merges/deduplicates restatements, the surviving unit MUST carry `source_ranges` covering **every absorbed instance**. New scorer unit test: a gold span anchored to a removed restatement must still score a hit via the surviving unit. (Track A's dedup ablation came back −1.1 pts; part of that may be false misses from this gap.)
4. **Dedup expectation pre-registered:** de-duplication is expected to be neutral-to-negative for recall (redundancy is robustness). Track A confirmed this (−0.011). A negative dedup ablation is an expected finding, not a failure.
5. **Cost accounting must actually work.** v1.0 reported `llm_calls: 0` for every condition including C2/C3. v1.1 requires per-condition attribution split into `fresh_calls`/`cached_calls` and `fresh_tokens`/`cached_tokens`; the run must FAIL a self-check if C2/C3/C5 report zero total (fresh+cached) LLM usage.
6. **Base-rate controls:** report units-per-doc and index size prominently; additionally report recall@5 for all conditions at one **common fixed chunk size (256 tokens)** alongside each condition's swept-best, so wins can't come from unit-count compression (Track A: C0 at 768 tokens ≈ 1–2 chunks/doc made naive artificially strong and squeezed all differences).
7. **Diagnostics required this run** (§11): (a) investigate why C2's dense recall was byte-identical to C0's in Track A (blurbs helped only via BM25 — confirm or find the bug); (b) sanity-check the C1 semantic chunker (0.54 on Track A is anomalously poor — verify boundary detection isn't broken); (c) guard the no-size ablation against degenerate micro-units (Track A produced 5,143 units of ~10 tokens; enforce a minimum unit size of 30 tokens in `C3-nosize` so the ablation measures sizing skill, not degeneracy).
8. **Statistical-precision rule for prose claims:** any "beats" claim in `results.md` must be backed by a significant pairwise test (CI excluding 0 after Holm). Track A's notes claimed C3 "clearly beats naive" while the pairwise was n.s. (p=0.24) — do not repeat that.
9. **Reuse the v1.0 cache.** Same seed (1337), same models, same Track A corpus. Track A C0–C3 + ablations should reproduce from cache; the formatted corpus is reused for C4/C5. Expected fresh spend: C5 blurbs on the formatted corpus, Track B everything, nothing else.

Everything not amended below carries over from v1.0 unchanged (repo layout, canonical schema, retrieval stack, scoring algorithm, statistics, output formats).

---

## 1. Background

Unchanged from v1.0. The semantic formatter is a conservative, meaning-preserving pre-chunking editorial pass (resolve references, de-duplicate, right-size, emit boundary markers) under one rule: edit structure and references, never vocabulary, identifiers or numbers. v1.0/Track A established the mechanism: parity with contextual retrieval (Δ = −0.034, n.s.), guardrail intact (0 preserved-term failures, hybrid gain preserved), reference-resolution and right-sizing the load-bearing operations.

## 2. Goals, hypotheses, pre-registered criteria

### 2.1 Primary goal (v1.1)
Determine, on real prose (Track B) and with composition cells, whether the formatter (a) generalizes beyond the synthetic mechanism study and (b) **improves existing chunking strategies** rather than only matching them.

### 2.2 Hypotheses (freeze before running)
- **H1 (retrieval):** unchanged — C3 recall@k ≥ C2, and > C1 > C0, k ∈ {1,3,5,10}.
- **H2 (guardrail):** unchanged — no hybrid degradation vs dense for C3 (and now C4/C5).
- **H3 (readability):** unchanged in substance; **assessed subjectively on Track B real prose** (Track A's rubric floored on synthetic text; its objective preserved-term check remains the Track A signal).
- **H4 (complementarity, NEW):** C5 (formatted + contextual) recall@5 > C2 (contextual alone), paired CI excluding 0 after Holm. Secondary: C4 (formatted + naive) > C0 (naive alone).
- **Pre-registered expectation:** the dedup ablation is neutral-to-negative (confirmed on Track A).

### 2.3 Verdict logic (freeze in `preregistration.json` before any v1.1 metric is computed)
- **VALIDATE:** as v1.0 — C3 ≥ C2 (within CI or better) on ≥2 tracks AND H2 AND H3.
- **COMPLEMENT (new, independent finding):** H4 holds on Track B (and directionally on Track A). May be reported alongside any verdict; C5 > C2 significant on both tracks is the strongest possible outcome.
- **PARTIAL:** parity with C2 plus significant wins over C0 *or* C1 (state precisely which, per §Changelog-8), AND H2, AND H3-objective.
- **KILL:** unchanged from v1.0.

## 3. Conditions (updated table)

| ID | Corpus | Chunking | Enrichment | Purpose |
|----|--------|----------|------------|---------|
| C0 | original | naive fixed (swept) | — | floor |
| C1 | original | semantic | — | boundary-intelligence baseline (sanity-check per §11b) |
| C2 | original | naive/semantic (best) | contextual blurbs | strong baseline |
| C3 | formatted | split on markers | — | treatment (v1.0) |
| **C4** | **formatted** | **naive fixed (same size as C0's swept-best and the 256 control)** | — | does formatting help a dumb chunker? (ignore markers entirely) |
| **C5** | **formatted** | **split on markers** | **contextual blurbs on formatted units** | stacked: complementarity test (H4) |
| C3-noref / C3-nosize / C3-nodedup / C3-markeronly | as v1.0 | | | ablations (nosize: enforce 30-token minimum unit) |

Notes: C4 must NOT use the markers — cut the formatted text with the same fixed-size splitter as C0. C5's blurbs are generated per formatted unit with the same prompt/model as C2's (cached by content hash; formatted units differ from original chunks so these are fresh calls).

## 4. Tracks

- **Track A (synthetic):** rerun from cache; add C4/C5 (cheap: formatted corpus cached). Its role is mechanism + directional H4.
- **Track B (public, REQUIRED):** as v1.0 §5.1-B — QASPER preferred, else Natural Questions long-answer, else NarrativeQA/MultiHop-RAG; ≥150 queries, mixed qtypes; gold evidence mapped to char offsets in original documents. If no candidate loads, STOP and write `BLOCKERS.md` — v1.1 is not complete without a second track.
- **Track C (internal):** unchanged, optional, runs iff `data/internal/` + human-verified gold exist.

Run the readability review (H3 subjective) on **Track B documents**: 20 docs, blind LLM rubric, original vs formatted, plus the preserved-term check on every formatted doc in both tracks.

## 5. Measurement amendments

### 5.1 Provenance (supersedes v1.0 §6.1 for merges)
Every unit carries `source_ranges: list[(start,end)]` in original-document coordinates. **When content is merged or removed as duplicate, the surviving unit's `source_ranges` must include the ranges of all absorbed/removed instances.** Required new scorer tests:
1. Gold span anchored inside a removed restatement → retrieval of the surviving merged unit scores a **hit**.
2. Existing v1.0 tests still pass.

### 5.2 Base-rate control
For every (track, condition): report `index_units`, `units_per_doc_mean`, `token_mean` in the headline table, AND compute the **common-size control**: recall@5 with all corpus variants cut at fixed 256 tokens (original corpus for C0/C1/C2-basis; formatted corpus for C4-at-256). This isolates text-quality effects from unit-count effects.

### 5.3 Cost accounting (supersedes v1.0 §7.7)
Per condition: `{fresh_calls, cached_calls, fresh_tokens, cached_tokens, format_seconds, index_seconds}`. Self-check at report time: `fresh+cached == 0` for any of C2/C3/C5 → abort with error. The cost-vs-recall figure uses fresh+cached tokens (label which).

## 6. Statistics
Unchanged from v1.0 (paired bootstrap ≥10k, permutation + Holm, CIs mandatory) with one addition: the pairwise set now includes **C5 vs C2** (the H4 test), **C4 vs C0**, and **C5 vs C3**. Prose rule per Changelog-8.

## 7. Outputs
As v1.0 §10 with: `conditions` extended to include C4/C5; `verdict` block gains `"H4": "supported|not"` and `"complement": true|false`; figures add `composition_<track>.svg` (C0 vs C4, C2 vs C5, side-by-side with CIs) and the common-size-control table as `figures/common_size_control_<track>.csv`. Return the same §10.5 bundle.

## 8. Diagnostics required this run (new)

a. **C2-dense anomaly:** on Track A, C2 dense recall was identical to C0's (0.7045) to 4 d.p. Determine whether blurbs genuinely didn't move dense retrieval at 660-token units (plausible: blurb is small relative to unit) or whether blurbed text was not what got embedded (bug). One paragraph + evidence in `results.md`.
b. **C1 sanity check:** semantic chunking scored 0.54 on Track A — verify the boundary detector on 5 hand-inspected documents (dump boundaries; do they fall at topic shifts?). If broken, fix and re-run C1 (note the fix); if genuinely this bad on degraded text, say so with an example.
c. **Ablation degeneracy guard:** `C3-nosize` enforces ≥30-token units (merge smaller into neighbors). Re-run; report the corrected right-sizing contribution.

## 9. Execution order

1. Freeze updated `preregistration.json` (H4 + dedup expectation + verdict logic above); hash into results.
2. Scorer changes (§5.1) + new tests green. Cost-accounting fix + self-check.
3. Track A: reproduce C0–C3+ablations from cache; run diagnostics (§8); add C4, C5, common-size control.
4. Track B: adapter, gold mapping, sweep sizes on dev split, full run all conditions incl. C4/C5 + ablations + readability review.
5. Track C iff data present.
6. Stats incl. H4 pairwise; figures; `results.md` (with Threats-to-validity updated: synthetic-mechanism caveat, any deviations); return bundle.

## 10. Acceptance criteria (delta from v1.0)
- New scorer tests pass; cost self-check active; `C3-nosize` unit floor enforced.
- Track B complete (or `BLOCKERS.md` with exact failures — run is then explicitly incomplete).
- H4 tested with CIs on every track run; composition figure emitted.
- All v1.0 acceptance criteria still hold; cache reuse verified (Track A C0–C3 metrics identical to run-20260723-223653).

---

*End v1.1. Where deviation is unavoidable, record it in `results.md` under Threats to validity. The formatted corpus, prompts, models and seed are unchanged from v1.0 — spend should concentrate almost entirely on Track B and C5 blurbs.*
