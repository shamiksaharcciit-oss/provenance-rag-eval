"""PW-1 — sentence-accurate ("tight") provenance for formatted units.

Arm 2b needs, for every fmt256 chunk, the original-document ranges of **exactly the sentences
its own text covers** — not the whole `source_ranges` of every formatter segment it overlaps.
Production merges that information away twice (`FormatterChunker._emit`, then
`_formatted_segments`), so it cannot be recovered from a built corpus post-hoc. This rebuilds
the same chunks while retaining the sentence layer.

Three range sets per chunk:

  claimed   what production ships — union of every overlapped formatter segment's ranges
  tight     original spans of exactly the sentences the chunk's own text covers
  absorbed  original spans of duplicate sentences absorbed by sentences the chunk covers

`claimed \\ tight` is the width the paper's §11 threats paragraph is about. It has two
components — absorption and chunk-to-segment inheritance — and step 0 measures them separately.

**Drift guard.** This re-derives chunk boundaries rather than importing them, so it asserts that
the chunks it produces are identical to production's in id, text, and claimed ranges. If the
production chunker changes, this fails loudly instead of silently measuring a different corpus.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.chunkers.base import ChunkContext, Unit
from src.chunkers.formatted import _SEP, _TOKEN_SPAN_RE, FormattedNaiveChunker
from src.chunkers.formatter import FormatterChunker
from src.datasets.base import Document
from src.textutil import merge_ranges

Range = tuple[int, int]


class TightProvenanceMismatch(AssertionError):
    """Re-derived chunks disagree with production's. Every downstream number is void."""


@dataclass
class TightUnit:
    """A production fmt256 chunk plus the range sets production discards.

    Four disjoint components, from which the frozen scoring ladder is assembled:

      own                original spans of the sentences this chunk's own text COVERS
      absorbed_own       duplicate ranges absorbed by those covered sentences
      inherited_own      original spans of SIBLING sentences in overlapped segments that this
                         chunk does not contain
      inherited_absorbed duplicate ranges absorbed by those sibling sentences

    `claimed` (production's `source_ranges`) is the union of all four, which the drift guard
    asserts against production per document.
    """
    unit_id: str
    doc_id: str
    text: str
    claimed: list[Range]
    own: list[Range]
    absorbed_own: list[Range]
    inherited_own: list[Range]
    inherited_absorbed: list[Range]
    n_sentences: int = 0
    n_sibling_sentences: int = 0
    meta: dict = field(default_factory=dict)

    # ---- the frozen scoring ladder ----
    @property
    def S0(self) -> list[Range]:
        """own + absorbed + inherited — CLAIMED. The published scoring."""
        return list(self.claimed)

    @property
    def S1(self) -> list[Range]:
        """own + inherited — minus-absorbed. Strips EVERY absorbed range, siblings' included."""
        return merge_ranges(self.own + self.inherited_own)

    @property
    def S2(self) -> list[Range]:
        """own + absorbed — minus-inherited. PRIMARY: the ruler the paper's methods describe."""
        return merge_ranges(self.own + self.absorbed_own)

    @property
    def S3(self) -> list[Range]:
        """own only — minus-both. The conservative floor."""
        return merge_ranges(list(self.own))

    # `tight` and `absorbed` are the pre-ladder names, kept so step 0 keeps reading.
    @property
    def tight(self) -> list[Range]:
        return self.S3

    @property
    def absorbed(self) -> list[Range]:
        return merge_ranges(list(self.absorbed_own))

    def as_unit(self, scoring: str = "S2") -> Unit:
        """A `Unit` carrying one scoring's ranges, for the frozen hit test."""
        if scoring not in ("S0", "S1", "S2", "S3"):
            raise ValueError(f"unknown scoring {scoring!r}; expected S0/S1/S2/S3")
        return Unit(unit_id=self.unit_id, text=self.text, doc_id=self.doc_id,
                    source_ranges=list(getattr(self, scoring)),
                    meta={**self.meta, "pw1_scoring": scoring})


