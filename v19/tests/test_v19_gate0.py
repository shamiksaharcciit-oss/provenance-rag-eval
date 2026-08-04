"""v1.9 Gate 0 — the five required tests, plus the invariants they depend on (§7).

Required by §7: overlap-not-coverage selection; mismatched-package wiring (query *i* → package
*i*+1 exactly); the fresh-call assertion; `response.model` constancy; B2(q) equality across arms
per query.

No model is called. The generator tests drive a fake provider, so the whole of v1.9's call
machinery is exercised at Gate 0 for nothing.
"""
from __future__ import annotations

import pytest

from src.chunkers.base import Unit
from src.datasets.base import GoldSpan
from src.textutil import count_tokens
from src.v17.packages import build_package
from v19.arms import ARMS, PRIMARY_PAIR, assert_builder_identity
from v19.control import (CONTROL_N, CONTROL_SEED, b2_for_query, draw_control_sample,
                         pair_with_successor)
from v19.generate import (ModelPinViolated, ProbeServedFromCache, V19Client, determinism_probe)

D = "doc1"


def unit(i, word, n, doc=D, ranges=None):
    return Unit(unit_id=f"u{i}", text=" ".join([word] * n), doc_id=doc,
                source_ranges=ranges if ranges is not None else [(i * 10, i * 10 + 10)])


def inventory(n_units, n_tokens=100):
    return [unit(i, f"w{i}", n_tokens) for i in range(n_units)]


# ---------------------------------------------------------------- arms by import

def test_arm_builder_is_the_v16_object_not_a_copy():
    assert_builder_identity()


def test_arms_are_the_declared_three_with_the_primary_pair_first():
    assert ARMS == ("F768", "U768", "U256")
    assert PRIMARY_PAIR == ("F768", "U768")


# ---------------------------------------------------------------- REQUIRED: overlap, not coverage

def test_selection_uses_overlap_not_coverage():
    """v1.7's whitespace defect must not reach v1.9.

    This unit's ranges have a HOLE exactly where the gold sits, so it does NOT cover the gold —
    `integrity_single` would score it 0. It still OVERLAPS, so packaging must still select it.
    """
    from src.v17.integrity import integrity_single

    holed = unit(0, "w", 100, ranges=[(0, 40), (45, 100)])   # gap at [40,45)
    gold = [GoldSpan(doc_id=D, start_char=30, end_char=60)]  # straddles the hole

    assert integrity_single([(holed.doc_id, holed.source_ranges)], gold) == 0, \
        "precondition: this unit does NOT cover the gold"
    p = build_package([holed], gold, 100)   # budget must clear the unit; 100 is its exact size
    assert p.core_unit_ids == ["u0"], "overlap-based selection must still pick it"


def test_a_unit_with_no_overlap_is_not_selected():
    inv = [unit(0, "a", 100, ranges=[(0, 10)]), unit(1, "b", 100, ranges=[(500, 600)])]
    p = build_package(inv, [GoldSpan(doc_id=D, start_char=501, end_char=550)], 100)
    assert p.core_unit_ids == ["u1"]


# ---------------------------------------------------------------- REQUIRED: B2(q) equality

def test_b2_is_equal_across_all_three_arms_for_a_query():
    gold = [GoldSpan(doc_id=D, start_char=0, end_char=5),
            GoldSpan(doc_id=D, start_char=50, end_char=55)]
    invs = {"F768": inventory(40, 600), "U768": inventory(40, 300), "U256": inventory(40, 100)}
    b = b2_for_query(invs, gold)
    sizes = {a: build_package(inv, gold, b["b2"]).tokens for a, inv in invs.items()}
    assert len(set(sizes.values())) == 1, f"packages differ within the pair: {sizes}"
    assert set(sizes.values()) == {b["b2"]}


def test_b2_attribution_names_the_arm_that_escalated():
    gold = [GoldSpan(doc_id=D, start_char=0, end_char=5),
            GoldSpan(doc_id=D, start_char=50, end_char=55)]
    invs = {"F768": inventory(40, 600), "U768": inventory(40, 100), "U256": inventory(40, 100)}
    b = b2_for_query(invs, gold)
    assert b["escalated"] is True
    assert b["set_by"] == ["F768"]


