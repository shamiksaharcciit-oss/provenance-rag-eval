# RAG Semantic Formatter — Results

**Run:** `run-20260726-191447` · **UTC:** 2026-07-26T19:14:47Z · **config digest:** `3fbfd2d58c49…`

## TL;DR verdict

**Decision: PARTIAL** — H1 not, H2 supported, H3 supported, H4 not.

> 2 track(s) evaluated; VALIDATE per §2.4 needs C3>=C2 on >=2 tracks + H2 + H3. validate_tracks=0, complement_tracks=0. A: C3=0.773 vs C2=0.852 (Δ=-0.080) — significantly beats semantic(C1) — H4 not significant (C5 vs C2 Δ=0.0)  | B: C3=0.380 vs C2=0.387 (Δ=-0.007) — significantly beats neither C0 nor C1 — H4 not significant (C5 vs C2 Δ=0.0067) . Per changelog-8, 'beats' claims above are only those with a Holm-significant, CI-excludes-0 pairwise difference. H3 note: the subjective readability rubric floored out on synthetic prose (judge rated BOTH original and formatted poorly); the OBJECTIVE preserved-term check (0 failures) is the trustworthy H3 signal — confirm subjective readability on Track B real prose. 


## Setup

- Tracks: A, B; conditions: C0, C1, C2, C3, C4, C5.
- Embedding: `BAAI/bge-base-en-v1.5` (backend `sentence-transformers`, rev `main`); FAISS `1.14.3`; seed 1337.
- LLM: `claude-opus-4-8` (provider `anthropic`).
- Chosen chunk sizes (dev-swept, §5.3): {'C0': 768, 'C1': 512, 'C3': 768}.
- Track A: n_test=176 queries.
- Track B: n_test=150 queries.

## Headline — Track A (recall@k, hybrid, any-overlap; 95% CI at k=5)

| Condition | R@1 | R@3 | R@5 [CI] | R@10 | nDCG@5 | MRR | units | u/doc |
|---|---|---|---|---|---|---|---|---|
| C0 | 0.562 | 0.727 | 0.790 [0.727,0.847] | 0.847 | 0.685 | 0.658 | 90 | 2.0 |
| C1 | 0.278 | 0.432 | 0.540 [0.466,0.614] | 0.619 | 0.407 | 0.379 | 328 | 7.3 |
| C2 | 0.460 | 0.818 | 0.852 [0.801,0.903] | 0.881 | 0.695 | 0.644 | 90 | 2.0 |
| C3 | 0.591 | 0.739 | 0.773 [0.710,0.835] | 0.835 | 0.692 | 0.672 | 90 | 2.0 |
| C4 | 0.744 | 0.807 | 0.835 [0.778,0.886] | 0.875 | 0.786 | 0.784 | 90 | 2.0 |
| C5 | 0.528 | 0.835 | 0.852 [0.801,0.903] | 0.875 | 0.726 | 0.685 | 90 | 2.0 |

![recall](figures/recall_at_k_by_condition_A.svg)


### Significance (paired bootstrap + permutation, Holm) — Track A

| Pair | Δrecall@5 | 95% CI | p | p(Holm) | CI excludes 0 |
|---|---|---|---|---|---|
| C3_vs_C2 | -0.080 | [-0.131,-0.028] | 0.0052 | 0.0208 | yes |
| C3_vs_C1 | +0.233 | [+0.153,+0.312] | 0.0001 | 0.0006 | yes |
| C3_vs_C0 | -0.017 | [-0.062,+0.034] | 0.6489 | 1.0000 | no |
| C5_vs_C2 | +0.000 | [-0.028,+0.028] | 1.0000 | 1.0000 | no |
| C4_vs_C0 | +0.045 | [+0.000,+0.091] | 0.0931 | 0.2793 | no |
| C5_vs_C3 | +0.080 | [+0.034,+0.131] | 0.0028 | 0.0140 | yes |

### Composition / complementarity (H4) — Track A

- C4 (formatted+naive) 0.835 vs C0 (naive) 0.790.
- C5 (formatted+contextual) 0.852 vs C2 (contextual) 0.852 — the H4 test.

![composition](figures/composition_A.svg)


