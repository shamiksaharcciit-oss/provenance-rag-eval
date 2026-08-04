"""PF-12 §8 — the batch path's guards, against a mocked API. Spends nothing.

A fake batches namespace stands in for the SDK. That is the point: what needs testing is the
*protocol* — identity by `custom_id`, no payload-cache traffic, bounded resubmission, idempotent
submission, ledger accumulation, model constancy — and every one of those is a property of the
runner, not of the network.
"""
from __future__ import annotations

import json

import pytest

from v18.batch import (MAX_RESUBMIT_ROUNDS, REJECTED, SUBMITTED, BatchIntentAmbiguous,
                       BatchRunner, PayloadCacheTouched, ResubmissionExhausted,
                       build_requests, custom_id, parse_custom_id, request_set_digest)
from v18.codebook import INDEX
from v18.client import V18_CALL_MODEL, ModelPinViolated, V18Client
from v18.ledger import SpendLedger


# --------------------------------------------------------------------------- fake API


class FakeBatches:
    """Minimal stand-in for `client.messages.batches`."""

    def __init__(self, outcomes=None, served="claude-sonnet-5"):
        self.created: list[dict] = []
        self.outcomes = outcomes or {}          # custom_id -> "succeeded" | "errored"
        self.served = served
        self._store: dict[str, list[dict]] = {}
        self._n = 0

    def create(self, requests):
        self._n += 1
        bid = f"msgbatch_{self._n:03d}"
        rows = []
        for r in requests:
            cid = r["custom_id"]
            kind = self.outcomes.get(cid, "succeeded")
            if kind == "succeeded":
                rows.append({"custom_id": cid, "result": {
                    "type": "succeeded",
                    "message": {"model": self.served,
                                "content": [{"type": "text", "text": f"ans::{cid}"}],
                                "usage": {"input_tokens": 10, "output_tokens": 5}}}})
            else:
                rows.append({"custom_id": cid,
                             "result": {"type": "errored", "error": {"type": "api_error"}}})
        self._store[bid] = rows
        self.created.append({"id": bid, "requests": requests})
        return {"id": bid}

    def retrieve(self, bid):
        return type("B", (), {"processing_status": "ended"})()

    def results(self, bid):
        return list(self._store[bid])

    def list(self, limit=50):
        return [{"id": bid, "request_counts": {"succeeded": len(rows), "errored": 0,
                                               "processing": 0, "canceled": 0, "expired": 0}}
                for bid, rows in self._store.items()]


def _client():
    return V18Client(provider="anthropic", model=V18_CALL_MODEL)


def _qid(track, i):
    return INDEX.id_of(track, i)


def _spec(n, stage="generate", arm="F768"):
    return [{"custom_id": custom_id(stage, "A", arm, _qid("A", i), None, 0, 0),
             "prompt": f"p{i}", "system": ""}
            for i in range(n)]


def _runner(tmp_path, api, client=None):
    client = client or _client()
    ledger = SpendLedger(tmp_path / "ledger.json")
    return BatchRunner(client, ledger, tmp_path / "batches", api=api, poll_seconds=0,
                       sleep=lambda s: None), client, ledger


# ------------------------------------------------------------------------- custom_id


def test_custom_id_round_trips():
    qid = _qid("A", 17)
    cid = custom_id("judge1", "A", "F768", qid, "faithfulness", 2, 0)
    assert cid == "v18-j1-A-f768-q017-fa-a2-s0"
    got = parse_custom_id(cid)
    assert got["stage"] == "judge1" and got["track"] == "A" and got["arm"] == "F768"
    assert got["query_index"] == 17 and got["query_id"] == qid
    assert got["metric"] == "faithfulness" and got["answer"] == 2 and got["sub"] == 0


def test_generation_uses_the_metric_free_code():
    got = parse_custom_id(custom_id("generate", "B", "U256", _qid("B", 1), None, 0, 0))
    assert got["metric"] is None and got["stage"] == "generate"


