"""v1.11 §1 — the unanswerable packages, free by provenance.

Two constructions per query per arm:

  cross-doc  the successor query's package (PR-0's mismatch machinery, seed 1337) — off-topic
             and answerless.
  same-doc   built by the frozen v1.9 procedure from the SAME document's units with every
             gold-overlapping unit EXCLUDED — on-topic, plausible, provably answerless. This
             is the hard case: the model sees the right document and must still abstain.

`assert_no_gold_overlap` is the acceptor, executed against every constructed package for both
arms rather than argued: a same-doc package whose units overlap the gold by provenance is not
unanswerable, and `false_answer` would then be measuring the wrong thing entirely.
"""
from __future__ import annotations

from src.chunkers.base import Unit
from src.datasets.base import GoldSpan
from src.score.provenance import covered_chars
from src.v17.packages import PaddingUnsupported, build_package


class PackageIsAnswerable(AssertionError):
    """A supposedly unanswerable package overlaps its query's gold span."""


def gold_bearing_ids(units: list[Unit], gold: list[GoldSpan]) -> set[str]:
    return {u.unit_id for u in units if any(covered_chars(u, g) > 0 for g in gold)}


def same_doc_answerless(units: list[Unit], gold: list[GoldSpan], budget: int):
    """The arm's units for the gold document, gold-bearing ones removed, packed to `budget`.

    Returns None when the document has no non-gold units left to pack — recorded as a
    construction gap rather than approximated with something else's text.
    """
    doc = {g.doc_id for g in gold}
    if len(doc) != 1:
        return None
    doc_id = doc.pop()
    drop = gold_bearing_ids(units, gold)
    keep = [u for u in units if u.doc_id == doc_id and u.unit_id not in drop]
    if not keep:
        return None
    # Pack in document order to the budget; no gold exists to centre on, so this is a plain
    # prefix rather than build_package's gold-centred padding.
    out, total = [], 0
    for u in keep:
        out.append(u)
        total += _tok(u.text)
        if total >= budget:
            break
    return out


def _tok(s: str) -> int:
    from src.textutil import count_tokens
    return count_tokens(s)


def assert_no_gold_overlap(pkg_units: list[Unit], gold: list[GoldSpan], label: str) -> None:
    """THE census acceptor. Executed per package, both arms, both constructions."""
    bad = [u.unit_id for u in pkg_units if any(covered_chars(u, g) > 0 for g in gold)]
    if bad:
        raise PackageIsAnswerable(
            f"{label}: units {bad} overlap the query's gold by provenance, so this package is "
            f"not unanswerable and false_answer would measure the wrong thing")


def false_answer(reply: str) -> int:
    """1 iff the reply is anything other than the frozen abstention token."""
    from src.v17.reading import is_not_found
    return 0 if is_not_found(reply) else 1
