"""Sentence-aligned child construction (amendment v1.5 §3).

ONE RULE ACROSS ALL THREE CONDITIONS
====================================
Split the condition's indexed text into sentences; greedily accumulate sentences into a child
until adding the next would exceed `child_tokens`; emit. A sentence longer than `child_tokens`
on its own is hard-cut at a token boundary.

`child_tokens` is a **ceiling, not a size** — conditions will not land on identical
distributions, which is why the realized distribution is reported per condition.

Why one rule rather than per-condition cutting: children now only RANK, and child cutting
quality drives ranking quality. Condition-asymmetric cutting would therefore be a machinery
advantage in the one place that determines the entire result. One rule across three corpora
means the only thing differing between conditions is **the corpus, not the machinery**.

Sentence alignment was originally adopted to give C4 derivable child provenance. Under v1.5
children are never scored, so that necessity evaporated; it is kept on the uniformity ground
above, which never depended on provenance (v1.5 §0e).

C2 CHILDREN CARRY THE BLURB
===========================
Every C2 child is `blurb + child text`, with `child_tokens` the ceiling on the child **text**
and the blurb prepended on top. That is what contextual retrieval actually does — context on
every indexed unit — and it keeps C2's child text directly comparable to C0's. Since children
only rank and are never scored or delivered, the extra blurb tokens carry no volume consequence
for the metric. The blurb-to-child ratio is reported as the dilution diagnostic: if C2's ranking
underperforms, near-duplicate sibling vectors is the first hypothesis and the ratio is how to
check it.

PROVENANCE
==========
Children are used only for ranking, so `source_ranges` are not required for the primary
comparison. They are populated where derivable (verbatim text, optionally behind a
provenance-free prefix) to support the H7c "localisation precision at fixed k" descriptive, and
left empty where they are not — never guessed. See `ProvenanceNotDerivable`.
"""
from __future__ import annotations

import re

from src.chunkers.base import Unit
from src.smalltobig.units import ChildParentPair, ParentContext
from src.textutil import sentence_spans

_TOKEN_SPAN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def _token_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in _TOKEN_SPAN_RE.finditer(text)]


def _n_tokens(text: str) -> int:
    return len(_TOKEN_SPAN_RE.findall(text))


class ProvenanceNotDerivable(RuntimeError):
    """Child offsets cannot be mapped to original document coordinates.

    Raised rather than guessed for the H7c descriptive. The alternatives would be handing
    children the parent's ranges (the dilution defect) or interpolating across edited text
    (fabricated provenance) — both produce numbers that look fine and are wrong.
    """


def _prefix_len(parent_unit: Unit, text: str) -> int | None:
    """Chars at the head of `text` with no document provenance (e.g. a C2 blurb).

    Returns None when provenance is not derivable at all — edited text (C4) or merged/disjoint
    ranges. Callers then emit children without `source_ranges`; ranking is unaffected.
    """
    if len(parent_unit.source_ranges) != 1:
        return None                      # merged/disjoint ranges — C4
    s, e = parent_unit.source_ranges[0]
    prefix = len(text) - (e - s)
    return prefix if prefix >= 0 else None   # text shorter than its range — edited


def _sentence_groups(text: str, child_tokens: int) -> list[tuple[int, int]]:
    """Greedy sentence accumulation up to the ceiling; oversized sentences hard-cut."""
    spans = sentence_spans(text)
    if not spans:
        return [(0, len(text))] if text.strip() else []

    groups: list[tuple[int, int]] = []
    cur_start: int | None = None
    cur_end = 0
    cur_tokens = 0

    for s, e in spans:
        n = _n_tokens(text[s:e])
        if n > child_tokens:
            # Sentence exceeds the ceiling on its own: flush, then hard-cut it at token
            # boundaries. The cut falls inside a single sentence, so provenance stays
            # derivable wherever it was derivable for the sentence.
            if cur_start is not None:
                groups.append((cur_start, cur_end))
                cur_start, cur_tokens = None, 0
            toks = _token_spans(text[s:e])
            for i in range(0, len(toks), child_tokens):
                chunk = toks[i:i + child_tokens]
                groups.append((s + chunk[0][0], s + chunk[-1][1]))
            continue
        if cur_start is None:
            cur_start, cur_end, cur_tokens = s, e, n
        elif cur_tokens + n <= child_tokens:
            cur_end, cur_tokens = e, cur_tokens + n
        else:
            groups.append((cur_start, cur_end))
            cur_start, cur_end, cur_tokens = s, e, n
    if cur_start is not None:
        groups.append((cur_start, cur_end))
    return groups


