"""C0 — Naive fixed-size chunking (plan §5.2). The floor.

Fixed token window + overlap over the raw document. Units are verbatim substrings,
so provenance is trivial: source_ranges are the substring's own char offsets (§6.1).
"""
from __future__ import annotations

import re

from src.chunkers.base import Chunker, Unit
from src.datasets.base import Document

# Word/punct token spans, so a token budget maps to exact char offsets.
_TOKEN_SPAN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def _token_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in _TOKEN_SPAN_RE.finditer(text)]


def fixed_size_units(doc: Document, chunk_tokens: int, overlap_frac: float,
                     condition_id: str) -> list[Unit]:
    spans = _token_spans(doc.text)
    n = len(spans)
    if n == 0:
        return []
    chunk_tokens = max(1, int(chunk_tokens))
    step = max(1, int(round(chunk_tokens * (1.0 - overlap_frac))))
    units: list[Unit] = []
    i = 0
    ui = 0
    while i < n:
        j = min(n, i + chunk_tokens)
        start_char = spans[i][0]
        end_char = spans[j - 1][1]
        text = doc.text[start_char:end_char]
        units.append(Unit(
            unit_id=f"{condition_id}:{doc.doc_id}:{ui}",
            text=text,
            doc_id=doc.doc_id,
            source_ranges=[(start_char, end_char)],
            meta={"chunk_tokens": chunk_tokens, "overlap_frac": overlap_frac},
        ))
        ui += 1
        if j >= n:
            break
        i += step
    return units


class NaiveChunker(Chunker):
    condition_id = "C0"

    def chunk(self, doc: Document) -> list[Unit]:
        return fixed_size_units(
            doc,
            chunk_tokens=self.params.get("chunk_tokens", 384),
            overlap_frac=self.params.get("overlap_frac", 0.1),
            condition_id=self.condition_id,
        )
