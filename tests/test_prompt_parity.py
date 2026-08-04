"""Prompt-integrity regression tripwire for the canonical formatter prompts.

History: Gate 3a (byte-equality vs the old inline construction) and Gate 3b (the Track A
cache re-run — 100% cache hits, metrics identical to run-20260724-135411) BOTH passed,
proving the extraction into `prompts.py` is byte-pure. The old inline construction is now
deleted (single source of truth). This test freezes the proven prompt strings as a golden
snapshot so any future edit to `prompts.py` fails loudly — forcing an intentional bump of
PROMPTS_VERSION and a fresh cache gate (a fresh LLM call would otherwise break the
published-results lineage).
"""
from __future__ import annotations

import json
from pathlib import Path

from src.chunkers.prompts import (
    PROMPTS_VERSION, formatter_system_prompt, formatter_user_prompt, number_sentences,
)

_GOLDEN = json.loads(
    (Path(__file__).parent / "golden" / "formatter_prompts.json").read_text(encoding="utf-8"))


def test_prompts_version_matches_golden():
    assert PROMPTS_VERSION == _GOLDEN["PROMPTS_VERSION"] == "eval-run-20260724-135411"


def test_number_sentences_matches_golden():
    g = _GOLDEN["number_sentences"]
    assert number_sentences(g["input"]) == g["output"]


def test_system_prompt_matches_golden():
    # all four (do_ref, do_dedup) branches used by C3 + ablations (§9)
    for do_ref in (True, False):
        for do_dedup in (True, False):
            key = f"{do_ref}_{do_dedup}"
            out = formatter_system_prompt(do_ref, do_dedup)
            assert out == _GOLDEN["system"][key]
            assert out.encode("utf-8") == _GOLDEN["system"][key].encode("utf-8")


def test_user_prompt_matches_golden():
    assert formatter_user_prompt("The Kestrel indexer", "[0] a\n[1] b") == _GOLDEN["user"]
