"""v1.11 Gate 0 tests (§7), including the persist-every-output test the v1.9 defect made
load-bearing."""
from __future__ import annotations

import pytest

from src.chunkers.base import Unit
from src.datasets.base import GoldSpan
from v111.containment import containment_against
from v111.ids import custom_id, parse_custom_id
from v111.persist import PersistenceIncomplete, assert_every_output_persisted
from v111.prompts import VARIANTS, render
from v111.unanswerable import (PackageIsAnswerable, assert_no_gold_overlap, false_answer,
                               gold_bearing_ids, same_doc_answerless)

D = "d1"


def u(i, n=100, s=None):
    s = i * 100 if s is None else s
    return Unit(unit_id=f"u{i}", text=" ".join([f"w{i}"] * n), doc_id=D, source_ranges=[(s, s + 100)])


def test_custom_ids_are_unique_and_within_the_acceptor():
    ids = [custom_id(e, a, i, v) for e in ("ea", "eb") for a in ("f768", "u768")
           for v in ("sdoc", "frozen") for i in range(176)]
    assert len(ids) == len(set(ids)) and all(len(c) <= 64 for c in ids)


def test_custom_id_roundtrips():
    c = custom_id("ec", "u768", 42, "v2", 1)
    assert parse_custom_id(c) == {"exp": "ec", "arm": "u768", "index": 42, "variant": "v2", "rep": 1}


def test_v18_ids_are_rejected_by_the_v111_parser():
    with pytest.raises(AssertionError, match="not a v111"):
        parse_custom_id("v18-j1-B-u768-q149-cp-a0-s4")


def test_all_prompt_variants_retain_the_abstention_token():
    assert all("NOT FOUND" in v for v in VARIANTS.values())


def test_render_is_brace_safe():
    assert "{x}" in render("v2", "a {x} b", "q?")


def test_gold_bearing_units_are_excluded_from_same_doc():
    units = [u(0, s=0), u(1, s=100), u(2, s=200)]
    gold = [GoldSpan(doc_id=D, start_char=110, end_char=150)]
    assert gold_bearing_ids(units, gold) == {"u1"}
    pkg = same_doc_answerless(units, gold, 150)
    assert pkg is not None and all(x.unit_id != "u1" for x in pkg)
    assert_no_gold_overlap(pkg, gold, "t")


def test_an_overlapping_package_is_rejected():
    with pytest.raises(PackageIsAnswerable, match="not unanswerable"):
        assert_no_gold_overlap([u(1, s=100)], [GoldSpan(doc_id=D, start_char=110, end_char=150)], "t")


def test_same_doc_returns_none_when_no_non_gold_unit_exists():
    """The six-query case: for that arm the whole document is gold-bearing."""
    assert same_doc_answerless([u(0, s=0)], [GoldSpan(doc_id=D, start_char=10, end_char=50)], 100) is None


def test_false_answer_is_the_complement_of_the_frozen_token():
    assert false_answer("NOT FOUND") == 0 and false_answer("  NOT FOUND\n") == 0
    assert false_answer("The value is 42") == 1 and false_answer("not found") == 1


def test_containment_against_uses_the_frozen_normalisation():
    assert containment_against("The Answer, is 42.", "x the answer is 42 y") == 1
    assert containment_against("something else", "x the answer is 42 y") == 0


def test_persist_every_output_accepts_a_complete_record():
    assert_every_output_persisted({"q1": {"F768": {"answers": ["a", "b", "c"], "packages": "pkg"}}}, reps=3)


def test_persist_every_output_rejects_a_summary_only_record():
    """THE v1.9 defect, now a failing test: three scores kept, one text kept."""
    with pytest.raises(PersistenceIncomplete, match="every repetition"):
        assert_every_output_persisted({"q1": {"F768": {"answers": ["a"], "packages": "pkg"}}}, reps=3)


def test_persist_every_output_rejects_a_missing_package():
    with pytest.raises(PersistenceIncomplete, match="package text"):
        assert_every_output_persisted({"q1": {"F768": {"answers": ["a", "b", "c"]}}}, reps=3)
