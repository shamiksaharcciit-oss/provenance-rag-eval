"""v1.11 pre-submission tests (§6): the full custom_id cross-product against the imported
acceptor, and an intent-record round trip. Neither calls a model.

These run BEFORE any submission. A malformed id or a mis-shaped intent record discovered after
2,112 requests are in flight is discovered too late.
"""
from __future__ import annotations

import json

import pytest

import v18.batch as v18batch
from v111.ids import EXPS, custom_id, parse_custom_id
from v18.batch import CUSTOM_ID_MAX, CUSTOM_ID_PATTERN, BatchRunner, request_set_digest

N = 176


def full_cross_product() -> list[str]:
    """The plan's call table, expanded — 2,112 ids, derived not enumerated by hand."""
    plan = ([("ea", a, v) for a in ("f768", "u768") for v in ("xdoc", "sdoc")]
            + [("eb", a, "frozen") for a in ("f768", "u768")]
            + [("ec", a, v) for a in ("f768", "u768") for v in ("v1", "v2")]
            + [("ee", a, "frozen") for a in ("f768", "c768")])
    return [custom_id(e, a, i, v) for (e, a, v) in plan for i in range(N)]


def test_cross_product_is_the_planned_size():
    ids = full_cross_product()
    assert len(ids) == 2112, f"call table expands to {len(ids)}, plan says 2,112"


def test_every_id_satisfies_the_imported_acceptor():
    """The API's rule, imported by identity from v1.8 — one definition in the repository."""
    for cid in full_cross_product():
        assert CUSTOM_ID_PATTERN.match(cid), cid
        assert len(cid) <= CUSTOM_ID_MAX, cid


def test_every_id_is_unique():
    ids = full_cross_product()
    assert len(set(ids)) == len(ids)


def test_every_id_round_trips_to_its_coordinates():
    for cid in full_cross_product():
        d = parse_custom_id(cid)
        assert d["exp"] in EXPS and 0 <= d["index"] < N
        assert custom_id(d["exp"], d["arm"], d["index"], d["variant"], d["rep"]) == cid


def test_v18_ids_and_v111_ids_do_not_collide():
    v111 = set(full_cross_product())
    assert not any(c.startswith("v18-") for c in v111)


# ------------------------------------------------------------------ intent-record round trip

class _FakeAPI:
    """Records submissions; returns a batch id. No network."""

    def __init__(self):
        self.submitted = []

    def create(self, requests=None, **kw):
        self.submitted.append(requests)
        return type("B", (), {"id": f"msgbatch_fake{len(self.submitted)}"})()


class _FakeClient:
    calls = 0
    cache_hits = 0
    model = "claude-sonnet-5"
    # the real guard runs against these; the fake carries them rather than bypassing it
    max_llm_calls = 100000
    max_usd = 60.0
    est_usd = 0.0
    input_tokens = 0
    output_tokens = 0

    @staticmethod
    def build_payload(prompt, system=""):
        return {"model": "claude-sonnet-5", "max_tokens": 1024, "system": system,
                "thinking": {"type": "disabled"},
                "messages": [{"role": "user", "content": prompt}]}

    @staticmethod
    def payload_digest(p):
        import hashlib
        return hashlib.sha256(json.dumps(p, sort_keys=True).encode()).hexdigest()

    def pin_record(self):
        return {"requested_model": self.model}


def test_intent_record_is_written_before_submission_and_carries_the_id_after(tmp_path):
    api = _FakeAPI()
    r = BatchRunner(_FakeClient(), ledger=None, out_dir=tmp_path, api=api)
    reqs = [{"custom_id": custom_id("ea", "f768", i, "sdoc"),
             "params": _FakeClient.build_payload(f"p{i}")} for i in range(3)]
    bid = r.adopt_or_submit("ea", reqs)
    intents = json.loads((tmp_path / "batch_intents.json").read_text(encoding="utf-8"))
    assert bid.startswith("msgbatch_")
    entry = [e for e in intents if e.get("stage") == "ea"][-1]
    assert entry["batch_id"] == bid
    assert entry["n_requests"] == 3
    assert entry["request_set_sha256"] == request_set_digest(reqs)
    assert entry["state"] == "submitted" and entry["submitted_utc"]


def test_resubmitting_the_same_set_adopts_rather_than_paying_twice(tmp_path):
    api = _FakeAPI()
    r = BatchRunner(_FakeClient(), ledger=None, out_dir=tmp_path, api=api)
    reqs = [{"custom_id": custom_id("eb", "u768", i, "frozen"),
             "params": _FakeClient.build_payload(f"p{i}")} for i in range(4)]
    first = r.adopt_or_submit("eb", reqs)
    second = r.adopt_or_submit("eb", reqs)
    assert first == second, "an identical set must adopt the existing batch, not resubmit"
    assert len(api.submitted) == 1, "a second submission would pay twice"


def test_digest_is_order_independent():
    a = [{"custom_id": "v111-ea-f768-q000-sdoc-r0", "params": _FakeClient.build_payload("x")},
         {"custom_id": "v111-ea-u768-q000-sdoc-r0", "params": _FakeClient.build_payload("y")}]
    assert request_set_digest(a) == request_set_digest(list(reversed(a)))


def test_batch_module_is_imported_read_only_by_identity():
    """v111 uses v1.8's objects, not copies of them."""
    from v111 import requests_build  # noqa: F401
    import v18.batch as again
    assert again is v18batch
    assert again.CUSTOM_ID_PATTERN is CUSTOM_ID_PATTERN
