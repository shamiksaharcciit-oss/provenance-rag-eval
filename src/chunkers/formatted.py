"""Composition conditions C4 and C5 (v1.1 §3).

Both run the semantic formatter FIRST (reference-resolution + dedup + right-size, the
same full pass as C3) to produce a formatted corpus, then apply a DIFFERENT downstream
strategy — testing whether formatting *improves existing chunking* (hypothesis H4):

  C4 = formatted corpus + NAIVE fixed-size chunking (markers ignored) — does formatting
       help a dumb chunker?
  C5 = formatted corpus + CONTEXTUAL blurbs on the formatted units (stacked) — does
       formatting compose with contextual retrieval?

Provenance stays in ORIGINAL-document coordinates. For C4 a re-chunk of the formatted
text maps back to original ranges via the formatter units it overlaps; for C5 the
formatter units' source_ranges are used directly (blurb excluded, as in C2).
"""
from __future__ import annotations

import re

from src.chunkers.base import Chunker, ChunkContext, Unit
from src.chunkers.contextual import ContextualChunker
from src.chunkers.formatter import FormatterChunker
from src.datasets.base import Document
from src.textutil import merge_ranges

_TOKEN_SPAN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)

_SEP = "\n\n"


def _formatter_params(params: dict) -> dict:
    """Full-pass formatter params (the formatted corpus is the C3 corpus)."""
    return {
        "reference_resolution": params.get("reference_resolution", True),
        "dedup": params.get("dedup", True),
        "right_size": params.get("right_size", True),
        "boundary_markers": True,
        "verbatim_guardrail": params.get("verbatim_guardrail", True),
        "diff_gate": params.get("diff_gate", True),
        "soft_target_tokens": params.get("soft_target_tokens", 384),
        # v1.2: passes through to the formatter; False for baselines (byte-identical v1.1).
        "identity_injection": params.get("identity_injection", False),
    }


def _formatted_segments(fmt_units: list[Unit]) -> tuple[str, list[tuple[int, int, list]]]:
    """Concatenate formatter units into one formatted document, tracking for each
    unit its [start,end) span in the formatted text and its original source_ranges."""
    parts, segments, pos = [], [], 0
    for u in fmt_units:
        if parts:
            pos += len(_SEP)
        start = pos
        parts.append(u.text)
        pos += len(u.text)
        segments.append((start, pos, u.source_ranges))
    return _SEP.join(parts), segments


class FormattedNaiveChunker(Chunker):
    """C4 — formatted corpus, then naive fixed-size chunking (ignore markers)."""
    condition_id = "C4"

    def __init__(self, params: dict, ctx: ChunkContext | None = None) -> None:
        super().__init__(params, ctx)
        self.formatter = FormatterChunker(_formatter_params(params), ctx)

    def chunk(self, doc: Document) -> list[Unit]:
        fmt_units = self.formatter.chunk(doc)
        if not fmt_units:
            return []
        ftext, segments = _formatted_segments(fmt_units)
        spans = [(m.start(), m.end()) for m in _TOKEN_SPAN_RE.finditer(ftext)]
        if not spans:
            return []
        chunk_tokens = max(1, int(self.params.get("chunk_tokens", 768)))
        overlap = self.params.get("overlap_frac", 0.0)
        step = max(1, int(round(chunk_tokens * (1.0 - overlap))))

        units: list[Unit] = []
        i, ui = 0, 0
        n = len(spans)
        while i < n:
            j = min(n, i + chunk_tokens)
            cs, ce = spans[i][0], spans[j - 1][1]
            # union source_ranges of every formatter segment this chunk overlaps
            src: list = []
            for (s0, s1, sr) in segments:
                if s1 > cs and s0 < ce:
                    src.extend(sr)
            units.append(Unit(
                unit_id=f"{self.condition_id}:{doc.doc_id}:{ui}",
                text=ftext[cs:ce], doc_id=doc.doc_id,
                source_ranges=merge_ranges(src),
                meta={"corpus": "formatted", "chunk_tokens": chunk_tokens},
            ))
            ui += 1
            if j >= n:
                break
            i += step
        return units


class FormattedContextualChunker(Chunker):
    """C5 — formatted corpus, then contextual blurbs on the formatted units (stacked)."""
    condition_id = "C5"

    def __init__(self, params: dict, ctx: ChunkContext | None = None) -> None:
        super().__init__(params, ctx)
        self.formatter = FormatterChunker(_formatter_params(params), ctx)
        # reuse C2's blurb generation (same prompt/model, cached by content hash)
        self._blurber = ContextualChunker(params, ctx)

    def chunk(self, doc: Document) -> list[Unit]:
        units = self.formatter.chunk(doc)
        if not units:
            return []
        doc_summary = self._blurber._doc_summary(doc)
        for u in units:
            blurb = self._blurber._blurb(doc, u.text, doc_summary)
            # blurb prepended to indexed text but NOT part of source_ranges (§6.1)
            u.text = f"{blurb}\n\n{u.text}"
            u.unit_id = u.unit_id.replace("C3:", "C5:", 1)
            u.meta["blurb"] = blurb
            u.meta["corpus"] = "formatted"
        return units
