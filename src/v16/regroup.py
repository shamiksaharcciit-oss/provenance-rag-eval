"""v1.6 — the `F@S` transplant: FULL's edited sentences, grouped at SEAM's boundaries.

`F@S` splits the treatment term. `D_edit = F − S` is the TOTAL effect of enabling the editing
pass, boundary shift included, because editing changes `st.text` and `st.kept`, and `_right_size`
groups by `count_tokens(st.text)` over `st.kept` — so the cuts move as a *consequence* of the
treatment (Gate 0 G9: 0/45 Track A documents share boundaries between SEAM and FULL).

    D_text(m)   = F@S(m) − S(m)      editing at SEAM's seams          (direct effect)
    D_reseam(m) = F(m)   − F@S(m)    the boundary shift editing causes (indirect)

`F@S` rather than `S@F` is the pre-registered arm: it denies the edited text its preferred seams,
so a positive `D_text` survives its own worst case, and it puts no treatment-derived information
inside a control.

**The assignment rule IS the arm definition.** Each of FULL's kept sentences goes to the SEAM
segment containing the start of its first source range; sentences are concatenated in order
within each segment through the same `_emit` path FULL uses, so the scorer sees nothing new in
kind. A different rule would be a different experiment.

Nothing here scores, retrieves or embeds. It builds units.
"""
from __future__ import annotations

from src.chunkers.base import ChunkContext, Unit
from src.chunkers.formatter import FormatterChunker
from src.datasets.base import Document

Range = tuple[int, int]


class TransplantUnsupported(AssertionError):
    """The code does not support the assignment rule as specified. Stop and report."""


class RegroupingGateFailed(AssertionError):
    """`F@S` is not a pure re-grouping of `F`: a sentence was dropped, duplicated or reordered."""


def _capture_groups(chunker: FormatterChunker, doc: Document):
    """Run a formatter pass and keep the sentence layer `_emit` would otherwise consume."""
    captured: list[list] = []
    original = chunker._emit

    def emit(d, groups):
        captured.append(groups)
        return original(d, groups)

    chunker._emit = emit                      # type: ignore[method-assign]
    try:
        units = chunker.chunk(doc)
    finally:
        chunker._emit = original              # type: ignore[method-assign]
    if len(captured) != 1:
        raise TransplantUnsupported(
            f"expected one _emit call per document, saw {len(captured)} — the transplant "
            f"assumes a single boundary-placement step")
    return units, captured[0]


def seam_segment_spans(seam_groups: list[list]) -> list[Range]:
    """SEAM's segments in ORIGINAL-document coordinates, in order."""
    spans = []
    for g in seam_groups:
        if not g:
            continue
        spans.append((min(s.start for s in g), max(s.end for s in g)))
    return spans


def _segment_of(start: int, spans: list[Range]) -> int:
    """Index of the SEAM segment containing `start`.

    SEAM's segments tile the sentence sequence in order, so a sentence start falls in exactly one
    of them. A start beyond the last segment's end can only happen if the two passes saw
    different sentences, which is the condition this raises on.
    """
    for i, (s, e) in enumerate(spans):
        if s <= start < e:
            return i
    for i, (s, _) in enumerate(spans):
        if start < s:
            return max(0, i - 1)
    return len(spans) - 1


def build_fas_units(doc: Document, full_params: dict, seam_params: dict,
                    ctx_full: ChunkContext, ctx_seam: ChunkContext) -> tuple[list[Unit], dict]:
    """FULL's kept sentences, regrouped onto SEAM's segments, emitted by FULL's own `_emit`.

    Returns `(units, diagnostics)`. Diagnostics carry the segment counts and any EMPTY segments —
    dedup can empty one, and an empty segment is data about what dedup removed, so it is reported
    rather than padded, forced or merged.
    """
    seam = FormatterChunker(seam_params, ctx_seam)
    full = FormatterChunker(full_params, ctx_full)
    _, seam_groups = _capture_groups(seam, doc)
    _, full_groups = _capture_groups(full, doc)

    spans = seam_segment_spans(seam_groups)
    if not spans:
        raise TransplantUnsupported(f"{doc.doc_id}: SEAM produced no segments")

    full_sentences = [s for g in full_groups for s in g]
    buckets: list[list] = [[] for _ in spans]
    for st in full_sentences:
        buckets[_segment_of(st.start, spans)].append(st)

    non_empty = [b for b in buckets if b]
    units = full._emit(doc, non_empty)
    diag = {"doc_id": doc.doc_id,
            "seam_segments": len(spans),
            "fas_units": len(units),
            "empty_segments": sum(1 for b in buckets if not b),
            "full_units": len(full_groups),
            "full_sentences": len(full_sentences)}
    return units, diag


def assert_pure_regrouping(doc: Document, fas_units: list[Unit], full_params: dict,
                           ctx_full: ChunkContext) -> None:
    """THE GATE. `F@S` must be a pure re-grouping of `F`: same text, same order, nothing lost.

    Compared under whitespace normalisation, because `_emit` joins sentences with a single space
    and the two arms group them differently — so run-length differences in whitespace are
    expected and are not what this checks. What it checks is that no sentence was dropped,
    duplicated or reordered.
    """
    full_units = FormatterChunker(full_params, ctx_full).chunk(doc)
    a = " ".join(u.text for u in fas_units).split()
    b = " ".join(u.text for u in full_units).split()
    if a != b:
        first = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
        raise RegroupingGateFailed(
            f"{doc.doc_id}: F@S is not a pure re-grouping of F. tokens {len(a)} vs {len(b)}; "
            f"first divergence at {first}: {a[first:first + 6]} vs {b[first:first + 6]}")