def split_unit(parent_unit: Unit, child_tokens: int, condition_id: str, parent_ix: int,
               blurb: str = "") -> list[ChildParentPair]:
    """Cut one baseline unit into sentence-aligned children.

    `blurb`, when given (C2/C5), is prepended to every child's indexed text and excluded from
    the ceiling, which applies to the child text alone.
    """
    text = parent_unit.text
    if not text.strip():
        return []

    prefix = _prefix_len(parent_unit, text)
    base = parent_unit.source_ranges[0] if parent_unit.source_ranges else None

    parent = ParentContext(
        parent_id=parent_unit.unit_id,
        text=text,
        doc_id=parent_unit.doc_id,
        char_span=(base if base else (0, len(text))),
        n_tokens=_n_tokens(text),
        meta={"condition": condition_id, "n_ranges": len(parent_unit.source_ranges)},
    )

    # Cut only the provenance-bearing tail when there is a blurb prefix inside the unit text;
    # otherwise the whole text.
    cut_from = prefix if (prefix is not None and prefix > 0) else 0
    body = text[cut_from:]

    out: list[ChildParentPair] = []
    for ci, (s_local, e_local) in enumerate(_sentence_groups(body, child_tokens)):
        child_text = body[s_local:e_local]
        if not child_text.strip():
            continue
        ranges: list[tuple[int, int]] = []
        if prefix is not None and base is not None:
            s_doc = base[0] + s_local
            e_doc = min(base[1], base[0] + e_local)
            if e_doc > s_doc:
                ranges = [(s_doc, e_doc)]
        indexed = f"{blurb} {child_text}".strip() if blurb else child_text
        out.append(ChildParentPair(
            child=Unit(
                unit_id=f"{condition_id}s2b:{parent_unit.doc_id}:{parent_ix}:{ci}",
                text=indexed,
                doc_id=parent_unit.doc_id,
                source_ranges=ranges,
                meta={
                    "parent_id": parent_unit.unit_id,
                    "child_tokens_ceiling": child_tokens,
                    "condition": condition_id,
                    "child_text_tokens": _n_tokens(child_text),
                    "blurb_tokens": _n_tokens(blurb) if blurb else 0,
                    "provenance_derivable": bool(ranges),
                },
            ),
            parent=parent,
        ))
    return out


def build_children(parent_units: list[Unit], child_tokens: int, condition_id: str,
                   blurbs: dict[str, str] | None = None
                   ) -> tuple[list[Unit], dict[str, ParentContext]]:
    """Split a condition's baseline units into sentence-aligned children.

    Returns `(children, parent_index)`. Only `children` are indexed and ranked; parents are the
    delivered, scored units and their inventory is set-identical to `parent_units` by
    construction (asserted in `src/smalltobig/retrieve.py`).
    """
    children: list[Unit] = []
    parent_index: dict[str, ParentContext] = {}
    for ix, pu in enumerate(parent_units):
        blurb = (blurbs or {}).get(pu.unit_id, "")
        for pair in split_unit(pu, child_tokens, condition_id, ix, blurb=blurb):
            children.append(pair.child)
            parent_index.setdefault(pair.parent.parent_id, pair.parent)
    return children, parent_index


def child_token_distribution(children: list[Unit]) -> dict:
    """v1.5 §3 reporting: `child_tokens` is a ceiling, so report what was realized."""
    vals = sorted(c.meta.get("child_text_tokens", 0) for c in children)
    if not vals:
        return {"n": 0}
    n = len(vals)
    return {
        "n": n,
        "mean": round(sum(vals) / n, 2),
        "median": vals[n // 2],
        "p10": vals[int(n * 0.10)],
        "p90": vals[int(n * 0.90)],
        "max": vals[-1],
    }


def blurb_to_child_ratio(children: list[Unit]) -> float:
    """MEAN OF RATIOS: mean over children of (blurb tokens / child-text tokens).

    This is the statistic the v1.5 run recorded, kept unchanged so the artifacts stay
    readable. It is a **poor** dilution diagnostic and must not be read as one: `1/t` is
    convex, so a handful of very short remainder children dominate it, and it therefore does
    not scale with the child-size ceiling. On Track A it *rises* from 0.5669 to 0.9711 between
    128 and 256 while the actual dilution falls — the share of children under 32 tokens goes
    6.8% -> 17.2% as the same parents are cut into fewer, larger pieces with a longer tail.

    Use `blurb_dilution` instead. See `scripts/check_blurb_ratio.py`.
    """
    pairs = [(c.meta.get("blurb_tokens", 0), c.meta.get("child_text_tokens", 0))
             for c in children]
    pairs = [(b, t) for b, t in pairs if t > 0]
    if not pairs:
        return 0.0
    return round(sum(b / t for b, t in pairs) / len(pairs), 4)


def blurb_dilution(children: list[Unit]) -> dict:
    """v1.5 §3 dilution diagnostic, corrected (handoff 2026-07-29 §4).

    `ratio_of_means` is the quantity the diagnostic was always meant to express — what
    fraction of the indexed text is blurb rather than document — and it scales as a
    length-invariant blurb requires (~x0.5 across a doubling of the ceiling, measured x0.57
    on Track A and x0.55 on Track B). `mean_of_ratios` is retained only because it is what
    the run recorded. `short_child_share` is the quantity that separates them.
    """
    pairs = [(c.meta.get("blurb_tokens", 0), c.meta.get("child_text_tokens", 0))
             for c in children]
    pairs = [(b, t) for b, t in pairs if t > 0]
    if not pairs:
        return {"n": 0, "ratio_of_means": 0.0, "mean_of_ratios": 0.0,
                "mean_blurb_tokens": 0.0, "mean_child_tokens": 0.0, "short_child_share": 0.0}
    n = len(pairs)
    mb = sum(b for b, _ in pairs) / n
    mt = sum(t for _, t in pairs) / n
    return {
        "n": n,
        "ratio_of_means": round(mb / mt, 4),
        "mean_of_ratios": round(sum(b / t for b, t in pairs) / n, 4),
        "mean_blurb_tokens": round(mb, 2),
        "mean_child_tokens": round(mt, 2),
        "short_child_share": round(sum(1 for _, t in pairs if t < 32) / n, 4),
    }
