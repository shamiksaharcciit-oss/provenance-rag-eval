"""The PW-1 interpretation rule, including the `r <= 1` halt (work order A7).

Per template §A1b, every guard here is demonstrated FAILING against a deliberate violation.
The `r <= 1` invariant is the point of the exercise: it is structurally impossible for the
corrected delta to exceed the published one, so the test that matters is the one showing the
run stops rather than printing a number that cannot occur.
"""
from __future__ import annotations

import pytest

from src.pw1.interpret import (
    RatioExceedsOne,
    aggregate,
    classify_cell,
    excludes_zero,
    holm_within_family,
    retention_ratio,
)

FULL = 0.1477          # bge / Track A published delta, as an example denominator


# --------------------------------------------------------------------------
# A7 — the halt. Negative control first.
# --------------------------------------------------------------------------

def test_r_above_one_halts_rather_than_reporting():
    """THE §A1b CONTROL. Stripping ranges is monotone in hits and the unformatted arm has
    nothing to strip, so a corrected delta above the published one is a scoring defect."""
    with pytest.raises(RatioExceedsOne) as e:
        retention_ratio(delta_corrected=0.1600, delta_full=FULL)
    assert "monotone" in str(e.value)


def test_r_above_one_halts_inside_the_classifier_too():
    """The halt must not be bypassable by going through classify_cell."""
    with pytest.raises(RatioExceedsOne):
        classify_cell(delta_full=FULL, full_significant=True,
                      delta_corrected=0.20, ci_corrected=(0.15, 0.25),
                      p_holm_corrected=0.001)


def test_r_exactly_one_is_allowed():
    """The invariant is r <= 1, not r < 1: a cell untouched by stripping sits exactly at 1."""
    assert retention_ratio(delta_corrected=FULL, delta_full=FULL) == pytest.approx(1.0)


def test_float_slack_does_not_become_a_tolerance_for_real_overshoot():
    assert retention_ratio(FULL * (1 + 1e-12), FULL) <= 1.0 + 1e-9
    with pytest.raises(RatioExceedsOne):
        retention_ratio(FULL * 1.0001, FULL)          # 0.01% is real, not float noise


def test_sign_flip_gives_negative_r_and_does_not_halt():
    """A sign flip is a legitimate (very bad) outcome, not an impossibility."""
    assert retention_ratio(-0.05, FULL) < 0


# --------------------------------------------------------------------------
# The frozen boundary rule
# --------------------------------------------------------------------------

def test_ci_bound_of_exactly_zero_does_not_exclude_zero():
    """Frozen before computing, because bge/Track A's published CI is [+0.0000, +0.0909]."""
    assert excludes_zero((0.0170, 0.1023)) is True
    assert excludes_zero((0.0000, 0.0909)) is False
    assert excludes_zero((-0.0133, 0.0667)) is False
    assert excludes_zero((-0.20, -0.01)) is True


# --------------------------------------------------------------------------
# The five branches, in order, first match wins
# --------------------------------------------------------------------------

def test_branch_1_not_applicable_short_circuits_and_still_reports_r():
    out = classify_cell(delta_full=0.0267, full_significant=False,
                        delta_corrected=0.0100, ci_corrected=(-0.02, 0.04),
                        p_holm_corrected=0.9)
    assert out["branch"] == "NOT APPLICABLE"
    assert out["r"] == pytest.approx(0.0100 / 0.0267)


def test_branch_2_underpowered_needs_both_zero_and_delta_full_inside():
    out = classify_cell(delta_full=FULL, full_significant=True,
                        delta_corrected=0.08, ci_corrected=(-0.02, 0.20),
                        p_holm_corrected=0.3)
    assert out["branch"] == "UNDERPOWERED"


def test_underpowered_does_not_fire_when_delta_full_is_outside_the_ci():
    """CI contains zero but not delta_full -> NOT SEPARATED, not UNDERPOWERED."""
    out = classify_cell(delta_full=FULL, full_significant=True,
                        delta_corrected=0.02, ci_corrected=(-0.01, 0.05),
                        p_holm_corrected=0.4)
    assert out["branch"] == "NOT SEPARATED"


def test_branch_3_not_separated_on_low_r():
    out = classify_cell(delta_full=FULL, full_significant=True,
                        delta_corrected=0.02, ci_corrected=(0.005, 0.035),
                        p_holm_corrected=0.04)
    assert out["branch"] == "NOT SEPARATED" and out["r"] < 0.25


