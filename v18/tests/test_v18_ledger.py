"""Gate 0(b) §4 — the spend ledger, which exists because Gate 0's accounting could not survive.

During Gate 0 the probe's counter reset on every restart and two attempts died on credit
exhaustion, so cumulative spend became uncomputable: 334–1,018 against a hard 1,000. These tests
pin the three properties that make that impossible to repeat — durability across processes,
append-only history, and an honest representation of spend that genuinely cannot be computed.
"""
from __future__ import annotations

import pytest

from v18.ledger import CALL_CEILING, FROZEN_PROJECTION, CeilingBreached, SpendLedger


def test_ledger_survives_a_new_process(tmp_path):
    """The defect it was built for: an in-memory counter that resets."""
    p = tmp_path / "ledger.json"
    SpendLedger(p).record("gen", calls=100, input_tokens=10, output_tokens=5)
    reopened = SpendLedger(p)                      # a fresh object, as after a restart
    assert reopened.totals()["calls"] == 100


def test_totals_accumulate_across_stages(tmp_path):
    led = SpendLedger(tmp_path / "l.json")
    led.record("gen", calls=1_682, input_tokens=100, output_tokens=50)
    led.record("judge", calls=15_960, input_tokens=900, output_tokens=200)
    t = led.totals()
    assert t["calls"] == 17_642 == FROZEN_PROJECTION
    assert t["input_tokens"] == 1_000 and t["output_tokens"] == 250
    assert t["headroom_against_ceiling"] == CALL_CEILING - 17_642


def test_breaching_the_ceiling_raises(tmp_path):
    led = SpendLedger(tmp_path / "l.json")
    led.record("gen", calls=CALL_CEILING)
    with pytest.raises(CeilingBreached, match="STOP"):
        led.record("judge", calls=1)


def test_history_is_append_only(tmp_path):
    led = SpendLedger(tmp_path / "l.json")
    led.record("a", calls=1)
    led.record("b", calls=2)
    entries = led.read()["entries"]
    assert [e["stage"] for e in entries] == ["a", "b"]
    assert [e["calls"] for e in entries] == [1, 2]


def test_indeterminate_spend_is_recorded_as_a_range_with_its_cause(tmp_path):
    """Gate 0(b) §3 ordered the probe's 334–1,018 recorded as 'a range, attributed'.

    A single invented figure would be worse than the range it replaced — that is the 589 MB
    lesson, applied to spend.
    """
    led = SpendLedger(tmp_path / "l.json")
    led.record_indeterminate("probe", low=334, high=1_018,
                             cause="two attempts died on credit exhaustion")
    t = led.totals()
    assert t["indeterminate_low"] == 334 and t["indeterminate_high"] == 1_018
    assert t["calls"] == 0, "a range must not be silently folded into the determinate total"
    assert "credit" in led.read()["entries"][0]["cause"]


def test_affordability_check_reports_against_the_ceiling(tmp_path):
    """Gate 0(b) §5 — run before each submission, not discovered mid-run a third time."""
    led = SpendLedger(tmp_path / "l.json")
    led.record("gen", calls=1_682)
    chk = led.affordability_check(planned_calls=15_960, usd_per_call_estimate=0.003)
    assert chk["projected_total_calls"] == 17_642
    assert chk["within_ceiling"] is True
    assert chk["estimated_usd_for_planned"] == pytest.approx(47.88, abs=0.01)


def test_affordability_check_flags_a_projected_breach(tmp_path):
    led = SpendLedger(tmp_path / "l.json")
    led.record("gen", calls=20_000)
    assert led.affordability_check(10_000, 0.003)["within_ceiling"] is False


def test_a_truncated_write_cannot_corrupt_the_ledger(tmp_path):
    """Atomic replace: a kill mid-write must leave the previous ledger intact and parseable."""
    p = tmp_path / "l.json"
    led = SpendLedger(p)
    led.record("gen", calls=5)
    before = p.read_text(encoding="utf-8")
    with pytest.raises(TypeError):
        led._write({"boom": object()})            # json.dump raises partway through encoding
    assert p.read_text(encoding="utf-8") == before, (
        "a failed write must leave the previous ledger byte-identical, not truncated")
    assert not list(p.parent.glob("*.tmp")), "the scratch file must be cleaned up"
