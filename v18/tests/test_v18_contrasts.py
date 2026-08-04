"""§9 — B1's sign convention verified on a case where judge and F1 disagree by construction,
B2's telescoping identity, and the family's exactness.

The B1 test is the one §9 names explicitly, and it is worth saying why it is the one. B1 is a
difference of two preference indicators. If either comparison were written the wrong way round,
B1 would still be a well-typed number on the right scale with a plausible distribution — the
pipeline would run to completion and report the fluency-bias finding with its sign flipped,
which is the refutation rather than the finding. Nothing downstream could catch that. So the
convention is pinned here against a case built to disagree.
"""
from __future__ import annotations

import pytest

from v18.contrasts import (F_BIAS, b1_per_query, context_contrast_table,
                           descriptive_contrast, holm_family)
# Aliased on import: pytest's default `python_functions = "test*"` would otherwise COLLECT
# `tested_contrast` as a test case and error on its required arguments.
from v18.contrasts import tested_contrast as family_stat

# ------------------------------------------------------------------- B1, the sign convention


def test_b1_is_positive_when_the_judge_prefers_the_formatter_and_f1_does_not():
    """The fluency-bias signature, built by construction.

    One query. The judge scores F768 above U768 (0.9 vs 0.4). Token-F1 on the *identical*
    answers goes the other way (0.3 vs 0.7). So the judge favours the formatter beyond what
    objective scoring supports, and B1 must be strictly positive: +1 - (-1) = +2.
    """
    b1 = b1_per_query(judge_f=[0.9], judge_u=[0.4], f1_f=[0.3], f1_u=[0.7])
    assert b1 == [2]


def test_b1_is_negative_in_the_mirrored_case():
    """Same construction, mirrored. A convention that only passes one direction is not pinned."""
    b1 = b1_per_query(judge_f=[0.4], judge_u=[0.9], f1_f=[0.7], f1_u=[0.3])
    assert b1 == [-2]


def test_b1_is_zero_when_both_instruments_agree():
    """Agreement in either direction is no excess. This is what 'excess' means."""
    assert b1_per_query([0.9], [0.4], [0.9], [0.4]) == [0]   # both prefer F768
    assert b1_per_query([0.4], [0.9], [0.4], [0.9]) == [0]   # both prefer U768
    assert b1_per_query([0.5], [0.5], [0.5], [0.5]) == [0]   # both tie


def test_b1_half_step_when_one_instrument_ties():
    """Judge prefers F768, F1 is indifferent -> +1, not +2."""
    assert b1_per_query([0.9], [0.4], [0.5], [0.5]) == [1]
    assert b1_per_query([0.5], [0.5], [0.9], [0.4]) == [-1]


def test_b1_range_is_minus_two_to_plus_two():
    b1 = b1_per_query([0.9, 0.4, 0.5, 0.9], [0.4, 0.9, 0.5, 0.4],
                      [0.3, 0.7, 0.5, 0.9], [0.7, 0.3, 0.5, 0.4])
    assert b1 == [2, -2, 0, 0]
    assert all(-2 <= v <= 2 for v in b1)


def test_b1_raises_on_broken_pairing():
    with pytest.raises(AssertionError):
        b1_per_query([0.1, 0.2], [0.1], [0.1, 0.2], [0.1, 0.2])


def test_b1_mean_is_positive_on_a_constructed_biased_population():
    """Eight queries: six with the bias signature, two mirroring it, so the net is not trivial.

    Queries 1-6: judge prefers F768, F1 prefers U768 -> +2.
    Queries 7-8: judge prefers U768, F1 prefers F768 -> -2.
    Both instruments genuinely disagree on all eight, so no query contributes a lazy zero.
    """
    judge_f = [0.9] * 6 + [0.4] * 2
    judge_u = [0.4] * 6 + [0.9] * 2
    f1_f = [0.3] * 6 + [0.9] * 2
    f1_u = [0.7] * 6 + [0.4] * 2
    b1 = b1_per_query(judge_f, judge_u, f1_f, f1_u)
    assert b1 == [2] * 6 + [-2] * 2
    assert sum(b1) / len(b1) > 0
    stat = family_stat(b1)
    assert stat["mean"] > 0
    assert stat["discordant"]["favour_positive"] == 6
    assert stat["discordant"]["favour_negative"] == 2
    assert stat["discordant"]["ties"] == 0