def test_b2_floor_when_every_arm_fits():
    b = b2_for_query({a: inventory(40, 100) for a in ARMS},
                     [GoldSpan(doc_id=D, start_char=10, end_char=15)])
    assert b["b2"] == 1024 and b["escalated"] is False and b["set_by"] == []


# ------------------------------------------- shortfall must carry its cause (ruling §5.2)

def test_exact_package_records_no_shortfall_and_no_cause():
    from v19.packages import build_matched

    m = build_matched("U768", inventory(40, 100), [GoldSpan(doc_id=D, start_char=10, end_char=15)], 1024)
    assert m.is_exact and m.shortfall == 0 and m.cause is None


def test_short_package_records_document_exhaustion_as_its_cause():
    from v19.packages import DOCUMENT_EXHAUSTED, build_matched

    inv = inventory(3, 100)                    # 300 tokens available, budget 1024
    m = build_matched("F768", inv, [GoldSpan(doc_id=D, start_char=10, end_char=15)], 1024)
    assert m.shortfall == 724
    assert m.cause == DOCUMENT_EXHAUSTED
    assert set(m.package.unit_ids) == {"u0", "u1", "u2"}, "exhaustion means nothing was left"


def test_a_shortfall_with_units_left_over_is_an_apparatus_fault():
    """The only permitted cause is exhaustion; anything else must raise, not be recorded."""
    from v19.packages import ShortfallCauseUnknown, build_matched
    import v19.packages as vp

    real = vp.build_package

    def _leaky(units, gold, budget):
        p = real(units, gold, budget)
        p.unit_ids = p.unit_ids[:-1]           # simulate a builder that stopped padding early
        return p

    vp.build_package = _leaky
    try:
        with pytest.raises(ShortfallCauseUnknown, match="apparatus fault"):
            build_matched("F768", inventory(3, 100),
                          [GoldSpan(doc_id=D, start_char=10, end_char=15)], 1024)
    finally:
        vp.build_package = real


def test_build_all_reports_tokens_and_shortfalls_per_arm():
    from v19.packages import build_all

    invs = {"F768": inventory(3, 100), "U768": inventory(40, 100), "U256": inventory(40, 100)}
    gold = [GoldSpan(doc_id=D, start_char=10, end_char=15)]
    r = build_all(invs, gold, 1024)
    assert r["all_exact"] is False
    assert r["tokens"]["U768"] == 1024 and r["tokens"]["F768"] == 300
    assert r["shortfalls"]["F768"]["tokens"] == 724
    assert r["shortfalls"]["F768"]["cause"] == "document_exhausted"
    assert "U768" not in r["shortfalls"]


def test_gold_delivery_cost_companion_reports_values_and_attribution():
    from v19.packages import gold_delivery_costs

    invs = {"F768": inventory(40, 100), "U768": inventory(40, 600), "U256": inventory(40, 100)}
    gold = [GoldSpan(doc_id=D, start_char=0, end_char=5),
            GoldSpan(doc_id=D, start_char=50, end_char=55)]
    c = gold_delivery_costs(invs, gold)
    assert c["argmax"] == ["U768"]
    assert c["T_a"]["F768"] < c["T_a"]["U768"], "the compactness fact the companion exists to state"


# ---------------------------------------------------------------- REQUIRED: mismatch wiring

def test_mismatched_package_is_the_successor_with_wraparound():
    sample = ["q1", "q2", "q3", "q4"]
    pairs = pair_with_successor(sample)
    assert [(p.query_id, p.mismatched_package_of) for p in pairs] == [
        ("q1", "q2"), ("q2", "q3"), ("q3", "q4"), ("q4", "q1")]


def test_no_query_ever_receives_its_own_package():
    pairs = pair_with_successor([f"q{i}" for i in range(30)])
    assert all(p.query_id != p.mismatched_package_of for p in pairs)
    assert all(p.correct_package_of == p.query_id for p in pairs)


def test_mismatch_needs_at_least_two_queries():
    with pytest.raises(ValueError, match="at least two"):
        pair_with_successor(["only"])


