"""v1.6 G6 — the SEAM partition gate, in its weakened three-part form, plus the gold-span check.

The original gate demanded byte-verbatim reconstruction. That conflated two things: whether the
formatter changes *vocabulary* (the property SEAM depends on) and whether `_emit` preserves the
*join separator* (an artifact). It failed on 10/10 Track A documents purely on the second —
`_emit` joins sentences with a single space, so `'# Kestrel indexer\\n\\n'` became
`'# Kestrel indexer '`. No word, identifier or number changed.

The gate is therefore:

  1. whitespace-normalised equality — concatenated SEAM units reproduce the document, character
     for character, under the same normalisation on both sides;
  2. exact coverage — the union of SEAM `source_ranges` covers every NON-WHITESPACE character
     exactly once;
  3. non-overlap — unchanged.

Plus the assertion that replaces an argument with a check (A1g): every gold span in the Track A
test set overlaps at least one SEAM `source_range`. That was previously reasoned to be true from
ANY-overlap scoring; reasoning is a HYPOTHESIS, this makes it VERIFIED.

Run under the FINAL SEAM configuration — `markers_only: True`, the deterministic path — not the
rule-based path the earlier probe used, because the gate has to pass on the arm that runs.
"""
from __future__ import annotations

import os
import re

import pytest

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from src import config as C
from src.chunkers.base import ChunkContext
from src.chunkers.formatter import FormatterChunker
from src.datasets import load_track_dataset
from src.llm.client import LLMClient
from src.textutil import merge_ranges

# The FINAL SEAM configuration. `markers_only` forces the deterministic path (formatter.py:184)
# and zeroes do_ref/do_dedup (204-205). Note line 243: right-sizing runs regardless of
# `right_size`, which is why C3-markeronly lands on 90 units rather than 1552.
SEAM_768 = {"soft_target_tokens": 768, "reference_resolution": False, "dedup": False,
            "right_size": False, "boundary_markers": False, "markers_only": True,
            "verbatim_guardrail": True, "diff_gate": True}
SEAM_384 = {**SEAM_768, "soft_target_tokens": 384}

_WS = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _WS.sub(" ", s).strip()


@pytest.fixture(scope="module")
def track_a():
    cfg = C.load_default()
    cfg.setdefault("_cache_root", "cache")
    tr = C.load_track("A")
    ds = load_track_dataset(tr, cfg["seed"])
    ctx = ChunkContext(embedder=None, llm=LLMClient(provider="none"), config=cfg)
    return ds, ctx


@pytest.fixture(scope="module")
def seam_units(track_a):
    ds, ctx = track_a
    return {d.doc_id: (d, FormatterChunker(SEAM_768, ctx).chunk(d)) for d in ds.documents}


# --------------------------------------------------------------------------
# Part 1 — whitespace-normalised equality
# --------------------------------------------------------------------------

def test_G6_1_whitespace_normalised_equality(seam_units):
    """No vocabulary changed: the token stream is identical under normalisation."""
    bad = []
    for doc_id, (doc, units) in seam_units.items():
        if _norm(" ".join(u.text for u in units)) != _norm(doc.text):
            bad.append(doc_id)
    assert not bad, f"SEAM changed text on {len(bad)} documents: {bad[:5]}"


def test_G6_1_is_not_vacuous_a_changed_word_must_fail(seam_units):
    """§A1b — the check must be seen to fail. One substituted word is the smallest violation
    that matters, and it is exactly what the standing editorial rule forbids."""
    doc, units = next(iter(seam_units.values()))
    tampered = [u.text for u in units]
    tampered[0] = tampered[0].replace("indexer", "indexor", 1)
    assert _norm(" ".join(tampered)) != _norm(doc.text) or "indexer" not in units[0].text


# --------------------------------------------------------------------------
# Part 2 — exact coverage of every non-whitespace character
# --------------------------------------------------------------------------

def test_G6_2_covers_every_non_whitespace_character_exactly_once(seam_units):
    bad = []
    for doc_id, (doc, units) in seam_units.items():
        covered = bytearray(len(doc.text))
        for u in units:
            for s, e in u.source_ranges:
                for i in range(s, e):
                    covered[i] += 1
        missed = sum(1 for i, ch in enumerate(doc.text) if not ch.isspace() and covered[i] == 0)
        twice = sum(1 for i, ch in enumerate(doc.text) if not ch.isspace() and covered[i] > 1)
        if missed or twice:
            bad.append((doc_id, missed, twice))
    assert not bad, f"non-whitespace coverage defects on {len(bad)} docs: {bad[:5]}"


# --------------------------------------------------------------------------
# Part 3 — non-overlap
# --------------------------------------------------------------------------

def test_G6_3_ranges_do_not_overlap(seam_units):
    bad = []
    for doc_id, (_doc, units) in seam_units.items():
        rs = [r for u in units for r in u.source_ranges]
        if sum(e - s for s, e in rs) != sum(e - s for s, e in merge_ranges(rs)):
            bad.append(doc_id)
    assert not bad, f"overlapping source_ranges on: {bad[:5]}"


# --------------------------------------------------------------------------
# The gold-span assertion — replaces an argument with a check (A1g)
# --------------------------------------------------------------------------

def test_every_gold_span_overlaps_at_least_one_seam_range(track_a, seam_units):
    """Previously argued from ANY-overlap scoring; now verified.

    A gold span crossing a sentence boundary spans inter-sentence whitespace that no
    `source_range` claims — so the argument was that it still overlaps the sentences either
    side. This asserts it for every gold span in the test set rather than trusting that.
    """
    ds, _ = track_a
    by_doc = {}
    for doc_id, (_d, units) in seam_units.items():
        by_doc[doc_id] = merge_ranges([r for u in units for r in u.source_ranges])
    unreachable = []
    for q in ds.queries:
        for g in q.gold_spans:
            rs = by_doc.get(g.doc_id, [])
            if not any(min(e, g.end_char) > max(s, g.start_char) for s, e in rs):
                unreachable.append((q.query_id, g.doc_id, g.start_char, g.end_char))
    assert not unreachable, (
        f"{len(unreachable)} gold spans overlap NO SEAM range — scoring would be broken: "
        f"{unreachable[:5]}")


def test_gate_holds_at_the_other_declared_size(track_a):
    """384 as well as 768 — a partition property must not depend on the size dial."""
    ds, ctx = track_a
    for d in ds.documents[:12]:
        units = FormatterChunker(SEAM_384, ctx).chunk(d)
        assert _norm(" ".join(u.text for u in units)) == _norm(d.text), d.doc_id
