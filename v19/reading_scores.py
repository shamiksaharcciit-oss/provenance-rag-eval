"""v1.9 §3 — scoring, by citation of the v1.7 frozen artifacts.

The prompt template and `normalise` are canonical at `e19dd35` in `src/v17/reading.py` and the
plan cites them rather than restating them. This module imports; it defines no scorer of its own,
so there is no second procedure for any quantity (A5b).
"""
from __future__ import annotations

from src.v17.reading import (PROMPT_TEMPLATE, exact_containment, gold_text, is_not_found,
                             normalise, render_prompt, token_f1, tokens)

__all__ = ["render", "PROMPT_TEMPLATE", "normalise", "tokens", "token_f1", "exact_containment",
           "gold_text", "is_not_found", "score_pair"]


def render(package: str, query: str) -> str:
    """The frozen v1.7 prompt, by citation."""
    return render_prompt(package, query)


def score_pair(answer_a: str, answer_b: str, gold: str) -> dict:
    """Objective scores for one paired query. Judge scoring is separate and descriptive."""
    fa, fb = token_f1(answer_a, gold), token_f1(answer_b, gold)
    return {"f1_a": fa, "f1_b": fb, "f1_diff": fa - fb,
            "contain_a": exact_containment(answer_a, gold),
            "contain_b": exact_containment(answer_b, gold),
            "not_found_a": is_not_found(answer_a), "not_found_b": is_not_found(answer_b)}
