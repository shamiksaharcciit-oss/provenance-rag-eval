"""§9/PF-2 — the probe's own guards, exercised without spending anything.

The probe exists to answer one question, and Gate 0 established that the drafted version could
only ever answer it "yes". These tests pin the two mechanisms that make a "no" reachable:
the cache bypass, and the fresh-call assertion that fires when the bypass fails.

A fake client stands in for the model. That is the point — the probe's *accounting* is what is
under test here, and it must be verifiable with zero spend and no credential.
"""
from __future__ import annotations

import pytest

from v18.probe import (PROBE_CALL_BUDGET, ModelPinViolation, ProbeBudgetExceeded,
                       ProbeCacheLeak, run_probe)


class FakeProbeClient:
    """Stands in for `ProbeClient`, with the same surface `run_probe` consumes."""

    def __init__(self, outputs, cache_hits=0, undercount=0, budget=PROBE_CALL_BUDGET):
        self._outputs = list(outputs)
        self._i = 0
        self.cache_hits = cache_hits
        self._undercount = undercount
        self.budget = budget
        self.requested_model = "claude-sonnet-5"
        self._calls = 0

    def complete(self, prompt, system=""):
        if self._calls + 1 > self.budget:
            raise ProbeBudgetExceeded(f"budget {self.budget}")
        self._calls += 1
        out = self._outputs[self._i % len(self._outputs)]
        self._i += 1
        return out

    @property
    def fresh_calls(self):
        return self._calls - self._undercount


PROMPTS = [("sys", "one"), ("sys", "two")]


def test_identical_repeats_report_byte_identical():
    client = FakeProbeClient(["same"])
    out = run_probe(PROMPTS, client, repeats=3)
    assert out["byte_identical"] is True
    assert out["divergent_prompt_indices"] == []
    assert out["fresh_calls"] == 6 == out["prompts"] * out["repeats"]


def test_a_single_divergent_repeat_is_caught():
    """The verdict the drafted probe could never reach."""
    client = FakeProbeClient(["a", "a", "a", "a", "a", "b"])
    out = run_probe(PROMPTS, client, repeats=3)
    assert out["byte_identical"] is False
    assert out["divergent_prompt_indices"] == [1]


def test_a_cached_repeat_fails_the_probe_loudly():
    """PF-2's core guard: a cache hit invalidates the verdict rather than flattering it."""
    client = FakeProbeClient(["same"], cache_hits=1)
    with pytest.raises(ProbeCacheLeak, match="served from cache"):
        run_probe(PROMPTS, client, repeats=3)


def test_missing_fresh_calls_fail_even_when_cache_hits_are_zero():
    """The second half of the assertion — a bypass can fail without incrementing cache_hits."""
    client = FakeProbeClient(["same"], undercount=2)
    with pytest.raises(ProbeCacheLeak, match="did not issue an independent call"):
        run_probe(PROMPTS, client, repeats=3)


def test_probe_refuses_to_start_beyond_the_call_budget():
    """PF-1's 1,000-call bound is checked before spending, not discovered during."""
    client = FakeProbeClient(["same"], budget=4)
    with pytest.raises(ProbeBudgetExceeded, match="probe budget"):
        run_probe(PROMPTS, client, repeats=3)


def test_probe_requires_at_least_two_repeats():
    with pytest.raises(AssertionError):
        run_probe(PROMPTS, FakeProbeClient(["same"]), repeats=1)


def test_the_reported_model_is_labelled_as_requested_not_served():
    """G10: `response.model` is unrecoverable through LLMClient, so the record must not
    imply otherwise. A pin confirmed against the value we sent is no pin at all."""
    out = run_probe(PROMPTS, FakeProbeClient(["same"]), repeats=2)
    assert out["requested_model"] == "claude-sonnet-5"
    assert "served_models" not in out
    assert "REQUESTED" in out["_served_model_note"]


def test_model_pin_violation_is_available_as_an_apparatus_stop():
    """PF-5's intended stop, kept for when a served-model source exists (see G10)."""
    assert issubclass(ModelPinViolation, AssertionError)


def test_budget_constant_matches_the_ruling():
    assert PROBE_CALL_BUDGET == 1000


def test_probe_client_does_not_point_at_the_shared_cache():
    """The bypass, demonstrated on the real object rather than asserted in a docstring.

    Constructing a `ProbeClient` spends nothing — `LLMClient` only contacts a provider inside
    `complete()`. So the one property that makes the whole probe meaningful (its cache is not
    the shared one) is checkable here for free.
    """
    from pathlib import Path

    from src import config as C
    from v18.probe import ProbeClient

    cfg = C.load_default()
    cfg["llm"]["provider"] = "anthropic"
    shared = Path(cfg.get("_cache_root", "cache")).resolve()

    probe = ProbeClient(cfg)
    try:
        probe_dir = Path(probe.client.cache_dir).resolve()
        assert probe_dir.exists()
        assert shared not in probe_dir.parents and probe_dir != shared, (
            f"probe cache {probe_dir} sits under the shared cache {shared}; the bypass is "
            f"cosmetic and the probe would measure the cache again (§2, PF-2)")
        assert not any(probe_dir.iterdir()), "probe cache must start empty"
        assert probe.fresh_calls == 0 and probe.cache_hits == 0
    finally:
        probe.dispose()
    assert not probe_dir.exists(), "dispose() must remove the scratch cache"