**Common-size control (naive @256, §5.2):** original corpus 0.608 vs formatted corpus 0.756 (Δ=+0.148) — isolates text-quality from unit-count. See `figures/common_size_control_A.csv`.


## Headline — Track B (recall@k, hybrid, any-overlap; 95% CI at k=5)

| Condition | R@1 | R@3 | R@5 [CI] | R@10 | nDCG@5 | MRR | units | u/doc |
|---|---|---|---|---|---|---|---|---|
| C0 | 0.160 | 0.313 | 0.353 [0.280,0.433] | 0.473 | 0.262 | 0.249 | 378 | 6.3 |
| C1 | 0.140 | 0.273 | 0.360 [0.280,0.440] | 0.447 | 0.253 | 0.228 | 1040 | 17.3 |
| C2 | 0.180 | 0.340 | 0.387 [0.307,0.467] | 0.473 | 0.286 | 0.271 | 378 | 6.3 |
| C3 | 0.167 | 0.313 | 0.380 [0.300,0.460] | 0.447 | 0.279 | 0.253 | 381 | 6.3 |
| C4 | 0.167 | 0.340 | 0.400 [0.320,0.480] | 0.507 | 0.290 | 0.271 | 379 | 6.3 |
| C5 | 0.193 | 0.333 | 0.393 [0.313,0.473] | 0.507 | 0.296 | 0.282 | 381 | 6.3 |

![recall](figures/recall_at_k_by_condition_B.svg)


### Significance (paired bootstrap + permutation, Holm) — Track B

| Pair | Δrecall@5 | 95% CI | p | p(Holm) | CI excludes 0 |
|---|---|---|---|---|---|
| C3_vs_C2 | -0.007 | [-0.053,+0.033] | 1.0000 | 1.0000 | no |
| C3_vs_C1 | +0.020 | [-0.053,+0.093] | 0.7207 | 1.0000 | no |
| C3_vs_C0 | +0.027 | [-0.020,+0.073] | 0.3832 | 1.0000 | no |
| C5_vs_C2 | +0.007 | [-0.040,+0.053] | 1.0000 | 1.0000 | no |
| C4_vs_C0 | +0.047 | [+0.007,+0.093] | 0.0674 | 0.4044 | yes |
| C5_vs_C3 | +0.013 | [-0.033,+0.067] | 0.7977 | 1.0000 | no |

### Composition / complementarity (H4) — Track B

- C4 (formatted+naive) 0.400 vs C0 (naive) 0.353.
- C5 (formatted+contextual) 0.393 vs C2 (contextual) 0.387 — the H4 test.

![composition](figures/composition_B.svg)


**Common-size control (naive @256, §5.2):** original corpus 0.360 vs formatted corpus 0.427 (Δ=+0.067) — isolates text-quality from unit-count. See `figures/common_size_control_B.csv`.


## Guardrail — dense vs hybrid (H2)

Vocabulary drift would show as hybrid failing to track dense. See `figures/dense_vs_hybrid_<track>.svg`. Preserved-term failures: 0.


## Diagnostics (§8)

- **§8a C2-dense vs C0-dense (Track A):** dense C2=0.7898 vs C0=0.6818 (differ); hybrid C2=0.852 vs C0=0.790. Blurbs moved dense ranking as expected.
- **§8b C1 semantic sanity (Track A):** 328 units, 7.3/doc, mean 167 tokens. See `results.md` diagnostics note / boundary dump in the run log.
- **§8a C2-dense vs C0-dense (Track B):** dense C2=0.2933 vs C0=0.2867 (differ); hybrid C2=0.387 vs C0=0.353. Blurbs moved dense ranking as expected.
- **§8b C1 semantic sanity (Track B):** 1040 units, 17.3/doc, mean 257 tokens. See `results.md` diagnostics note / boundary dump in the run log.

## Reranking axis (amendment v1.3, H6)

Cross-encoder `cross-encoder/ms-marco-MiniLM-L-6-v2` reranking the fused candidate pool before the top-k cut. Orthogonal axis: every condition is scored with and without reranking from the same retrieval call, paired over queries.

### H6 main effect — recall@5 (hybrid, any)

