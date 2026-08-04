"""Offset-preserving text utilities shared by chunkers.

Everything returns CHARACTER OFFSETS into the original document so that provenance
(§6) is exact regardless of how a chunker groups text.

Token counting is an intentional approximation (regex word+punct tokens), applied
identically across all conditions so chunk-size budgets are comparable (§5.3).
"""
from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
# Sentence terminator followed by whitespace; keeps the terminator with the sentence.
_SENT_END_RE = re.compile(r"[.!?]+(?=\s|$)")


def count_tokens(text: str) -> int:
    """Approximate token count (regex word/punct units)."""
    return len(_TOKEN_RE.findall(text))


def sentence_spans(text: str) -> list[tuple[int, int]]:
    """Return (start, end) char spans of sentences, trimmed of surrounding space.

    Splits on ., !, ? at end-of-sentence and on blank lines. Offsets index the
    ORIGINAL text. Empty/whitespace-only fragments are dropped.
    """
    spans: list[tuple[int, int]] = []
    n = len(text)
    pos = 0
    # First split on hard paragraph breaks, then on sentence terminators within.
    for para in _paragraph_spans(text):
        p0, p1 = para
        cur = p0
        for m in _SENT_END_RE.finditer(text, p0, p1):
            end = m.end()
            seg = _trim(text, cur, end)
            if seg:
                spans.append(seg)
            cur = end
        # trailing fragment with no terminator
        seg = _trim(text, cur, p1)
        if seg:
            spans.append(seg)
    return spans


def _paragraph_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for m in re.finditer(r"[^\n]+(?:\n(?!\s*\n)[^\n]+)*", text):
        spans.append((m.start(), m.end()))
    if not spans and text.strip():
        spans.append((0, len(text)))
    return spans


def paragraph_spans(text: str) -> list[tuple[int, int]]:
    """Public: blank-line-separated paragraph spans (trimmed)."""
    out = []
    for s, e in _paragraph_spans(text):
        t = _trim(text, s, e)
        if t:
            out.append(t)
    return out


def _trim(text: str, s: int, e: int) -> tuple[int, int] | None:
    while s < e and text[s].isspace():
        s += 1
    while e > s and text[e - 1].isspace():
        e -= 1
    return (s, e) if e > s else None


def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Union of char ranges, sorted and coalesced."""
    if not ranges:
        return []
    rs = sorted(ranges)
    out = [list(rs[0])]
    for s, e in rs[1:]:
        if s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(s, e) for s, e in out]