def _capture_groups(formatter: FormatterChunker, doc: Document):
    """Run the formatter, returning (units, groups) — groups is the sentence layer."""
    captured: list[list] = []
    original_emit = formatter._emit

    def emit(d, groups):
        captured.append(groups)
        return original_emit(d, groups)

    formatter._emit = emit          # type: ignore[method-assign]
    try:
        units = formatter.chunk(doc)
    finally:
        formatter._emit = original_emit    # type: ignore[method-assign]
    if not units:
        return [], []
    if len(captured) != 1:
        raise TightProvenanceMismatch(
            f"expected one _emit call per document, saw {len(captured)}")
    return units, captured[0]


def build_tight_units(doc: Document, params: dict, ctx: ChunkContext,
                      condition_id: str | None = None) -> list[TightUnit]:
    """Rebuild `doc`'s formatted chunks with the sentence layer retained.

    `condition_id` overrides the chunker's class attribute so unit ids match production's. The
    harness names units after the CONDITION id, which is "C4" in the main runs but "fmt256" for
    the size-matched control -- so a rebuild that hard-codes the class attribute produces ids
    that no persisted ranked list refers to.
    """
    prod = FormattedNaiveChunker(params, ctx)
    if condition_id:
        prod.condition_id = condition_id
    fmt_units, groups = _capture_groups(prod.formatter, doc)
    if not fmt_units:
        return []
    if len(fmt_units) != len(groups):
        raise TightProvenanceMismatch(
            f"{len(fmt_units)} formatter units vs {len(groups)} sentence groups")

    # Rebuild the formatted document exactly as `_formatted_segments` does, but track each
    # SENTENCE's span in the formatted text alongside its original span.
    # `_emit` joins a group's sentence texts with a single space.
    parts: list[str] = []
    # fs, fe, os, oe, absorbed, segment_index — the segment index is what makes a SIBLING
    # sentence identifiable: one in an overlapped segment that the chunk does not itself cover.
    sent_spans: list[tuple[int, int, int, int, list[Range], int]] = []
    pos = 0
    for gi_, (u, g) in enumerate(zip(fmt_units, groups)):
        if parts:
            pos += len(_SEP)
        start = pos
        parts.append(u.text)
        off = start
        for si, st in enumerate(g):
            if si:
                off += 1                       # the joining space
            sent_spans.append((off, off + len(st.text), st.start, st.end,
                               list(st.absorbed), gi_))
            off += len(st.text)
        if off != start + len(u.text):
            raise TightProvenanceMismatch(
                f"sentence offsets do not tile unit {u.unit_id}: {off} vs "
                f"{start + len(u.text)}")
        pos += len(u.text)
    ftext = _SEP.join(parts)

    segments = [(s, e, u.source_ranges) for (s, e), u in
                zip(_segment_spans(fmt_units), fmt_units)]

    spans = [(m.start(), m.end()) for m in _TOKEN_SPAN_RE.finditer(ftext)]
    if not spans:
        return []
    chunk_tokens = max(1, int(params.get("chunk_tokens", 768)))
    overlap = params.get("overlap_frac", 0.0)
    step = max(1, int(round(chunk_tokens * (1.0 - overlap))))

    out: list[TightUnit] = []
    i, ui, n = 0, 0, len(spans)
    while i < n:
        j = min(n, i + chunk_tokens)
        cs, ce = spans[i][0], spans[j - 1][1]
        claimed_raw: list[Range] = []
        overlapped_segments = set()
        for gi_, (s0, s1, sr) in enumerate(segments):
            if s1 > cs and s0 < ce:
                claimed_raw.extend(sr)
                overlapped_segments.add(gi_)
        own_raw: list[Range] = []
        absorbed_own_raw: list[Range] = []
        inherited_own_raw: list[Range] = []
        inherited_absorbed_raw: list[Range] = []
        n_sent = n_sib = 0
        for (fs, fe, os_, oe, absorbed, seg_ix) in sent_spans:
            if fe > cs and fs < ce:            # same half-open overlap test as segments
                own_raw.append((os_, oe))
                absorbed_own_raw.extend(absorbed)
                n_sent += 1
            elif seg_ix in overlapped_segments:
                # a SIBLING: its ranges reach this chunk only through segment inheritance
                inherited_own_raw.append((os_, oe))
                inherited_absorbed_raw.extend(absorbed)
                n_sib += 1
        out.append(TightUnit(
            unit_id=f"{prod.condition_id}:{doc.doc_id}:{ui}",
            doc_id=doc.doc_id, text=ftext[cs:ce],
            claimed=merge_ranges(claimed_raw),
            own=merge_ranges(own_raw),
            absorbed_own=merge_ranges(absorbed_own_raw),
            inherited_own=merge_ranges(inherited_own_raw),
            inherited_absorbed=merge_ranges(inherited_absorbed_raw),
            n_sentences=n_sent, n_sibling_sentences=n_sib,
            meta={"corpus": "formatted", "chunk_tokens": chunk_tokens},
        ))
        ui += 1
        if j >= n:
            break
        i += step

    _assert_matches_production(prod, doc, out)
    return out