def test_custom_id_is_unique_across_repeats():
    """The whole reason `custom_id` is identity: the three repeats are the same payload."""
    qid = _qid("A", 1)
    ids = {custom_id("generate", "A", "F768", qid, None, r, 0) for r in range(3)}
    assert len(ids) == 3


def test_free_text_no_longer_reaches_the_identity():
    """PF-13: the id encodes an INDEX, so an id full of illegal characters is still legal.

    `A-040-marlin-planner::syn` is a real Track A id; under PF-12's format it produced a
    custom_id the API rejected outright (G12).
    """
    qid = _qid("A", 0)
    assert "::" in qid
    cid = custom_id("generate", "A", "U256", qid, None, 0, 0)
    assert ":" not in cid
    assert parse_custom_id(cid)["query_id"] == qid


def test_an_unknown_query_id_is_refused():
    with pytest.raises(KeyError, match="frozen codebook"):
        custom_id("generate", "A", "F768", "not-a-real-id", None, 0, 0)


def test_build_requests_refuses_duplicate_ids():
    c = _client()
    cid = custom_id("generate", "A", "F768", _qid("A", 0), None, 0, 0)
    spec = [{"custom_id": cid, "prompt": "a"}, {"custom_id": cid, "prompt": "b"}]
    with pytest.raises(AssertionError, match="duplicate custom_id"):
        build_requests(c, spec)


def test_request_set_digest_is_order_independent():
    c = _client()
    a = build_requests(c, _spec(5))
    assert request_set_digest(a) == request_set_digest(list(reversed(a)))


# ------------------------------------------------------- repeats stay distinct rows (§2)


def test_repeats_are_distinct_rows_and_the_payload_cache_is_untouched(tmp_path):
    api = FakeBatches()
    runner, client, ledger = _runner(tmp_path, api)
    spec = [{"custom_id": custom_id("generate", "A", "F768", _qid("A", 1), None, r, 0),
             "prompt": "same"} for r in range(3)]
    out = runner.run_stage("gen", build_requests(client, spec))

    assert out["n_answers"] == 3, "three byte-identical payloads must yield three rows"
    assert len(set(out["answers"])) == 3
    assert (client.calls, client.cache_hits) == (0, 0), "batch mode touched the payload cache"


def test_cache_traffic_during_a_batch_stage_is_caught(tmp_path):
    api = FakeBatches()
    runner, client, _ = _runner(tmp_path, api)
    reqs = build_requests(client, _spec(2))
    client.cache_hits += 1                      # simulate a stray cached read
    with pytest.raises(PayloadCacheTouched, match="not be independent"):
        runner.assert_no_cache_traffic((0, 0))


# ------------------------------------------------------------ partial failure (§3)


def test_failed_rows_are_resubmitted_and_recovered(tmp_path):
    reqs_ids = [custom_id("generate", "A", "F768", _qid("A", i)) for i in range(4)]
    api = FakeBatches(outcomes={reqs_ids[2]: "errored"})
    runner, client, _ = _runner(tmp_path, api)
    reqs = build_requests(client, [{"custom_id": c, "prompt": "p"} for c in reqs_ids])

    api.outcomes = {reqs_ids[2]: "errored"}
    # the retry round succeeds because the fake clears the outcome after the first batch
    original_create = api.create

    def create_then_heal(requests):
        out = original_create(requests)
        api.outcomes = {}
        return out
    api.create = create_then_heal

    out = runner.run_stage("gen", reqs)
    assert out["n_answers"] == 4
    assert out["resubmission_rounds_used"] == 1