# ------------------------------------- the absolute-numbers table that replaced B2 [PF-7]


def test_context_contrast_table_reports_three_values_and_no_ratio():
    f = [0.8, 0.6, 0.55]
    u7 = [0.7, 0.5, 0.50]
    u2 = [0.3, 0.4, 0.50]
    out = context_contrast_table(f, u7, u2)
    # total    = [0.5, 0.2, 0.05] -> 0.75/3
    # size     = [0.4, 0.1, 0.00] -> 0.50/3
    # residual = [0.1, 0.1, 0.05] -> 0.25/3
    assert out["total_F768_minus_U256"]["mean_diff"] == pytest.approx(0.25)
    assert out["size_U768_minus_U256"]["mean_diff"] == pytest.approx(0.5 / 3, abs=1e-6)
    assert out["residual_F768_minus_U768"]["mean_diff"] == pytest.approx(0.25 / 3, abs=1e-6)
    # Check the emitted *quantities*, not the prose: the `_note` legitimately says "no ratio",
    # so string-scanning the whole record would fail on its own disclaimer.
    for key, value in out.items():
        if isinstance(value, dict):
            assert "p_permutation" not in value, f"{key} carries a test (§4: descriptive)"
            assert "ci95" not in value, f"{key} carries a CI (§4: descriptive)"
        assert "ratio" not in key, f"{key} is a ratio; PF-7 removed ratios from this table"


def test_the_three_contrasts_still_telescope():
    """total = size + residual. The reader's subtraction has to actually work."""
    f, u7, u2 = [0.8, 0.6, 0.55], [0.7, 0.5, 0.50], [0.3, 0.4, 0.50]
    out = context_contrast_table(f, u7, u2)
    assert out["total_F768_minus_U256"]["mean_diff"] == pytest.approx(
        out["size_U768_minus_U256"]["mean_diff"]
        + out["residual_F768_minus_U768"]["mean_diff"])


def test_pd2_direction_holds_when_size_exceeds_residual():
    out = context_contrast_table([0.8, 0.6], [0.7, 0.5], [0.3, 0.4])
    assert out["pd2_direction_holds"] is True


def test_pd2_direction_fails_when_residual_exceeds_size():
    """PD-2 must be refutable, or it predicts nothing."""
    out = context_contrast_table([0.9, 0.9], [0.35, 0.45], [0.3, 0.4])
    assert out["pd2_direction_holds"] is False


def test_context_contrast_table_raises_on_broken_pairing():
    with pytest.raises(AssertionError):
        context_contrast_table([0.1, 0.2], [0.1, 0.2], [0.1])


# --------------------------------------------------------------------- the family, exactly


def test_f_bias_is_exactly_one_member_after_pf7():
    out = holm_family({"B1": 0.01})
    assert out["members"] == list(F_BIAS) == ["B1"]


def test_single_member_holm_is_the_identity_and_says_so():
    """A single-member 'correction' reported without comment overstates what was done."""
    out = holm_family({"B1": 0.037})
    assert out["p_holm"]["B1"] == out["p_raw"]["B1"] == 0.037
    assert "identity" in out["_note"]


def test_holm_refuses_a_second_member():
    """B2 is deleted; family creep is exactly what this guard exists to catch."""
    with pytest.raises(AssertionError):
        holm_family({"B1": 0.01, "B2": 0.04})


def test_holm_refuses_an_empty_family():
    with pytest.raises(AssertionError):
        holm_family({})


# ------------------------------------------------------------------- descriptive companions


def test_descriptive_contrast_reports_counts_and_no_p_value():
    out = descriptive_contrast([0.5, 0.2, 0.4], [0.1, 0.6, 0.4])
    assert out["n01_favour_first"] == 1
    assert out["n10_favour_second"] == 1
    assert out["ties"] == 1
    assert out["informative"] == 2
    assert "p_permutation" not in out and "p" not in out, "§4: descriptive means no test"


def test_tested_contrast_reports_ties_separately_from_informative_pairs():
    """A net built from 6 and 2 is a different object from one built from 40 and 34."""
    out = family_stat([1, 1, 0, -1, 0])
    assert out["discordant"] == {"favour_positive": 2, "favour_negative": 1, "ties": 2,
                                 "informative": 3,
                                 "_note": out["discordant"]["_note"]}
