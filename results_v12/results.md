# v1.2 — Document-Identity Injection — Results

**UTC:** 2026-07-24T23:24:17Z · **prereg:** `478548fa5fb0…` · **doc-list:** `1e7c6ed5f9f1…` · **exclusion:** `2892875dfb69…`

## TL;DR verdict

**Decision: REJECT** — H5 not, H5a not, H5b not, H5c supported.

> fmt_valid=True (fallbacks C4=2/134; C4i=1/134, max_rate=0.1); H5(C4i>C4 full-set)=n.s.; H5a(identity_poor)=n.s. (delta=0.0065, n=153); H5b term_fail=7 src_viol=111 hybrid>=dense=True; H5c c4i=3.85 orig=3.95 c4=3.8; stamps=120.


> Decided on **Track B2** (180 fresh held-out queries, 153 identity_poor / 27 rich, 134 docs). The old B-150 is **development data (contaminated — the idea was derived from its failures)** and plays no part in this decision.


## B2 headline (recall@5, hybrid; 95% CI)

| Condition | prompts | recall@5 [CI] | dense@5 | units | fresh/cached |
|---|---|---|---|---|---|
| C0 | n/a | 0.322 [0.256,0.389] | 0.222 | 815 | 0/0 |
| C2 | eval-run-20260724-135411 | 0.378 [0.311,0.450] | 0.250 | 815 | 0/815 |
| C4 | eval-run-20260724-135411 | 0.361 [0.294,0.433] | 0.256 | 813 | 21/113 |
| C4i | v1.2-identity | 0.356 [0.283,0.428] | 0.261 | 814 | 134/0 |

### Significance (paired bootstrap + Holm) — the H5 family

| Pair | Δrecall@5 | 95% CI | p | p(Holm) | CI excludes 0 |
|---|---|---|---|---|---|
| C4i_vs_C4 | -0.006 | [-0.044,+0.033] | 1.0000 | 1.0000 | no |
| C4i_vs_C2 | -0.022 | [-0.067,+0.022] | 0.4848 | 0.9695 | no |
| C4i_vs_C0 | +0.033 | [-0.006,+0.078] | 0.1800 | 0.5400 | no |

## Subgroup effect (H5a) — the mechanism test

![subgroup](figures/subgroup_effect.svg)

| Subgroup | n | C4 | C4i | Δ (C4i−C4) | 95% CI | sig |
|---|---|---|---|---|---|---|
| identity_poor | 153 | 0.294 | 0.301 | +0.006 | [-0.039,+0.052] | no |
| identity_rich | 27 | 0.741 | 0.667 | -0.074 | [-0.185,+0.000] | no |

## Guardrail (H5b)

- preserved-term failures: **7** (target 0)
- identity-source violations: **111** (target 0)
- hybrid tracks dense: **True** (C4i hybrid 0.356 vs dense 0.261)

## Readability 3-way (H5c)

- original 3.95 · C4 3.80 · C4i 3.85 (n=20); C4i must be within 0.15 of both.
- identity stamps: total 120, per-doc mean 0.90 / max 9. ![stamps](figures/stamps_distribution.svg)

## Track A regression (safety, not a decision input)

C4 0.841 vs C4i 0.830 (Δ=-0.011, CI [-0.034,+0.011]); within CI of C4: **True** (pre-registered expectation: C4i ≈ C4 on identity-rich synthetic data).

## Cost

B2 LLM: {'llm_calls': 204, 'llm_tokens': 1427833, 'input_tokens': 1388669, 'output_tokens': 39164, 'cache_hits': 999, 'est_usd': 7.9224}.


## Threats to validity

- **The old B-150 was development data** — the identity-injection idea was derived from its failures, so it is contaminated as evidence; this decision uses only the fresh B2 split.
- **v1.2 baselines are NOT numerically comparable to v1.1** (corpus expanded for query supply). The v1.2 decision is internal to its own corpus (C4i vs C4), which is unaffected.
- **Larger distractor pool** (expanded corpus) increases distractor mass — realistic for real KBs and favorable to detecting the identity effect; accepted because the corpus was frozen (doc-list hash) before any treatment metric existed.
- **One-shot rule:** if H5 failed on B2, the feature is not re-tried on B2 — a retry needs a B3 split.

## Reproduction

```bash
python -m src.run_v12 --provider anthropic --b2-model claude-sonnet-5 --a-model claude-opus-4-8
```
