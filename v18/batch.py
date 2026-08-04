"""v1.8 PF-12 — Batch API execution for every test-set model call.

Batching changes *when* calls run, never *what* they contain: the same model, pins, prompts and
call counts as the frozen real-time design, at half the per-token price. Requests are built by
`V18Client.build_payload`, the one constructor, so "the batch input carries true payloads" is
true by construction rather than by inspection.

Four things this module is responsible for, each answering a specific way the run could go
wrong:

**`custom_id` is identity, and the payload cache is banned.** The 3× repeats are byte-identical
payloads. Any payload-keyed store collapses them into one sample — that is G2 returning in new
clothing, and it gets the same treatment: `assert_no_cache_traffic` fails the stage if the
shared cache was read or written at all. The record is the API's own result rows, keyed by
`custom_id`, persisted verbatim with a SHA-256 in the manifest.

**Partial failure is expected, not exceptional.** Per-request `errored` rows are collected,
resubmitted under their original `custom_id`s, and bounded at two rounds per stage. A request
still failing after that is a STOP carrying the row-level errors — never a silent drop, because
a missing query silently shrinks `n` and `F_BIAS` is declared over all 176.

**Submission is idempotent.** The failure mode is a runner that dies after submitting and before
recording, then resubmits on restart and pays twice. An intent record (stage, request count,
request-set digest) is written *before* submission and the returned batch id immediately after.
On restart an intent with no id triggers adoption by match, and anything ambiguous is a STOP.

**Batches are checkpoints.** A batch id is a durable pointer to results retrievable for 29 days,
so a crash, credit death, or machine loss between submission and collection loses nothing —
resume is a re-fetch. This structurally retires the failure that discarded 194 calls of finished
work during Gate 0.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

from v18.client import V18Client, guarded_cost_check
from v18.codebook import (ARM_CODES, CODE_TO_ARM, CODE_TO_METRIC, CODE_TO_STAGE, INDEX,
                          INDEX_WIDTH, METRIC_CODES, STAGE_CODES, TRACKS, call_plan)

#: PF-12 §1 — conservative partition well under the API's 100,000-request cap.
SUBBATCH_MAX = 10_000

#: PF-12 §3 — resubmission rounds per stage, then STOP.
MAX_RESUBMIT_ROUNDS = 2

#: Terminal per-row outcomes the API reports.
SUCCEEDED, ERRORED, CANCELED, EXPIRED = "succeeded", "errored", "canceled", "expired"

#: PF-13 / G12 §3 — intent states. `submitted` means an id may exist and adoption applies;
#: `rejected` means the API refused the set outright, so a fresh submission is not a duplicate.
SUBMITTED, REJECTED = "submitted", "rejected"

class BatchIntentAmbiguous(RuntimeError):
    """An orphaned intent matched zero or several live batches. STOP, never resubmit."""


class ResubmissionExhausted(RuntimeError):
    """Rows still failing after the bounded rounds. STOP with the row-level errors."""


class PayloadCacheTouched(AssertionError):
    """Batch mode read or wrote the shared response cache. The repeats are not independent."""


# ------------------------------------------------------------------------------ custom_id


#: The API's limit and alphabet for `custom_id`. Both are the acceptor's, not ours.
CUSTOM_ID_MAX = 64
CUSTOM_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def custom_id(stage: str, track: str, arm: str, query_id: str,
              metric: str | None = None, answer: int = 0, sub: int = 0) -> str:
    """`v18-{stage}-{track}-{arm}-q{index}-{metric}-a{answer}-s{sub}` (PF-15).

    e.g. `v18-j1-B-u768-q149-cp-a0-s4`.

    **Two coordinates, because the domain has two.** `{answer}` is which generated answer a
    judgement concerns (0-2 on the targeted pair, 0 elsewhere); `{sub}` is the position within
    that metric's own call plan (0-4 for context precision's per-context calls, 0-2 for answer
    relevancy's samples, 0 where the metric issues one call). They are orthogonal: context
    precision's five calls attach to *contexts* and to no answer, while answer relevancy's three
    attach to *each* answer. G14 collapsed them into one field and the grammar could not
    express the call plan.

    Every field is still a closed, hyphen-free vocabulary, so the uniform split stays
    unambiguous by construction, and the metric table remains a bijection onto the five metric
    names — untouched.
    """
    idx = INDEX.index_of(track, query_id)
    cid = "-".join([
        "v18",
        STAGE_CODES[stage],
        track,
        ARM_CODES[arm],
        f"q{idx:0{INDEX_WIDTH}d}",
        METRIC_CODES[metric],
        f"a{answer}",
        f"s{sub}",
    ])
    assert CUSTOM_ID_PATTERN.match(cid), (
        f"custom_id {cid!r} violates the API's pattern {CUSTOM_ID_PATTERN.pattern}")
    return cid


def parse_custom_id(cid: str) -> dict:
    """Uniform split — every field is closed, so there is nothing to disambiguate."""
    parts = cid.split("-")
    assert len(parts) == 8 and parts[0] == "v18", f"not a v18 custom_id: {cid!r}"
    _, stage, track, arm, qfield, metric, afield, sfield = parts
    assert qfield.startswith("q") and afield.startswith("a") and sfield.startswith("s"), (
        f"malformed custom_id: {cid!r}")
    index = int(qfield[1:])
    return {"stage": CODE_TO_STAGE[stage], "track": track, "arm": CODE_TO_ARM[arm],
            "query_index": index, "query_id": INDEX.id_of(track, index),
            "metric": CODE_TO_METRIC[metric], "answer": int(afield[1:]), "sub": int(sfield[1:])}


def legal_coordinates(reps_for) -> list[tuple[str, str, str, int, int]]:
    """The DERIVED validity set: every legal `(stage, arm-role, metric, answer, sub)` tuple.

    Generated **from** `call_plan()` and the targeted-pair spec — the same objects the request
    builder uses — so the acceptance census and the call plan cannot disagree: one is a function
    of the other. That is G14's ruling applied to the census itself.

    `reps_for(track, arm)` supplies how many generated answers exist for that cell.
    """
    out = []
    for track in TRACKS:
        for arm in ARM_CODES:
            reps = reps_for(track, arm)
            for stage, metric, n_sub, concerns_answer in call_plan():
                answers = range(reps) if concerns_answer else (0,)
                for a in answers:
                    for sub in range(n_sub):
                        out.append((stage, track, arm, metric, a, sub))
    return out


def request_set_digest(requests: list[dict]) -> str:
    """Digest over (custom_id, payload) pairs, order-independent.

    Sorted so that a resubmission built in a different order still recognises itself, which is
    what makes the idempotency match in `adopt_or_submit` meaningful.
    """
    items = sorted((r["custom_id"], V18Client.payload_digest(r["params"])) for r in requests)
    return hashlib.sha256(json.dumps(items).encode()).hexdigest()


def build_requests(client: V18Client, spec: list[dict]) -> list[dict]:
    """Turn (ids, prompt, system) specs into batch requests via the one payload constructor.

    Every `spec` entry is `{custom_id, prompt, system}`. Uniqueness of `custom_id` is asserted
    here: two requests sharing an id would make one of the two results unrecoverable.
    """
    seen: set[str] = set()
    out = []
    for s in spec:
        cid = s["custom_id"]
        assert cid not in seen, f"duplicate custom_id {cid!r}"
        seen.add(cid)
        out.append({"custom_id": cid,
                    "params": client.build_payload(s["prompt"], s.get("system", ""))})
    return out


# --------------------------------------------------------------------------- the runner


class BatchRunner:
    """Submits, adopts, collects and resubmits — with the ledger and the pin kept current."""

    def __init__(self, client: V18Client, ledger, out_dir: Path, api=None,
                 poll_seconds: int = 60, sleep=time.sleep):
        self.client = client
        self.ledger = ledger
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.intents_path = self.out_dir / "batch_intents.json"
        self._api = api
        self.poll_seconds = poll_seconds
        self._sleep = sleep

    # ------------------------------------------------------------------------ plumbing

    @property
    def api(self):
        """The SDK's batches namespace. Injected in tests; resolved lazily in production."""
        if self._api is None:
            import os

            import anthropic
            key = os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                raise RuntimeError("ANTHROPIC_API_KEY not set")
            self._api = anthropic.Anthropic(api_key=key).messages.batches
        return self._api

    def _intents(self) -> list[dict]:
        if not self.intents_path.exists():
            return []
        return json.loads(self.intents_path.read_text(encoding="utf-8"))

    def _write_intents(self, intents: list[dict]) -> None:
        self.intents_path.write_text(json.dumps(intents, indent=2), encoding="utf-8")

    def assert_no_cache_traffic(self, before: tuple[int, int]) -> None:
        """PF-12 §2 — batch mode must not touch the payload cache at all."""
        if (self.client.calls, self.client.cache_hits) != before:
            raise PayloadCacheTouched(
                f"batch stage changed the client's call/cache counters "
                f"{before} -> {(self.client.calls, self.client.cache_hits)}; the repeats would "
                f"not be independent samples (PF-12 §2).")

    # --------------------------------------------------------------- idempotent submission

    def adopt_or_submit(self, stage: str, requests: list[dict]) -> str:
        """Return a batch id for `requests`, adopting an orphaned submission rather than paying
        twice. The protocol is PF-12 §4, in order."""
        digest = request_set_digest(requests)
        intents = self._intents()

        for entry in intents:
            if entry["stage"] == stage and entry["request_set_sha256"] == digest:
                if entry.get("batch_id"):
                    return entry["batch_id"]                      # already submitted, known
                if entry.get("state") == REJECTED:
                    # G12 §3: the API refused this set outright, so nothing exists to adopt and
                    # a fresh submission is not a duplicate. Without this the adoption logic
                    # conflates "rejected" with "died after submitting" and STOPs a legitimate
                    # retry — which is exactly what the Batch G rejection produced.
                    break
                return self._adopt_orphan(entry, requests, intents)

        # No adoptable prior intent: write one BEFORE submitting, so a death here is recoverable.
        entry = {"stage": stage, "n_requests": len(requests),
                 "request_set_sha256": digest, "batch_id": None, "state": SUBMITTED,
                 "submitted_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        intents.append(entry)
        self._write_intents(intents)

        guarded_cost_check(self.client, len(requests))
        try:
            batch = self.api.create(requests=requests)
        except Exception as e:
            # A synchronous refusal is terminal for this intent and nothing was created. Record
            # that, so the next attempt submits rather than hunting for a batch that never was.
            entry["state"] = REJECTED
            entry["rejected_reason"] = f"{type(e).__name__}: {str(e)[:200]}"
            self._write_intents(intents)
            raise
        entry["batch_id"] = getattr(batch, "id", None) or batch["id"]
        self._write_intents(intents)
        return entry["batch_id"]

    def _adopt_orphan(self, entry: dict, requests: list[dict], intents: list[dict]) -> str:
        """An intent with no batch id: the runner died between submit and record.

        Match on request count and a sampled `custom_id`. Exactly one match is adopted; zero or
        several is a STOP, because resubmitting-by-default is precisely the duplicate spend the
        intent record exists to prevent.
        """
        assert entry.get("state", SUBMITTED) == SUBMITTED, (
            f"adoption attempted on a {entry.get('state')!r} intent; only submitted intents "
            f"can have produced a batch (G12 §3)")
        sample = requests[0]["custom_id"]
        candidates = []
        for batch in self.api.list(limit=50):
            bid = getattr(batch, "id", None) or batch["id"]
            counts = getattr(batch, "request_counts", None)
            total = _total_requests(counts)
            if total is not None and total != entry["n_requests"]:
                continue
            try:
                ids = {getattr(r, "custom_id", None) or r["custom_id"]
                       for r in self.api.results(bid)}
            except Exception:
                continue
            if sample in ids:
                candidates.append(bid)

        if len(candidates) == 1:
            entry["batch_id"] = candidates[0]
            entry["adopted"] = True
            self._write_intents(intents)
            return candidates[0]
        raise BatchIntentAmbiguous(
            f"orphaned intent for stage {entry['stage']!r} ({entry['n_requests']} requests) "
            f"matched {len(candidates)} live batches: {candidates}. STOP for a ruling — "
            f"resubmitting by default is how a run pays twice (PF-12 §4).")

    # ------------------------------------------------------------------------ collection

    def wait_and_collect(self, batch_id: str,
                         stage: str) -> tuple[dict, list[dict], dict[str, str]]:
        """Block until the batch ends, then persist rows verbatim and split by outcome."""
        while True:
            status = getattr(self.api.retrieve(batch_id), "processing_status", None)
            if status == "ended":
                break
            self._sleep(self.poll_seconds)

        rows = list(self.api.results(batch_id))
        raw_path = self.out_dir / f"{stage}_{batch_id}.jsonl"
        with raw_path.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(_row_to_dict(row), ensure_ascii=False) + "\n")
        digest = hashlib.sha256(raw_path.read_bytes()).hexdigest()

        succeeded, failed = {}, []
        in_tok = out_tok = 0
        for row in rows:
            cid = getattr(row, "custom_id", None) or row["custom_id"]
            result = getattr(row, "result", None) or row["result"]
            rtype = getattr(result, "type", None) or result["type"]
            if rtype == SUCCEEDED:
                msg = getattr(result, "message", None) or result["message"]
                text = _text_of(msg)
                served = getattr(msg, "model", None) or _get(msg, "model", "<absent>")
                self.client.observe_served_model(served)          # PF-5 across all rows
                usage = getattr(msg, "usage", None) or _get(msg, "usage", {})
                in_tok += _get(usage, "input_tokens", 0)
                out_tok += _get(usage, "output_tokens", 0)
                succeeded[cid] = text
            else:
                failed.append({"custom_id": cid, "type": rtype,
                               "error": _error_of(result)})

        self.ledger.record(stage=stage, calls=len(succeeded), input_tokens=in_tok,
                           output_tokens=out_tok, batch_id=batch_id,
                           note=f"raw rows sha256={digest[:16]}")
        return {"batch_id": batch_id, "raw_path": str(raw_path), "raw_sha256": digest,
                "n_succeeded": len(succeeded), "n_failed": len(failed),
                "input_tokens": in_tok, "output_tokens": out_tok}, failed, succeeded

    # ---------------------------------------------------------------------- stage driver

    def run_stage(self, stage: str, requests: list[dict]) -> dict:
        """Submit, collect, and resubmit failures within the bounded rounds."""
        before = (self.client.calls, self.client.cache_hits)
        pending = list(requests)
        answers: dict[str, str] = {}
        batches: list[dict] = []
        round_no = 0

        while pending:
            label = stage if round_no == 0 else f"{stage}-retry{round_no}"
            for chunk_idx, chunk in enumerate(_chunks(pending, SUBBATCH_MAX)):
                sub = label if len(pending) <= SUBBATCH_MAX else f"{label}-part{chunk_idx}"
                bid = self.adopt_or_submit(sub, chunk)
                meta, failed, ok = self.wait_and_collect(bid, sub)
                meta["stage"] = sub
                batches.append(meta)
                answers.update(ok)
                batches[-1]["failed_rows"] = failed
            # Pending is recomputed from what is still MISSING rather than from the failure
            # list, so a row that succeeded on any round is never resubmitted.
            pending = [r for r in requests if r["custom_id"] not in answers]
            if not pending:
                break
            round_no += 1
            if round_no > MAX_RESUBMIT_ROUNDS:
                raise ResubmissionExhausted(
                    f"{len(pending)} request(s) still failing after {MAX_RESUBMIT_ROUNDS} "
                    f"resubmission rounds in stage {stage!r}. STOP — a dropped request would "
                    f"silently shrink n (PF-12 §3). Row-level errors: "
                    f"{[f for b in batches for f in b.get('failed_rows', [])][:20]}")

        self.assert_no_cache_traffic(before)
        return {"stage": stage, "batches": batches, "answers": answers,
                "n_requests": len(requests), "n_answers": len(answers),
                "resubmission_rounds_used": round_no,
                "pin": self.client.pin_record()}


# ------------------------------------------------------------------------------- helpers


def _chunks(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def _get(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _total_requests(counts) -> int | None:
    if counts is None:
        return None
    return sum(_get(counts, k, 0) for k in
               ("processing", "succeeded", "errored", "canceled", "expired"))


def _text_of(msg) -> str:
    content = _get(msg, "content", []) or []
    return "".join(_get(b, "text", "") for b in content if _get(b, "type", "") == "text")


def _error_of(result) -> str:
    err = _get(result, "error", None)
    if err is None:
        return ""
    return str(_get(err, "type", err))


def _row_to_dict(row) -> dict:
    """Persist the row verbatim where possible; fall back to a structural copy."""
    for attr in ("to_dict", "model_dump"):
        fn = getattr(row, attr, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                pass
    if isinstance(row, dict):
        return row
    result = _get(row, "result", None)
    return {"custom_id": _get(row, "custom_id"),
            "result": {"type": _get(result, "type"),
                       "error": _error_of(result) or None}}