def test_persistent_failure_stops_after_the_bounded_rounds(tmp_path):
    ids = [custom_id("generate", "A", "F768", _qid("A", i)) for i in range(3)]
    api = FakeBatches(outcomes={ids[1]: "errored"})
    runner, client, _ = _runner(tmp_path, api)
    reqs = build_requests(client, [{"custom_id": c, "prompt": "p"} for c in ids])
    with pytest.raises(ResubmissionExhausted) as e:
        runner.run_stage("gen", reqs)
    assert str(MAX_RESUBMIT_ROUNDS) in str(e.value)
    assert ids[1] in str(e.value), "the STOP must carry the row-level errors, not just a count"


# --------------------------------------------------------- idempotent submission (§4)


def test_second_submission_of_the_same_set_adopts_the_recorded_batch(tmp_path):
    api = FakeBatches()
    runner, client, _ = _runner(tmp_path, api)
    reqs = build_requests(client, _spec(3))
    first = runner.adopt_or_submit("gen", reqs)
    second = runner.adopt_or_submit("gen", reqs)
    assert first == second
    assert len(api.created) == 1, "resubmitting a recorded set would pay twice"


def test_orphaned_intent_adopts_an_unambiguous_live_batch(tmp_path):
    api = FakeBatches()
    runner, client, _ = _runner(tmp_path, api)
    reqs = build_requests(client, _spec(3))
    bid = runner.adopt_or_submit("gen", reqs)

    # simulate the death: the intent exists, the id was never recorded
    intents = json.loads(runner.intents_path.read_text(encoding="utf-8"))
    intents[0]["batch_id"] = None
    runner.intents_path.write_text(json.dumps(intents), encoding="utf-8")

    adopted = runner.adopt_or_submit("gen", reqs)
    assert adopted == bid
    assert len(api.created) == 1, "adoption must not create a second batch"


def test_ambiguous_orphan_stops_rather_than_resubmitting(tmp_path):
    api = FakeBatches()
    runner, client, _ = _runner(tmp_path, api)
    reqs = build_requests(client, _spec(3))
    runner.adopt_or_submit("gen", reqs)
    api.create(reqs)                     # an identical second batch exists -> ambiguous

    intents = json.loads(runner.intents_path.read_text(encoding="utf-8"))
    intents[0]["batch_id"] = None
    runner.intents_path.write_text(json.dumps(intents), encoding="utf-8")

    with pytest.raises(BatchIntentAmbiguous, match="STOP"):
        runner.adopt_or_submit("gen", reqs)


def test_intent_is_written_before_submission(tmp_path):
    """A death between submit and record must leave a recoverable intent behind."""
    class DyingAPI(FakeBatches):
        def create(self, requests):
            raise RuntimeError("process died mid-submit")

    runner, client, _ = _runner(tmp_path, DyingAPI())
    reqs = build_requests(client, _spec(2))
    with pytest.raises(RuntimeError, match="died mid-submit"):
        runner.adopt_or_submit("gen", reqs)
    intents = json.loads(runner.intents_path.read_text(encoding="utf-8"))
    assert len(intents) == 1 and intents[0]["batch_id"] is None
    assert intents[0]["request_set_sha256"] == request_set_digest(reqs)


# ------------------------------------------------------------------- ledger + pin (§5)


def test_ledger_accumulates_from_per_row_usage(tmp_path):
    api = FakeBatches()
    runner, client, ledger = _runner(tmp_path, api)
    runner.run_stage("gen", build_requests(client, _spec(4)))
    t = ledger.totals()
    assert t["calls"] == 4
    assert t["input_tokens"] == 40 and t["output_tokens"] == 20


def test_model_constancy_is_asserted_across_batch_rows(tmp_path):
    class DriftingAPI(FakeBatches):
        def create(self, requests):
            out = super().create(requests)
            self._store[out["id"]][-1]["result"]["message"]["model"] = "claude-opus-4-8"
            return out

    runner, client, _ = _runner(tmp_path, DriftingAPI())
    with pytest.raises(ModelPinViolated, match="changed mid-run"):
        runner.run_stage("gen", build_requests(client, _spec(3)))


