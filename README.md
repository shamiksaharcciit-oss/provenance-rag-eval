# provenance-rag-eval

The evaluation apparatus and complete experimental record behind the paper
**When the Scoreboard Lies** ([preprint link to be added at release]).

We built a document-cleaning tool for RAG pipelines and watched it pass every
standard test. The success turned out to be an illusion: of 38 queries the
standard fixed-k metric credited to the tool, 37 were chunk-size effects and the
metric's own size subsidy. Chasing down why produced the thing this repository
actually contains — an evaluation method for *transforming* pipelines in which
every text unit permanently carries the exact character ranges of the original
documents it derives from, so that scoring is interval arithmetic against
registered answer spans: deterministic, reproducible to the digit, and immune to
the artifacts that misled us.

The same instrument validated a technique it had every "incentive" to kill:
contextual retrieval's gain survived budget-honest accounting (+20/176, twenty
wins to zero losses) while its matched-length filler control did not — the gain
is information, not length. An instrument is only credible if it can return
different verdicts on different truths; the record here contains both directions.

## Why exact scoring of transformed text is possible

Provenance is recorded during transformation, never recovered after it. Three
rules cover every pipeline operation: cut a unit and the ranges split with it;
merge units and the ranges union; text the pipeline *writes* carries no ranges at
all and can never satisfy an answer check (it costs budget; it cannot score).
Formal statement and the composition lemma: `docs/formal_properties.md`.

## Layout

| Path | Contents |
|---|---|
| `src/` | the apparatus: chunkers (incl. the formatter and contextual variants), provenance scoring, retrieval, judge rubric, stats |
| `scripts/` | experiment drivers and analysis utilities |
| `v18/ v19/ v110/ v111/` | self-contained code for experiments v1.8–v1.11 |
| `tests/` | unit tests (plus per-experiment tests under `v1*/tests/`) |
| `config/` | conditions (C0–C5) and corpus tracks |
| `record/preregistrations/` | frozen pre-registrations — written and committed **before** results existed |
| `record/plans/` | the eleven experiment plans, v1.1 through v1.11 |
| `record/results/` | closed results documents for every experiment |
| `record/rulings/` | every deviation, defect and decision, ruled on in writing |
| `results*/ v1*/results_*` | raw outputs: every model reply, ledger, census and manifest the programme produced |

## Reproducing

Environment: Python 3.12; `pip install -r requirements.txt`. Corpora are
**generated, not stored**: Track A is synthetic (built by
`src/datasets/track_a_synthetic.py`, fixed seeds), Track B is constructed from
public sources at build time by `src/datasets/track_b_public.py` (QASPER,
CC BY 4.0). One qualification: the frozen v1.8 experiment records embed
retrieved QASPER passages, because the record of what the models were shown is
part of the reproducibility claim -- see `DATA_LICENSES.md` for attribution.

The token budget's meter is pinned *by this repository*: `count_tokens` in
`src/textutil.py` — a deliberate regex approximation (word + punctuation units),
applied identically to every arm of every experiment, so budgets are comparable
across conditions and reproducible without any external tokenizer dependency.
"1,920 tokens" everywhere in the paper means 1,920 of these units.

Scoring and statistics are deterministic: fixed seeds (bootstrap/permutation:
10,000 iterations, seed 1337), exact counts, and per-query artifacts sufficient
to re-derive every published number from the raw outputs in this repository.
Model-dependent stages (generation, judging) require API access and pin their
model identifiers in the experiment configs; every call's model was asserted
against the response at run time.

Run the unit tests with `pytest`.

## Reading the record

The claim "internally pre-specified" is checkable here: pre-registrations and
plans were frozen in version control before results existed, and every deviation
an execution encountered — including our own defects — is ruled on in writing in
`record/rulings/`. The record retains what a curated repository would hide:
experiment v1.5 was killed for *measured harm*; v1.2 and v1.3 were rejected; a
wrong-model probe response was voided and preserved
(`v19/results_run/probe_VOID_wrong_model.json`), as was an invalidated v1.8 probe
(`v18/results_gate0/INVALID_wrong_model__*`). These are negative controls in both
directions: the apparatus demonstrably kills bad claims — including ours — and
the process demonstrably catches its own execution errors rather than silently
absorbing them.

## Provenance of this repository

This is independent personal work, designed, funded and executed by the author
without employer resources. In the historical record (`record/`), a handful of
references to the author's employer — process notes about internal approval and
IP review — have been generalized ("the internal report", "the pending IP
ruling") for this public copy; no content, figure or verdict was altered. The
private record retains the originals verbatim.

## Reproducing

Verified on a clean checkout (fresh clone, fresh virtualenv, no caches):
`pip install -r requirements.txt` then `make test` — 212 tests pass offline in
seconds. `make smoke` runs the full pipeline end to end with zero paid LLM calls
(rule-based formatter stub, `--provider none`) and re-derives retrieval metrics
deterministically. One additional test module (`tests/test_pw1_safe_encode.py`)
and any real embedding run require network access to Hugging Face to fetch the
embedding model on first use; run `pytest --ignore=tests/test_pw1_safe_encode.py`
in restricted environments.

## Status

Released alongside the preprint. Code and record: Apache-2.0 (see
`LICENSE`). Embedded QASPER passages: CC BY 4.0 (see `DATA_LICENSES.md`).
