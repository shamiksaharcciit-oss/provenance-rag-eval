"""Gate 0 — the E2 package builder, the frozen prompt and the frozen scorers (plan §3.1-§3.3).

No model is called. Package construction and scoring are deterministic, so the whole of E2's
apparatus is pinned here before E1 decides whether E2 ever runs.
"""
from __future__ import annotations

import pytest

from src.chunkers.base import Unit
from src.datasets.base import GoldSpan
from src.textutil import count_tokens
from src.v17.packages import (B2_CAP, B2_FLOOR, BudgetCapExceeded, GoldExceedsBudget, JOIN,
                              PaddingUnsupported, build_package, gold_token_cost, matched_budget,
                              truncate_tokens)
from src.v17.reading import (PROMPT_TEMPLATE, exact_containment, gold_text, is_not_found,
                             normalise, render_prompt, token_f1, tokens)

D = "doc1"


def unit(i, word, n, doc=D, start=0):
    """A unit of exactly `n` single-token words, with a source range the caller controls."""
    return Unit(unit_id=f"u{i}", text=" ".join([word] * n), doc_id=doc,
                source_ranges=[(start, start + 10)])


def inventory(n_units, n_tokens=100):
    return [unit(i, f"w{i}", n_tokens, start=i * 10) for i in range(n_units)]


def gold(start, end, doc=D):
    return [GoldSpan(doc_id=doc, start_char=start, end_char=end)]


# ------------------------------------------------------------------ selection and padding

def test_package_lands_exactly_on_budget():
    inv = inventory(20, 100)
    p = build_package(inv, gold(50, 55), 1024)
    assert p.tokens == 1024
    assert count_tokens(p.text) == 1024
    assert p.shortfall == 0


def test_core_units_are_the_gold_bearing_ones():
    inv = inventory(20, 100)
    p = build_package(inv, gold(50, 55), 1024)     # range (50,60) -> unit 5
    assert p.core_unit_ids == ["u5"]
    assert "u5" in p.unit_ids


def test_padding_alternates_following_then_preceding():
    inv = inventory(20, 100)
    p = build_package(inv, gold(100, 105), 500)    # core u10; 4 more units needed
    assert p.core_unit_ids == ["u10"]
    # following u11, preceding u9, following u12, preceding u8 -> span u8..u12
    assert p.unit_ids == ["u8", "u9", "u10", "u11", "u12"]


def test_units_between_two_gold_units_are_included():
    inv = inventory(20, 100)
    two = [GoldSpan(doc_id=D, start_char=50, end_char=55),
           GoldSpan(doc_id=D, start_char=90, end_char=95)]
    p = build_package(inv, two, 1024)
    assert p.core_unit_ids == ["u5", "u9"]
    for uid in ("u5", "u6", "u7", "u8", "u9"):
        assert uid in p.unit_ids


def test_short_document_records_shortfall_and_pads_nothing_else():
    inv = inventory(3, 100)
    p = build_package(inv, gold(10, 15), 1024)
    assert p.tokens == 300
    assert p.shortfall == 724
    assert p.unit_ids == ["u0", "u1", "u2"]


def test_gold_exceeding_the_budget_raises_rather_than_truncating_gold():
    """§3.3 assumes a missing gold span is impossible; it is only impossible while gold fits."""
    inv = inventory(20, 600)
    two = [GoldSpan(doc_id=D, start_char=0, end_char=5),
           GoldSpan(doc_id=D, start_char=50, end_char=55)]
    with pytest.raises(GoldExceedsBudget, match="truncate gold"):
        build_package(inv, two, 1024)


def test_cross_document_gold_raises_rather_than_inventing_an_order():
    inv = inventory(5) + [unit(9, "z", 100, doc="doc2")]
    two = [GoldSpan(doc_id=D, start_char=10, end_char=15),
           GoldSpan(doc_id="doc2", start_char=0, end_char=5)]
    with pytest.raises(PaddingUnsupported, match="documents"):
        build_package(inv, two, 1024)


def test_gold_with_no_covering_unit_is_an_apparatus_fault():
    with pytest.raises(PaddingUnsupported, match="apparatus fault"):
        build_package(inventory(5), gold(9000, 9005), 1024)