def test_branch_4_separated_requires_both_r_and_significance():
    kw = dict(delta_full=FULL, full_significant=True, delta_corrected=0.13,
              ci_corrected=(0.06, 0.20))
    assert classify_cell(**kw, p_holm_corrected=0.001)["branch"] == "SEPARATED"
    # same r, significance lost -> demoted, NOT still SEPARATED
    assert classify_cell(**kw, p_holm_corrected=0.20)["branch"] == "PARTIALLY SEPARATED"


def test_branch_5_is_the_residual_band():
    out = classify_cell(delta_full=FULL, full_significant=True,
                        delta_corrected=0.074, ci_corrected=(0.02, 0.13),
                        p_holm_corrected=0.01)
    assert out["branch"] == "PARTIALLY SEPARATED" and 0.25 <= out["r"] < 0.75


def test_the_branches_are_exhaustive_over_a_sweep():
    """No input in a realistic sweep falls through unclassified — the defect the five-branch
    rule replaced."""
    seen = set()
    # The sweep must stay at or below delta_full: above it, the A7 halt fires — as it did on
    # the first version of this test, which swept to 0.15 against a delta_full of 0.1477.
    for num in [x / 1000 for x in range(-200, int(FULL * 1000) + 1, 5)]:
        for lo, hi in [(-0.02, 0.20), (-0.01, 0.05), (0.005, 0.035), (0.06, 0.20), (0.02, 0.13)]:
            for ph in (0.001, 0.20):
                out = classify_cell(delta_full=FULL, full_significant=True,
                                    delta_corrected=num, ci_corrected=(lo, hi),
                                    p_holm_corrected=ph)
                assert out["branch"] in {"UNDERPOWERED", "NOT SEPARATED", "SEPARATED",
                                         "PARTIALLY SEPARATED"}
                seen.add(out["branch"])
    assert len(seen) >= 3, seen


# --------------------------------------------------------------------------
# Aggregation — least favourable wins, same logic as REJECT_HARM over ADOPT
# --------------------------------------------------------------------------

def test_aggregate_takes_the_least_favourable_label():
    assert aggregate(["SEPARATED", "SEPARATED", "NOT SEPARATED"]) == "NOT SEPARATED"
    assert aggregate(["SEPARATED", "PARTIALLY SEPARATED"]) == "PARTIALLY SEPARATED"
    assert aggregate(["SEPARATED"]) == "SEPARATED"


def test_aggregate_ignores_inapplicable_and_unpowered_cells():
    assert aggregate(["NOT APPLICABLE", "UNDERPOWERED", "SEPARATED"]) == "SEPARATED"


def test_aggregate_is_underpowered_when_nothing_is_applicable_and_powered():
    assert aggregate(["NOT APPLICABLE", "UNDERPOWERED"]) == "UNDERPOWERED"
    assert aggregate([]) == "UNDERPOWERED"


# --------------------------------------------------------------------------
# A2 — Holm must be WITHIN the PW-1 family
# --------------------------------------------------------------------------

def test_family_2_holm_within_family_reproduces_the_work_order():
    """raw 0.0205 / 0.0931 over a 2-member family -> 0.0410 / 0.0931.

    The published artifacts store 0.10249 / 0.27927, which are Holm over that run's own
    six-member pairwise family — a foreign multiplicity that must not enter PW-1.
    """
    adj = holm_within_family([0.0205, 0.0931])
    assert adj[0] == pytest.approx(0.0410, abs=1e-6)
    assert adj[1] == pytest.approx(0.0931, abs=1e-6)
    assert adj[0] < 0.05 and adj[1] >= 0.05


def test_family_1_holm_within_family_reproduces_the_published_values():
    """Family 1's stored p_holm already IS Holm within family 1 — which is why only family 2
    needed correcting."""
    adj = holm_within_family([0.0002, 0.3423, 0.0001, 0.0135])
    assert adj == pytest.approx([0.0006, 0.3423, 0.0004, 0.027], abs=1e-6)


def test_importing_the_published_six_member_holm_would_empty_family_2():
    """Records the defect A2 fixes: the imported values gate out both cells."""
    assert 0.10249 >= 0.05 and 0.27927 >= 0.05
