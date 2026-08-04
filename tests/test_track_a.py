"""Track A generator correctness: gold spans must anchor to answer-bearing text,
and generation must be deterministic (plan §5.1-A, §11)."""
from __future__ import annotations

from src.datasets import track_a_synthetic as ta


def test_gold_spans_contain_answer_value():
    ds = ta.load({"params": {"n_docs": 20, "n_queries": 150}}, seed=1337)
    doc_by_id = ds.doc_by_id()
    checked = 0
    for q in ds.queries:
        if q.qtype != "factual":
            continue
        doc = doc_by_id[q.gold_spans[0].doc_id]
        # at least one gold span must contain the reference answer verbatim
        hit = any(
            q.answer in doc.text[g.start_char:g.end_char] for g in q.gold_spans
        )
        assert hit, f"{q.query_id}: answer {q.answer!r} not inside any gold span"
        checked += 1
    assert checked > 50


def test_offsets_in_bounds():
    ds = ta.load({"params": {"n_docs": 15, "n_queries": 120}}, seed=7)
    doc_by_id = ds.doc_by_id()
    for q in ds.queries:
        for g in q.gold_spans:
            doc = doc_by_id[g.doc_id]
            assert 0 <= g.start_char < g.end_char <= len(doc.text)


def test_deterministic_from_seed():
    a = ta.load({"params": {"n_docs": 12, "n_queries": 100}}, seed=42)
    b = ta.load({"params": {"n_docs": 12, "n_queries": 100}}, seed=42)
    assert [d.text for d in a.documents] == [d.text for d in b.documents]
    assert [(q.query_id, q.text) for q in a.queries] == [(q.query_id, q.text) for q in b.queries]


def test_degradation_present():
    # some factual answer sentences should be anaphora-degraded (start with a pronoun)
    ds = ta.load({"params": {"n_docs": 30, "n_queries": 200}}, seed=1337)
    doc_by_id = ds.doc_by_id()
    pron_starts = 0
    for q in ds.queries:
        doc = doc_by_id[q.gold_spans[0].doc_id]
        for g in q.gold_spans:
            seg = doc.text[g.start_char:g.end_char]
            if seg.startswith(("It ", "This system", "The system", "This component")):
                pron_starts += 1
    assert pron_starts > 0, "expected some anaphora-degraded gold sentences"
