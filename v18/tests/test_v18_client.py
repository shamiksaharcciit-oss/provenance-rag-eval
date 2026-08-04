"""PF-10 / Gate 0(b) §2 — `V18Client`'s pin, its payloads, and the drift guard.

The drift guard is the interesting one. `V18Client._call_anthropic` cannot re-enter its parent
to get `response.model` — the parent does not retain the SDK response — so it reproduces the
parent's call and truncation contract. That duplication is a second procedure for one quantity,
which A5b exists to forbid, and the only honest mitigation where identity is unavailable is to
**bind the copy to its source**: hash the parent's method and fail if `src/` moves underneath.

Nothing here spends. `V18Client` only contacts a provider inside `_call_anthropic`, so payload
construction, the pin, and the guards are all testable for free.
"""
from __future__ import annotations

import hashlib
import inspect

import pytest

from src.llm.client import LLMClient
from v18.client import (V18_CALL_MODEL, ModelNotAsConfigured, ModelPinViolated, V18Client,
                        guarded_cost_check)


def _client(**kw):
    kw.setdefault("provider", "anthropic")
    kw.setdefault("model", V18_CALL_MODEL)
    return V18Client(**kw)


# ------------------------------------------------------------------ the drift guard


PARENT_CALL_SHA256 = hashlib.sha256(
    inspect.getsource(LLMClient._call_anthropic).encode()).hexdigest()


def test_parent_provider_call_has_not_drifted():
    """If `src/llm/client.py`'s provider call changes, the v18 copy must be re-reviewed.

    This test failing is not a bug in v18 — it is the signal that the thing v18 duplicated has
    moved, and that the duplicate needs looking at. Update the digest deliberately, never
    reflexively.
    """
    current = hashlib.sha256(inspect.getsource(LLMClient._call_anthropic).encode()).hexdigest()
    assert current == PARENT_CALL_SHA256, (
        "LLMClient._call_anthropic changed. V18Client reproduces its call and truncation "
        "contract; re-review v18/client.py before updating this digest.")


def test_v18_client_is_a_subclass_so_the_cost_guard_still_binds():
    """Gate 0(b) §2: the subclass pattern exists *specifically* so the guard keeps applying."""
    assert issubclass(V18Client, LLMClient)
    c = _client(max_llm_calls=5, max_usd=1.0)
    assert c.max_llm_calls == 5 and c.max_usd == 1.0


# ---------------------------------------------------------------------- payloads (PF-9)


def test_payload_carries_no_sampling_parameters():
    """G9: the pinned model rejects `temperature`; a parameter that cannot be sent must not be
    constructed, recorded, or implied."""
    p = _client().build_payload("prompt", "system")
    assert "temperature" not in p
    assert "top_p" not in p and "top_k" not in p


def test_payload_shape_is_the_frozen_request():
    p = _client().build_payload("the prompt", "the system")
    assert p["model"] == V18_CALL_MODEL
    assert p["thinking"] == {"type": "disabled"}
    assert p["system"] == "the system"
    assert p["messages"] == [{"role": "user", "content": "the prompt"}]


def test_payload_digest_is_order_independent_and_content_sensitive():
    c = _client()
    a = c.build_payload("x", "s")
    b = dict(reversed(list(a.items())))
    assert V18Client.payload_digest(a) == V18Client.payload_digest(b)
    assert V18Client.payload_digest(a) != V18Client.payload_digest(c.build_payload("y", "s"))


def test_identical_repeats_produce_identical_payloads():
    """The reason the payload cache is banned in batch mode: repeats are indistinguishable by
    payload, so only `custom_id` can keep them apart (PF-12 §2)."""
    c = _client()
    assert V18Client.payload_digest(c.build_payload("q", "")) == \
           V18Client.payload_digest(c.build_payload("q", ""))


# --------------------------------------------------------------------------- the pin


def test_served_model_constancy_is_asserted():
    c = _client()
    c.observe_served_model("claude-sonnet-5")
    c.observe_served_model("claude-sonnet-5")
    assert c.pin_record()["served_model_constant"] is True
    with pytest.raises(ModelPinViolated, match="changed mid-run"):
        c.observe_served_model("claude-opus-4-8")


def test_configured_model_must_not_come_from_a_default():
    """G11: config fall-through is how the probe measured the wrong model."""
    _client().assert_configured_model()
    with pytest.raises(ModelNotAsConfigured, match="harness default"):
        _client(model="claude-opus-4-8").assert_configured_model()


def test_pin_record_reports_the_window_and_states_no_sampling_parameters():
    c = _client()
    c.observe_served_model("claude-sonnet-5")
    rec = c.pin_record()
    assert rec["requested_model"] == V18_CALL_MODEL
    assert rec["served_models"] == ["claude-sonnet-5"]
    assert rec["n_calls_observed"] == 1
    assert len(rec["run_window_utc"]) == 2
    assert rec["sampling_parameters"]["sent"] == []


# ------------------------------------------------------------------ the guard, batched


def test_guarded_cost_check_refuses_a_batch_that_would_pass_max_calls():
    from src.llm.client import CostGuardExceeded
    c = _client(max_llm_calls=100)
    guarded_cost_check(c, 100)
    with pytest.raises(CostGuardExceeded, match="max_llm_calls"):
        guarded_cost_check(c, 101)


def test_guarded_cost_check_refuses_when_usd_already_exceeded():
    from src.llm.client import CostGuardExceeded
    c = _client(max_usd=0.0)
    c.input_tokens = 1_000_000
    with pytest.raises(CostGuardExceeded, match="max_usd"):
        guarded_cost_check(c, 1)