def _segment_spans(fmt_units: list[Unit]) -> list[Range]:
    """Each formatter unit's [start, end) span in the concatenated formatted text."""
    spans, pos = [], 0
    for k, u in enumerate(fmt_units):
        if k:
            pos += len(_SEP)
        spans.append((pos, pos + len(u.text)))
        pos += len(u.text)
    return spans


def _assert_matches_production(prod: FormattedNaiveChunker, doc: Document,
                               rebuilt: list[TightUnit]) -> None:
    """The drift guard: rebuilt chunks must equal production's, claimed ranges included."""
    actual = prod.chunk(doc)
    if len(actual) != len(rebuilt):
        raise TightProvenanceMismatch(
            f"{doc.doc_id}: production produced {len(actual)} chunks, rebuild {len(rebuilt)}")
    for a, r in zip(actual, rebuilt):
        if a.unit_id != r.unit_id or a.text != r.text:
            raise TightProvenanceMismatch(f"{doc.doc_id}: chunk identity differs at {a.unit_id}")
        if [tuple(x) for x in a.source_ranges] != [tuple(x) for x in r.claimed]:
            raise TightProvenanceMismatch(
                f"{doc.doc_id}: claimed ranges differ at {a.unit_id}")
        # The four components must TILE claimed exactly. If they do not, the ladder is not a
        # decomposition of the published scoring and S1/S2/S3 mean nothing.
        parts_union = merge_ranges(r.own + r.absorbed_own + r.inherited_own
                                   + r.inherited_absorbed)
        if [tuple(x) for x in parts_union] != [tuple(x) for x in r.claimed]:
            raise TightProvenanceMismatch(
                f"{doc.doc_id}: own+absorbed+inherited does not reconstruct claimed at "
                f"{a.unit_id}")


def surface(ranges: list[Range]) -> int:
    """Characters covered by the union of `ranges`."""
    return sum(e - s for s, e in merge_ranges(list(ranges)))


def excess_ranges(claimed: list[Range], tight: list[Range]) -> list[Range]:
    """`claimed` minus `tight` — surface a unit claims but does not itself cover.

    This is the wide `D` of the §4.4 clean-gold redefinition: absorbed AND inherited.
    """
    keep: list[Range] = []
    tight_m = merge_ranges(list(tight))
    for s, e in merge_ranges(list(claimed)):
        cur = [(s, e)]
        for ts, te in tight_m:
            nxt: list[Range] = []
            for cs, ce in cur:
                if te <= cs or ts >= ce:
                    nxt.append((cs, ce))
                    continue
                if cs < ts:
                    nxt.append((cs, ts))
                if te < ce:
                    nxt.append((te, ce))
            cur = nxt
            if not cur:
                break
        keep.extend(cur)
    return merge_ranges(keep)
