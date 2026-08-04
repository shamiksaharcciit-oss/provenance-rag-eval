"""Sentence-aligned child construction and the C2 blurb rule (v1.5 §3).

One rule across all three conditions: greedily accumulate sentences up to a `child_tokens`
CEILING, hard-cutting any sentence that exceeds it alone. `child_tokens` is a ceiling, not a
size — which is why the realized distribution is a reported quantity rather than an assumption.
"""
from __future__ import annotations

from src.chunkers.base import Unit
from src.smalltobig.chunker import (
    blurb_to_child_ratio,
    build_children,
    child_token_distribution,
)

DOC = "d0"

S1 = "The Kestrel indexer listens on port 50051."          # ~9 tokens
S2 = "It rebuilds a shard in ninety seconds."              # ~8
S3 = "Operators override the port with an env var."        # ~9


def _unit(text: str, uid: str = "C0:d0:0", start: int = 0) -> Unit:
    return Unit(unit_id=uid, text=text, doc_id=DOC, source_ranges=[(start, start + len(text))])


def test_children_respect_sentence_boundaries():
    """With a ceiling comfortably above one sentence, children must break at sentence ends —
    never mid-sentence — so each child is a coherent ranking unit."""
    text = " ".join([S1, S2, S3])
    children, _ = build_children([_unit(text)], child_tokens=12, condition_id="C0")
    assert len(children) >= 2, "should split into several children at this ceiling"
    for c in children:
        t = c.text.strip()
        assert t.endswith("."), f"child does not end at a sentence boundary: {t!r}"


def test_ceiling_is_respected_and_is_a_ceiling_not_a_size():
    text = " ".join([S1, S2, S3])
    children, _ = build_children([_unit(text)], child_tokens=12, condition_id="C0")
    sizes = [c.meta["child_text_tokens"] for c in children]
    assert all(s <= 12 for s in sizes), f"ceiling exceeded: {sizes}"
    assert len(set(sizes)) >= 1
    # A ceiling produces uneven sizes; that is expected and is why it gets reported.
    dist = child_token_distribution(children)
    assert dist["n"] == len(children) and dist["max"] <= 12


def test_two_short_sentences_merge_into_one_child():
    """Greedy accumulation: two sentences that fit together must not become two children."""
    text = " ".join([S1, S2])
    children, _ = build_children([_unit(text)], child_tokens=64, condition_id="C0")
    assert len(children) == 1, "both sentences fit under the ceiling and should merge"
    assert "Kestrel" in children[0].text and "rebuilds" in children[0].text


def test_oversized_sentence_is_hard_cut():
    """A single sentence longer than the ceiling cannot be honoured whole."""
    long_sentence = "alpha " * 60 + "omega."
    children, _ = build_children([_unit(long_sentence)], child_tokens=10, condition_id="C0")
    assert len(children) > 1, "an oversized sentence must be hard-cut"
    assert all(c.meta["child_text_tokens"] <= 10 for c in children)


def test_children_stay_inside_their_parent_span_when_provenance_is_derivable():
    text = " ".join([S1, S2, S3])
    children, parents = build_children([_unit(text, start=500)], child_tokens=12,
                                       condition_id="C0")
    p = parents["C0:d0:0"]
    for c in children:
        assert c.meta["provenance_derivable"] is True
        (cs, ce) = c.source_ranges[0]
        assert p.char_span[0] <= cs < ce <= p.char_span[1]


# --------------------------------------------------------------------------
# C2: blurb + child text, ceiling on the child TEXT
# --------------------------------------------------------------------------

def test_c2_blurb_is_prepended_to_every_child():
    text = " ".join([S1, S2, S3])
    blurb = "This document describes the Kestrel indexer."
    children, _ = build_children([_unit(text, uid="C2:d0:0")], child_tokens=12,
                                 condition_id="C2", blurbs={"C2:d0:0": blurb})
    assert len(children) >= 2
    for c in children:
        assert c.text.startswith(blurb), "contextual retrieval puts context on EVERY unit"
        assert c.meta["blurb_tokens"] > 0


def test_c2_ceiling_applies_to_child_text_not_the_indexed_unit():
    """`child_tokens` bounds the child TEXT; the blurb rides on top.

    This keeps C2's child text directly comparable to C0's. It is safe precisely because
    children only rank — they are never scored or delivered — so the extra blurb tokens carry
    no volume consequence for the metric.
    """
    text = " ".join([S1, S2, S3])
    blurb = "Context sentence about the system under discussion here."
    c2, _ = build_children([_unit(text, uid="C2:d0:0")], child_tokens=12,
                           condition_id="C2", blurbs={"C2:d0:0": blurb})
    c0, _ = build_children([_unit(text, uid="C0:d0:0")], child_tokens=12, condition_id="C0")
    assert [c.meta["child_text_tokens"] for c in c2] == [c.meta["child_text_tokens"] for c in c0], \
        "C2 child TEXT must be cut identically to C0's; only the prepended blurb differs"
    assert all(c.meta["child_text_tokens"] <= 12 for c in c2)


def test_no_child_is_pure_blurb():
    """The v1.4 design produced unhittable pure-blurb children; v1.5's does not."""
    text = " ".join([S1, S2])
    children, _ = build_children([_unit(text, uid="C2:d0:0")], child_tokens=8,
                                 condition_id="C2", blurbs={"C2:d0:0": "Some context."})
    for c in children:
        assert c.meta["child_text_tokens"] > 0, "every child carries real document text"


def test_blurb_to_child_ratio_is_reported():
    text = " ".join([S1, S2, S3])
    children, _ = build_children([_unit(text, uid="C2:d0:0")], child_tokens=12,
                                 condition_id="C2", blurbs={"C2:d0:0": "A short blurb here."})
    ratio = blurb_to_child_ratio(children)
    assert ratio > 0, "ratio is the dilution diagnostic if C2's ranking underperforms"
    assert blurb_to_child_ratio(build_children([_unit(text)], 12, "C0")[0]) == 0.0


# --------------------------------------------------------------------------
# Provenance is populated where derivable, empty where not — never guessed
# --------------------------------------------------------------------------

def test_children_of_edited_units_get_no_provenance_rather_than_a_guess():
    """C4-shaped unit: merged disjoint ranges spanning more text than the unit holds.

    Children must still be produced (they rank fine) but must carry NO source_ranges — the
    alternatives were the parent's ranges (dilution) or interpolation (fabrication).
    """
    edited = Unit(unit_id="C4:d0:0", text=" ".join([S1, S2]), doc_id=DOC,
                  source_ranges=[(0, 40), (900, 980), (2000, 2100)])
    children, _ = build_children([edited], child_tokens=12, condition_id="C4")
    assert children, "children are still produced — ranking does not need provenance"
    for c in children:
        assert c.source_ranges == [], "provenance must be empty, not guessed"
        assert c.meta["provenance_derivable"] is False