| Track | Condition | base | +rerank | Δ | 95% CI | p | p(Holm) | CI excludes 0 |
|---|---|---|---|---|---|---|---|---|
| A | C0 | 0.790 | 0.688 | -0.1023 | [-0.1705, -0.0341] | 0.0062 | 0.0186 | yes |
| A | C1 | 0.540 | 0.494 | -0.0455 | [-0.1080, +0.0170] | 0.1960 | 0.3920 | no |
| A | C2 | 0.852 | 0.648 | -0.2045 | [-0.2670, -0.1420] | 0.0001 | 0.0006 | yes |
| A | C3 | 0.773 | 0.744 | -0.0284 | [-0.0852, +0.0284] | 0.4420 | 0.4420 | no |
| A | C4 | 0.835 | 0.744 | -0.0909 | [-0.1477, -0.0398] | 0.0018 | 0.0072 | yes |
| A | C5 | 0.852 | 0.631 | -0.2216 | [-0.2898, -0.1591] | 0.0001 | 0.0006 | yes |
| B | C0 | 0.353 | 0.393 | +0.0400 | [-0.0133, +0.0933] | 0.2360 | 1.0000 | no |
| B | C1 | 0.360 | 0.400 | +0.0400 | [-0.0267, +0.1067] | 0.3193 | 1.0000 | no |
| B | C2 | 0.387 | 0.347 | -0.0400 | [-0.1000, +0.0200] | 0.2682 | 1.0000 | no |
| B | C3 | 0.380 | 0.393 | +0.0133 | [-0.0400, +0.0667] | 0.7984 | 1.0000 | no |
| B | C4 | 0.400 | 0.420 | +0.0200 | [-0.0333, +0.0733] | 0.6297 | 1.0000 | no |
| B | C5 | 0.393 | 0.407 | +0.0133 | [-0.0467, +0.0733] | 0.8309 | 1.0000 | no |

### H6a interaction — Track A

- formatter gain (C3 − C0): **-0.0170**
- rerank gain on C0: **-0.1023**
- rerank gain on C3: **-0.0284**
- difference-in-differences `(C3+rerank - C3) - (C0+rerank - C0)`: **+0.0739**, 95% CI [+0.0057, +0.1420], p=0.0454
- reading: **the formatter REDUCES the reranker's harm — reranking costs less on the formatted corpus than on the naive one (both effects are negative)**
- H6b, C0+rerank vs C3: -0.0852 [-0.1591, -0.0114], significant

### H6a interaction — Track B

- formatter gain (C3 − C0): **+0.0267**
- rerank gain on C0: **+0.0400**
- rerank gain on C3: **+0.0133**
- difference-in-differences `(C3+rerank - C3) - (C0+rerank - C0)`: **-0.0267**, 95% CI [-0.0800, +0.0267], p=0.4487
- reading: **no detectable interaction (additive within CI)**
- H6b, C0+rerank vs C3: +0.0133 [-0.0467, +0.0733], not significant


## Cost

LLM cost (global): {'llm_calls': 0, 'llm_tokens': 0, 'input_tokens': 0, 'output_tokens': 0, 'cache_hits': 420, 'est_usd': 0.0}. See `figures/cost_vs_recall.svg`.


## Readability (H3)

C3 mean 1.45 vs original 1.60 on 20 docs; preserved-term failures 0. Rubric: LLM 1-5 readability rubric, temp 0 + preserved-term check.


## Threats to validity

- **Track A is synthetic and adversarial by construction** — the injected damage (anaphora, duplication, split) is exactly what the formatter targets, so Track A shows *mechanism*, not field generalization. VALIDATE requires ≥2 tracks (§2.4).
- **Per-condition LLM cost attribution** is approximate; only C2/C3 are charged and the global tally is authoritative.
- **Formatter provenance is approximate** (edited units map to source sentence offsets); any/strict variants are both reported as a cross-check (§13).

## Reproduction

```bash
make setup
make test
python -m src.run --track A --provider none  # zero-cost
python -m src.run --track A --provider anthropic   # headline (needs ANTHROPIC_API_KEY)
python -m src.run --report-only
```

Pre-registration hash: `ececbb922a1061a9…` (frozen before treatment metrics).