def test_only_the_gold_document_contributes():
    inv = inventory(5, 100) + [unit(99, "other", 100, doc="doc2", start=0)]
    p = build_package(inv, gold(10, 15), 1024)
    assert all(not uid.startswith("u99") for uid in p.unit_ids)
    assert p.meta["doc_id"] == D


# ------------------------------------------------------------------ truncation

def test_truncation_cuts_the_last_added_unit_only():
    inv = inventory(20, 100)
    p = build_package(inv, gold(100, 105), 450)   # 4 whole units + 50 of a fifth
    assert p.tokens == 450
    assert p.truncated_unit_id is not None
    assert p.core_unit_ids == ["u10"]


def test_a_following_unit_keeps_its_head():
    text = "a b c d e f"
    assert truncate_tokens(text, 3, from_start=True) == "a b c"


def test_a_preceding_unit_keeps_its_tail():
    text = "a b c d e f"
    assert truncate_tokens(text, 3, from_start=False) == "d e f"


def test_truncation_lands_on_a_token_boundary():
    text = " ".join(f"w{i}" for i in range(50))
    for k in (1, 7, 23, 49):
        assert count_tokens(truncate_tokens(text, k, from_start=True)) == k
        assert count_tokens(truncate_tokens(text, k, from_start=False)) == k


def test_truncating_to_more_than_available_returns_everything():
    assert truncate_tokens("a b c", 99, from_start=True) == "a b c"


def test_join_separator_adds_no_tokens():
    """The separator must not shift the budget between arms."""
    parts = ["a b c", "d e f"]
    assert count_tokens(JOIN.join(parts)) == sum(count_tokens(p) for p in parts)


def test_gold_token_cost_matches_what_the_builder_checks():
    inv = inventory(20, 600)
    two = [GoldSpan(doc_id=D, start_char=0, end_char=5),
           GoldSpan(doc_id=D, start_char=50, end_char=55)]
    assert gold_token_cost(inv, two) == 3600          # units 0..5 inclusive
    with pytest.raises(GoldExceedsBudget):
        build_package(inv, two, 1024)


# ------------------------------------------------------------------ B2(q), per plan §3.1 / PF-2

def test_b2_is_the_floor_when_gold_fits_in_every_arm():
    arms = {"U768": inventory(20, 100), "F768": inventory(20, 120)}
    b = matched_budget(arms, gold(50, 55))
    assert b.b2 == B2_FLOOR == 1024
    assert b.escalated is False
    assert b.set_by == []


def test_b2_escalates_to_the_largest_arm_and_names_it():
    """Straddling gold: the budget rises to the widest arm's gold-covering set."""
    wide = inventory(20, 600)
    two = [GoldSpan(doc_id=D, start_char=0, end_char=5),
           GoldSpan(doc_id=D, start_char=50, end_char=55)]
    arms = {"U256": inventory(20, 100), "F768": wide}
    b = matched_budget(arms, two)
    assert b.b2 == 3600
    assert b.escalated is True
    assert b.set_by == ["F768"]
    assert b.costs["U256"] == 600


def test_every_arm_is_padded_to_the_same_b2_so_the_pair_matches():
    """THE guarantee: equal tokens WITHIN the pair. Checked as a property across arms."""
    two = [GoldSpan(doc_id=D, start_char=0, end_char=5),
           GoldSpan(doc_id=D, start_char=50, end_char=55)]
    arms = {"U256": inventory(40, 100), "U768": inventory(40, 300), "F768": inventory(40, 600)}
    b = matched_budget(arms, two)
    sizes = {a: build_package(inv, two, b.b2).tokens for a, inv in arms.items()}
    assert len(set(sizes.values())) == 1, f"packages differ in size within the pair: {sizes}"
    assert set(sizes.values()) == {b.b2}


def test_b2_clears_gold_in_every_arm_so_gold_is_never_truncated():
    two = [GoldSpan(doc_id=D, start_char=0, end_char=5),
           GoldSpan(doc_id=D, start_char=50, end_char=55)]
    arms = {"U256": inventory(40, 100), "F768": inventory(40, 600)}
    b = matched_budget(arms, two)
    for inv in arms.values():
        build_package(inv, two, b.b2)          # GoldExceedsBudget is unreachable at B2(q)


