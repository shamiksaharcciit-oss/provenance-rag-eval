"""Formatter guardrail + provenance correctness (plan §6.3, §9, §13)."""
from __future__ import annotations

from src.chunkers.formatter import (
    FormatterChunker, diff_gate_ok, protected_tokens, _subject_phrase,
)
from src.chunkers.base import ChunkContext
from src.datasets.base import Document
from src.textutil import sentence_spans


def test_protected_tokens_detects_ids_numbers_terms():
    prot = set(protected_tokens("It uses HNSW on port 50051 in v2.3.1 under Apache-2.0 with ScaNN"))
    for t in ["HNSW", "50051", "v2.3.1", "Apache-2.0", "ScaNN"]:
        assert t in prot, t
    # plain lowercase words are not protected
    assert "uses" not in prot and "port" not in prot


def test_reference_placeholders_not_protected():
    # QASPER-style structural cross-references are references, not vocabulary (v1.1)
    prot = set(protected_tokens("illustrated in Fig. FIGREF6 and BIBREF9 and TABREF3, "
                                "but HNSW and v2.3.1 stay protected"))
    assert "FIGREF6" not in prot and "BIBREF9" not in prot and "TABREF3" not in prot
    assert "HNSW" in prot and "v2.3.1" in prot


def test_diff_gate_rejects_dropped_identifier():
    orig = "This system evicts hot vectors using a 2Q replacement policy."
    good = "The Kestrel indexer evicts hot vectors using a 2Q replacement policy."
    bad = "The Kestrel indexer evicts hot vectors using an LRU replacement policy."  # 2Q dropped
    assert diff_gate_ok(orig, good) is True
    assert diff_gate_ok(orig, bad) is False


def test_subject_phrase_extraction():
    text = "# Kestrel indexer\n\nThe Kestrel indexer is a distributed vector-search indexer."
    spans = sentence_spans(text)
    assert _subject_phrase(text, spans) == "The Kestrel indexer"


def _doc():
    text = (
        "# Kestrel indexer\n\n"
        "The Kestrel indexer is a distributed vector-search indexer.\n\n"
        "The operations runbook documents rolling upgrades and health checks.\n\n"
        "This system evicts hot vectors using a 2Q replacement policy.\n\n"
        "To recap, this system evicts hot vectors using a 2Q replacement policy.\n\n"
        "It listens for gRPC traffic on port 50051 by default."
    )
    return Document("d1", text)


def test_reference_resolution_injects_subject_and_preserves_provenance():
    doc = _doc()
    ch = FormatterChunker({"reference_resolution": True, "dedup": True,
                           "right_size": True, "soft_target_tokens": 64,
                           "verbatim_guardrail": True, "diff_gate": True})
    units = ch.chunk(doc)
    joined = " ".join(u.text for u in units)
    # anaphora resolved: entity now appears where a pronoun stood
    assert "The Kestrel indexer evicts hot vectors" in joined
    assert "The Kestrel indexer listens for gRPC traffic on port 50051" in joined
    # protected tokens survive
    assert "2Q" in joined and "50051" in joined
    # provenance: every source range maps inside the original document
    for u in units:
        for (s, e) in u.source_ranges:
            assert 0 <= s < e <= len(doc.text)


def test_dedup_drops_recap_copy():
    doc = _doc()
    ch = FormatterChunker({"reference_resolution": False, "dedup": True,
                           "right_size": True, "soft_target_tokens": 512})
    units = ch.chunk(doc)
    joined = " ".join(u.text for u in units)
    assert joined.count("evicts hot vectors using a 2Q") == 1  # recap removed


def test_dedup_preserves_provenance_of_removed_restatement():
    # v1.1 §5.1: gold anchored INSIDE a removed restatement must still score a hit via
    # the surviving merged unit (its source_ranges must cover the absorbed duplicate).
    from src.datasets.base import GoldSpan, Query
    from src.score.provenance import is_hit
    doc = _doc()
    # locate the "To recap, ... 2Q ..." restatement span in the original text
    recap = "To recap, this system evicts hot vectors using a 2Q replacement policy."
    start = doc.text.index(recap)
    gold = GoldSpan("d1", start, start + len(recap))
    q = Query("q", "which policy?", [gold], qtype="factual")

    ch = FormatterChunker({"reference_resolution": True, "dedup": True,
                           "right_size": True, "soft_target_tokens": 512})
    units = ch.chunk(doc)
    # the recap sentence itself was removed, but some surviving unit must be a hit
    assert any(is_hit(u, q) for u in units), "removed restatement lost provenance"


def test_nosize_min_unit_floor_merges_micro_units():
    # v1.1 §8c: with right_size OFF, per-sentence paragraphs must be merged to >=30 tok
    doc = _doc()
    ch = FormatterChunker({"reference_resolution": False, "dedup": False,
                           "right_size": False, "min_unit_tokens": 30})
    from src.textutil import count_tokens
    units = ch.chunk(doc)
    # every unit (except possibly a lone final one) should clear the floor-ish size
    assert all(count_tokens(u.text) >= 20 for u in units[:-1] or units)


def test_markers_only_keeps_text_verbatim():
    doc = _doc()
    ch = FormatterChunker({"markers_only": True, "reference_resolution": True,
                           "dedup": True, "right_size": False,
                           "soft_target_tokens": 64})
    units = ch.chunk(doc)
    joined = " ".join(u.text for u in units)
    # no reference resolution and no dedup: pronoun + recap remain verbatim
    assert "This system evicts hot vectors using a 2Q replacement policy." in joined
    assert joined.count("evicts hot vectors using a 2Q") == 2