def test_control_sample_is_deterministic_and_order_independent():
    ids = [f"q{i}" for i in range(200)]
    a = draw_control_sample(ids, CONTROL_N, CONTROL_SEED)
    b = draw_control_sample(list(reversed(ids)), CONTROL_N, CONTROL_SEED)
    assert a == b, "the draw must depend on the id set and seed, not on loader order"
    assert len(a) == CONTROL_N == 30 and len(set(a)) == 30


def test_control_sample_refuses_an_undersized_pool():
    with pytest.raises(ValueError, match="cannot draw"):
        draw_control_sample([f"q{i}" for i in range(5)])


# ---------------------------------------------------------------- REQUIRED: fresh-call assertion

class _Fake(V19Client):
    """Drives the call machinery with no network. `provider` stays 'anthropic' for the guards."""

    def __init__(self, outputs, **kw):
        super().__init__(provider="anthropic", **kw)
        self._outputs = list(outputs)
        self._i = 0
        self.model_to_report = "claude-sonnet-5"

    def _call_provider(self, prompt, system):
        out = self._outputs[self._i % len(self._outputs)]
        self._i += 1
        self.models_seen.append(self.model_to_report)
        self.finish_reasons.append("end_turn")
        self.output_lengths.append(len(out))
        self.assert_model_constant()
        return out, 10, 5


def test_probe_asserts_every_repeat_was_a_fresh_call():
    c = _Fake(["same"])
    r = determinism_probe(c, ["p1", "p2"], repeats=3)
    assert r["fresh_calls"] == 6 == c.uncached_calls
    assert r["verdict"] == "DETERMINISTIC" and r["all_identical"] is True


def test_probe_detects_nondeterminism():
    c = _Fake(["a", "b", "a"])
    r = determinism_probe(c, ["p1"], repeats=3)
    assert r["verdict"] == "NONDETERMINISTIC" and r["n_prompts_identical"] == 0


def test_probe_fails_loudly_if_a_repeat_is_served_from_cache():
    """The G2 defect, simulated: a client whose repeats do not reach the provider."""
    class _Cached(_Fake):
        def complete_uncached(self, prompt, system=""):
            if self.uncached_calls >= 1:
                return "cached"                      # served without a fresh call
            return super().complete_uncached(prompt, system)

    with pytest.raises(ProbeServedFromCache, match="measured the cache"):
        determinism_probe(_Cached(["x"]), ["p1", "p2"], repeats=3)


def test_probe_refuses_to_exceed_its_call_bound():
    with pytest.raises(RuntimeError, match="over the 500"):
        determinism_probe(_Fake(["x"]), [f"p{i}" for i in range(200)], repeats=3)


def test_uncached_path_never_touches_the_cache_directory(tmp_path):
    c = _Fake(["out"], cache_dir=tmp_path / "llm")
    c.complete_uncached("prompt")
    assert list((tmp_path / "llm").glob("*.json")) == [], "the probe wrote to the cache"
    assert c.cache_hits == 0, "the probe read from the cache"


def test_uncached_path_still_obeys_the_cost_guard():
    c = _Fake(["out"], max_llm_calls=1)
    c.complete_uncached("one")
    from src.llm.client import CostGuardExceeded
    with pytest.raises(CostGuardExceeded):
        c.complete_uncached("two")


# ---------------------------------------------------------------- REQUIRED: response.model pin

def test_model_constancy_is_asserted_on_every_call():
    c = _Fake(["out"])
    c.complete_uncached("a")
    c.model_to_report = "claude-sonnet-5-something-else"
    with pytest.raises(ModelPinViolated, match="APPARATUS-STOP"):
        c.complete_uncached("b")


def test_pin_record_reports_what_can_actually_be_pinned():
    c = _Fake(["out"])
    c.complete_uncached("a")
    c.complete_uncached("b")
    rec = c.pin_record()
    assert rec["response_model_distinct"] == ["claude-sonnet-5"]
    assert rec["n_calls_observed"] == 2
    assert rec["requested_model"] and rec["run_started_utc"] and rec["run_ended_utc"]


def test_anomaly_record_logs_finish_reasons_for_the_g6_guard():
    c = _Fake(["out"])
    c.complete_uncached("a")
    rec = c.anomaly_record()
    assert rec["finish_reasons"] == {"end_turn": 1}
    assert rec["n"] == 1 and rec["output_length_max"] == 3