def test_raw_rows_are_persisted_verbatim_with_a_digest(tmp_path):
    api = FakeBatches()
    runner, client, _ = _runner(tmp_path, api)
    out = runner.run_stage("gen", build_requests(client, _spec(2)))
    meta = out["batches"][0]
    raw = (tmp_path / "batches") / f"{meta['stage']}_{meta['batch_id']}.jsonl"
    assert raw.exists()
    lines = [json.loads(x) for x in raw.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 2 and all("custom_id" in x for x in lines)
    assert len(meta["raw_sha256"]) == 64


# ----------------------------------------------------- intent states after G12 §3


def test_a_create_rejection_marks_the_intent_rejected(tmp_path):
    """The defect Batch G's rejection exposed: a refused set left an unadoptable orphan."""
    class RejectingAPI(FakeBatches):
        def create(self, requests):
            raise ValueError("custom_id: String should match pattern")

    runner, client, _ = _runner(tmp_path, RejectingAPI())
    reqs = build_requests(client, _spec(2))
    with pytest.raises(ValueError):
        runner.adopt_or_submit("gen", reqs)
    intents = json.loads(runner.intents_path.read_text(encoding="utf-8"))
    assert intents[0]["state"] == REJECTED
    assert "pattern" in intents[0]["rejected_reason"]


def test_a_rejected_intent_permits_a_fresh_submission(tmp_path):
    """A legitimate retry after a rejection must not STOP looking for a batch that never was."""
    class FirstRejects(FakeBatches):
        def __init__(self):
            super().__init__()
            self.first = True

        def create(self, requests):
            if self.first:
                self.first = False
                raise ValueError("rejected")
            return super().create(requests)

    runner, client, _ = _runner(tmp_path, FirstRejects())
    reqs = build_requests(client, _spec(2))
    with pytest.raises(ValueError):
        runner.adopt_or_submit("gen", reqs)
    bid = runner.adopt_or_submit("gen", reqs)          # must submit, not hunt
    assert bid.startswith("msgbatch_")


def test_a_genuine_post_submit_loss_still_adopts(tmp_path):
    """The rejection fix must not weaken the duplicate-spend guard it sits beside."""
    api = FakeBatches()
    runner, client, _ = _runner(tmp_path, api)
    reqs = build_requests(client, _spec(3))
    bid = runner.adopt_or_submit("gen", reqs)
    intents = json.loads(runner.intents_path.read_text(encoding="utf-8"))
    intents[0]["batch_id"] = None
    intents[0]["state"] = SUBMITTED
    runner.intents_path.write_text(json.dumps(intents), encoding="utf-8")
    assert runner.adopt_or_submit("gen", reqs) == bid
    assert len(api.created) == 1


# ------------------------------------- PF-15 generation-id migration (G14 §5)


def test_generation_ids_migrate_from_the_pf13_grammar():
    """Batch G's 1,682 rows stay valid across the grammar change — re-keyed, never re-spent."""
    from v18.run import migrate_generation_id
    assert migrate_generation_id("v18-g-A-f768-q000-na-r2") == "v18-g-A-f768-q000-na-a2-s0"
    got = parse_custom_id(migrate_generation_id("v18-g-B-u256-q149-na-r0"))
    assert got["track"] == "B" and got["arm"] == "U256"
    assert got["query_index"] == 149 and got["answer"] == 0 and got["sub"] == 0


def test_migration_is_idempotent_on_already_migrated_ids():
    from v18.run import migrate_generation_id
    new = "v18-g-A-f768-q000-na-a2-s0"
    assert migrate_generation_id(new) == new


def test_migration_refuses_to_collapse_two_rows():
    from v18.run import migrate_answers
    with pytest.raises(AssertionError, match="not injective"):
        migrate_answers({"v18-g-A-f768-q000-na-r0": "x",
                         "v18-g-A-f768-q000-na-a0-s0": "y"})
