# v1.8 PF-12 — Batch API execution mode: design and ruling

**Status:** pre-freeze amendment to v1.8, authorised by Shamik ("design for the batch api
route"). Applies to v1.8 only. **v1.9 is frozen at `5bc4aeb` and is untouched** — its
real-time execution and pinned client are sealed; changing them would be unfreezing, so its
~$12 stands.
**Date:** 1 August 2026
**Effect:** all v1.8 test-set model calls (generation and judging, repeats included) move to
the Anthropic Message Batches API — same model, same pins, same prompts, same call counts,
**half the per-token price**. Verified facts the design relies on: 50% off all per-token
rates, up to 100,000 requests per batch, ≤24 h processing target (typically much faster),
results retrievable 29 days, per-request `succeeded`/`errored` rows so one failure never
fails a batch, and prompt caching composes with the discount.

Projected v1.8 cost: **~$25–35 true** (from ~$50–70). Combined with v1.9, total programme
spend ~$40–50; a $60–70 top-up is comfortable.

---

## 1. Execution pipeline — batches follow stage dependencies, nothing else

Stage order is forced by data dependency only:

1. **Batch G** — all generation: every (track, arm, query) plus the Track A `F768`/`U768`
   3× repeats, as independent requests in one batch (~1,682 requests).
2. Collect G; score F1 (local, free); construct judge inputs.
3. **Batch J** — all judge calls, repeats included (~16k requests; split into ≤10,000-request
   sub-batches in `custom_id` order as a conservative partition, well under the 100k cap).
4. Collect J; compute contrasts; results document.

Blinding and order-randomisation happen at request construction, exactly as frozen —
batching changes *when* calls run, never *what* they contain.

## 2. `custom_id` is the identity, and the payload cache is banned from batch mode

Every request carries a deterministic
`custom_id = v18:{stage}:{track}:{arm}:{query_id}:{metric|-}:{rep}`.

**The response cache is not consulted and not written in batch mode.** This is G2's ghost
returning in new clothing and it gets the same stake through it: the 3× repeats are
byte-identical payloads, so any payload-keyed store collapses them back into one sample.
The batch result store — the API's own JSONL, persisted verbatim, SHA-256 in the manifest —
is keyed by `custom_id` and is the sole record. A test asserts that repeat results are
distinct rows and that batch mode performs zero payload-cache reads or writes.

## 3. Partial failure, retries, and the STOP

Per-request `errored` rows are expected, not exceptional. Handling: collect succeeded rows;
resubmit failed rows in a follow-up batch (same `custom_id`s); **maximum two resubmission
rounds per stage**. A request still failing after that is a STOP with the row-level errors
in the report — not a silent drop, because a missing query would silently shrink n and the
family is declared over all 176.

## 4. Idempotent submission — the duplicate-spend guard

The failure mode: runner dies after submitting, before recording, resubmits on restart,
pays twice. Protocol: write an **intent record** (stage, request count, request-set
SHA-256) to the manifest *before* submission; write the returned batch id beside it
immediately after. On restart, an intent without a batch id means: list recent batches,
match by request count and a sampled `custom_id`; an unambiguous match adopts that batch,
anything ambiguous is a STOP for a ruling — never a resubmission by default.

## 5. Ledger, guard, and pins under batch mode

- **Spend ledger:** updated at collection from the API's per-row usage figures — actuals,
  not estimates. Call counts are unchanged by batching (17,642 projection, 25,000 ceiling,
  breach is a STOP, all as frozen).
- **Cost guard:** `max_usd` 150 as-computed stands. The guard's pricing model knows neither
  the Sonnet rate nor the batch discount — it is like-for-like inflated, which is exactly
  how PF-4/G4 left it, and the discount is *not* modelled into it (documented, per that
  ruling: the guard is a tripwire, not an invoice).
- **Model pin:** stronger under batch — every result row carries the served model; PF-5's
  constancy assertion runs across all rows of all batches. Config still names both model
  roles explicitly; no default resolution (G11 ruling unchanged).
- **Payloads:** `V18Client` writes actual request payloads into the batch input (G9 ruling
  unchanged — no temperature parameter, none recorded).

## 6. Checkpointing comes free — batches are the checkpoints

Batch ids in the manifest are durable pointers to 29-day-retrievable results, so a crash,
credit death, or machine loss between submission and collection loses nothing: resume =
re-fetch by id. This structurally retires the attempt-3 failure mode (194 calls of finished
work discarded), and the §5-of-Gate-0(b) affordability check runs once per stage, against
the ledger, before each submission.

## 7. What batching costs: wall clock, and one discipline note

Worst case is ~24 h per batch round; with two stages and up to two retry rounds each, the
pessimistic envelope is a few days, the typical case hours. Two consequences, accepted:

- **v1.9 waits longer.** The spend-sequencing rule — no v1.9 call until v1.8's results
  commit exists — is unchanged. Batch mode stretches v1.8's window; the guard-attribution
  reasoning that motivated the rule stretches with it. v1.9's freeze keeps.
- **No peeking between stages.** Batch G's answers arrive complete before judging begins.
  Nobody — agent or ruling side — reads answers, F1 distributions, or any per-arm signal
  between Batch G and Batch J beyond the mechanical checks (row counts, model constancy,
  resubmission triage). The results document is assembled once, after Batch J, per the
  frozen plan. Stage gaps are where impatience reads data early; this paragraph exists so
  that it can't happen quietly.

## 8. Tests required before the freeze commit

Mocked-API unit tests: `custom_id` round-trip and uniqueness across repeats; zero
payload-cache traffic in batch mode; partial-failure resubmission with the two-round bound
and the STOP; intent-record idempotency (restart with intent-but-no-id adopts, ambiguity
stops); ledger accumulation from per-row usage; model-constancy across rows;
parent-source-hash guard on the overridden provider code, unchanged.

## 9. Freeze instruction, amended once

PF-12 joins PF-1…PF-11 in the §0 amendments table. One freeze commit as already ruled —
plan + code + prompts + tests + probe disposition + projection + the `max_usd` raise — now
including the batch client and these tests. Everything else in Gate 0(b) §7 stands
unchanged: run after the balance check, `Results_v18_InstrumentDivergence.md`, item-7
self-check with output in the record, STOP at Gate 1.