def test_b2_over_the_cap_is_an_apparatus_stop():
    arms = {"F768": inventory(40, 900)}
    two = [GoldSpan(doc_id=D, start_char=0, end_char=5),
           GoldSpan(doc_id=D, start_char=100, end_char=105)]
    with pytest.raises(BudgetCapExceeded, match="cap"):
        matched_budget(arms, two)


def test_b2_with_no_arms_is_undefined():
    with pytest.raises(PaddingUnsupported, match="no arms"):
        matched_budget({}, gold(10, 15))


def test_b2_raises_when_an_arm_cannot_cover_the_gold():
    arms = {"good": inventory(5), "bad": [unit(0, "x", 100, start=9000)]}
    with pytest.raises(PaddingUnsupported, match="undefined"):
        matched_budget(arms, gold(10, 15))


# ------------------------------------------------------------------ the frozen prompt

def test_prompt_has_no_mid_sentence_line_break():
    """The plan's fenced block wraps at 96 columns; the template stores the instruction unwrapped."""
    first = PROMPT_TEMPLATE.split("\n")[0]
    assert first.endswith("reply exactly: NOT FOUND.")
    assert "Answer the question using only the provided context." in first


def test_prompt_labels_and_abstention_string_are_verbatim():
    assert "\nContext:\n" in PROMPT_TEMPLATE
    assert "\nQuestion: {query}\n" in PROMPT_TEMPLATE
    assert "NOT FOUND" in PROMPT_TEMPLATE


def test_render_survives_braces_in_the_package():
    """Package text is corpus text and may contain braces; str.format would raise or interpolate."""
    p = render_prompt("a {weird} {0} package", "q?")
    assert "{weird}" in p and "{0}" in p
    assert p.endswith("Question: q?\n")


def test_render_places_both_fields():
    p = render_prompt("PKG", "QRY")
    assert "Context:\nPKG\n" in p and "Question: QRY" in p


def test_is_not_found_is_exact():
    assert is_not_found("NOT FOUND")
    assert is_not_found("  NOT FOUND\n")
    assert not is_not_found("not found")
    assert not is_not_found("NOT FOUND, sorry")


# ------------------------------------------------------------------ the frozen scorers

def test_normalisation_lowercases_and_collapses():
    assert normalise("  The   QUICK\nbrown  ") == "the quick brown"


def test_punctuation_becomes_a_separator_not_a_deletion():
    """Hyphen removal must not weld words: the formatter edits punctuation."""
    assert tokens("state-of-the-art") == ["state", "of", "the", "art"]
    assert normalise("state of the art") == normalise("state-of-the-art")


def test_curly_and_straight_quotes_normalise_alike():
    assert normalise("the “value”") == normalise('the "value"')
    assert normalise("don’t") == normalise("don't")


def test_token_f1_exact_match_is_one():
    assert token_f1("the answer is 42", "the answer is 42") == 1.0


def test_token_f1_no_overlap_is_zero():
    assert token_f1("completely different", "the answer") == 0.0


def test_token_f1_is_multiset_not_set():
    """A term repeated in gold must be repeated in the answer to earn its second point."""
    assert token_f1("a", "a a") < 1.0


def test_token_f1_partial_overlap():
    assert 0.0 < token_f1("the answer is 42 and more", "the answer is 42") < 1.0


def test_token_f1_empty_cases():
    assert token_f1("", "") == 1.0
    assert token_f1("", "gold") == 0.0
    assert token_f1("answer", "") == 0.0


def test_not_found_scores_zero_against_real_gold():
    assert token_f1("NOT FOUND", "the melting point is 1085 c") < 0.2


def test_exact_containment_ignores_punctuation_and_case():
    assert exact_containment("The answer is: 42 degrees.", "answer is 42") == 1
    assert exact_containment("something else entirely", "answer is 42") == 0


def test_exact_containment_of_empty_gold_is_zero():
    assert exact_containment("anything", "") == 0


def test_gold_text_concatenates_in_document_order():
    doc = "0123456789abcdefghij"
    spans = [GoldSpan(doc_id=D, start_char=10, end_char=13),
             GoldSpan(doc_id=D, start_char=2, end_char=5)]
    assert gold_text(doc, spans) == "234 abc"
