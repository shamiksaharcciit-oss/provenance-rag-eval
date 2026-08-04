"""v1.6 — the `F@S` transplant gate.

`F@S` takes FULL's kept sentences and groups them at SEAM's boundaries, so that

    D_text   = F@S − S     editing at SEAM's seams          (direct effect)
    D_reseam = F   − F@S   the boundary shift editing causes (indirect)

split the total `D_edit = F − S`. The transplant is a **pure re-grouping**: no sentence gained,
none lost, order preserved. If that fails, `D_text` and `D_reseam` measure nothing, so the gate
is a halt condition rather than a diagnostic.

Compared under whitespace normalisation, because `_emit` joins with a single space and the two
arms group differently — run-length differences in whitespace are expected and are not what this
tests. What it tests is the token stream.

Nothing here scores, retrieves or embeds.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from src import config as C
from src.chunkers.base import ChunkContext
from src.datasets import load_track_dataset
from src.llm.client import LLMClient, build_llm
from src.v16.regroup import (RegroupingGateFailed, assert_pure_regrouping,
                             build_fas_units, seam_segment_spans)

SEAM = {"soft_target_tokens": 768, "reference_resolution": False, "dedup": False,
        "right_size": False, "boundary_markers": False, "markers_only": True,
        "verbatim_guardrail": True, "diff_gate": True}
FULL = {"soft_target_tokens": 768, "reference_resolution": True, "dedup": True,
        "right_size": True, "boundary_markers": True, "verbatim_guardrail": True,
        "diff_gate": True}


@pytest.fixture(scope="module")
def env():
    cfg = C.load_default()
    cfg.setdefault("_cache_root", "cache")
    cfg["llm"]["provider"] = "anthropic"
    tr = C.load_track("A")
    tm = tr.get("params", {}).get("llm_model")
    tcfg = C.deep_merge(cfg, {"llm": {"model": tm}}) if tm else cfg
    ds = load_track_dataset(tr, tcfg["seed"])
    ctx_full = ChunkContext(embedder=None, llm=build_llm(tcfg), config=tcfg)
    ctx_seam = ChunkContext(embedder=None, llm=LLMClient(provider="none"), config=tcfg)
    return ds, ctx_full, ctx_seam


@pytest.fixture(scope="module")
def built(env):
    ds, cf, cs = env
    out = {}
    for d in ds.documents:
        out[d.doc_id] = (d,) + build_fas_units(d, FULL, SEAM, cf, cs)
    return out


# --------------------------------------------------------------------------
# THE GATE
# --------------------------------------------------------------------------

def test_fas_is_a_pure_regrouping_of_full(built, env):
    """Halt condition. Every document, no exceptions."""
    _ds, cf, _cs = env
    for doc_id, (doc, units, _diag) in built.items():
        assert_pure_regrouping(doc, units, FULL, cf)


def test_the_gate_is_not_vacuous_a_dropped_sentence_must_fail(built, env):
    """§A1b — demonstrate it firing. Dropping one unit is the coarsest possible violation and
    the gate must not absorb it."""
    _ds, cf, _cs = env
    doc, units, _ = next(iter(built.values()))
    with pytest.raises(RegroupingGateFailed):
        assert_pure_regrouping(doc, units[:-1], FULL, cf)


def test_the_gate_fires_on_a_duplicated_sentence(built, env):
    """The other direction: a re-grouping that duplicates rather than drops."""
    _ds, cf, _cs = env
    doc, units, _ = next(iter(built.values()))
    with pytest.raises(RegroupingGateFailed):
        assert_pure_regrouping(doc, list(units) + [units[0]], FULL, cf)


# --------------------------------------------------------------------------
# Segment counts and empty segments — reported, never forced
# --------------------------------------------------------------------------

def test_fas_lands_on_seams_segment_count(built):
    """`F@S` should carry SEAM's segmentation, not FULL's — that is the whole point."""
    for doc_id, (_doc, units, diag) in built.items():
        assert diag["fas_units"] + diag["empty_segments"] == diag["seam_segments"], (
            f"{doc_id}: {diag}")


# --------------------------------------------------------------------------
# Empty segments: TWO claims, two tests, each named for what it asserts.
#
# A single test previously asserted a corpus fact under a behavioural name. The name is what a
# reader sees when it fails, so the first corpus with an empty segment would have produced a
# failure saying the code padded something, when the code had behaved correctly and only the
# corpus differed. The claims are:
#   1. behavioural, corpus-independent — when a segment IS empty, it is reported, not padded,
#      merged, forced or silently dropped. True or false about the implementation.
#   2. a Track A measurement — this corpus yields zero. A regression pin, not a gate.
# --------------------------------------------------------------------------

def test_empty_segment_is_reported_not_padded():
    """CLAIM 1, hard on every corpus, forever. The fixture is CONSTRUCTED rather than waited
    for: a document whose middle SEAM segments consist entirely of sentences dedup removes."""
    from src.datasets.base import Document
    ctx = ChunkContext(embedder=None, llm=LLMClient(provider="none"), config={})
    uniq = [f"Node {i:02d} reports heartbeat to the coordinator process." for i in range(6)]
    dup = "The Kestrel indexer listens on port 50051."
    doc = Document(doc_id="empty-seg", text=" ".join([dup] + uniq[:2] + [dup] * 5 + uniq[2:]))
    seam = {**SEAM, "soft_target_tokens": 18}
    full = {**FULL, "soft_target_tokens": 18, "reference_resolution": False}

    units, diag = build_fas_units(doc, full, seam, ctx, ctx)

    assert diag["empty_segments"] > 0, "the fixture must actually empty a segment"
    # reported...
    assert diag["empty_segments"] == diag["seam_segments"] - diag["fas_units"]
    # ...not padded, merged or forced: no empty unit is emitted to stand in for one
    assert all(u.text.strip() for u in units), "an empty segment was padded into a unit"
    assert len(units) == diag["fas_units"] < diag["seam_segments"]
    # ...and downstream scoring still proceeds: every emitted unit carries usable provenance
    assert all(u.source_ranges for u in units)


def test_track_a_has_no_empty_segments(built):
    """CLAIM 2, hard on TRACK A ONLY, pinning the observed value.

    If this fires, something changed underneath — dedup behaviour, the corpus, or the tokenizer
    — and that also means the published C3 corpus is no longer what it was. On Track B or any
    other corpus the count is REPORTED AND THE RUN CONTINUES; it is a recorded field of every
    arm, like D_ws. The reasoning lives in the plan, not only here.
    """
    total = sum(d["empty_segments"] for _doc, _u, d in built.values())
    assert total == 0, (
        f"Track A now yields {total} empty segments where it yielded 0. This is not a v1.6 "
        f"defect: it means dedup, the corpus or the tokenizer changed, and the published C3 "
        f"corpus is no longer what it was.")


def test_seam_segments_are_ordered_and_disjoint(env):
    """The assignment rule sends a sentence to the segment containing its start, which is only
    well defined if the segments are ordered and non-overlapping."""
    ds, _cf, cs = env
    from src.v16.regroup import _capture_groups
    from src.chunkers.formatter import FormatterChunker
    for d in ds.documents[:12]:
        _u, groups = _capture_groups(FormatterChunker(SEAM, cs), d)
        spans = seam_segment_spans(groups)
        assert spans == sorted(spans), d.doc_id
        assert all(spans[i][1] <= spans[i + 1][0] for i in range(len(spans) - 1)), d.doc_id


def test_fas_differs_from_full_which_is_why_the_arm_exists(built, env):
    """If `F@S` reproduced `F` unit-for-unit there would be no boundary shift to measure and
    `D_reseam` would be identically zero by construction. Gate 0 G9 measured 0/45 documents
    sharing boundaries; this pins that the transplant actually moves them."""
    _ds, cf, _cs = env
    from src.chunkers.formatter import FormatterChunker
    differing = 0
    for doc_id, (doc, units, _d) in built.items():
        full = FormatterChunker(FULL, cf).chunk(doc)
        if [u.source_ranges for u in units] != [u.source_ranges for u in full]:
            differing += 1
    assert differing == len(built), (
        f"only {differing}/{len(built)} documents differ between F@S and F — if this is not all "
        f"of them, D_reseam is zero by construction on the rest")
