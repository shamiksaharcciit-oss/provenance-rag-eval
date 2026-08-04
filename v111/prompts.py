"""v1.11 §3 — the two prompt variants, byte-frozen here.

Both retain the NOT FOUND token because scoring is mechanical; token-free prompts are a
declared limitation, not an oversight. The frozen v1.9 prompt is imported by identity and is
never restated.
"""
from __future__ import annotations

from src.v17.reading import PROMPT_TEMPLATE as FROZEN_V19_PROMPT   # canonical at e19dd35

V1 = ("Answer the question using only the provided context.\n\nContext:\n{package}\n\n"
      "Question: {query}\n\nIf the context does not contain the answer, reply exactly: NOT FOUND.")

V2 = ("Use the context to answer the question.\n\nContext:\n{package}\n\nQuestion: {query}\n\n"
      "Reply NOT FOUND if the answer is not in the context.")

VARIANTS = {"frozen": FROZEN_V19_PROMPT, "v1": V1, "v2": V2}


def render(variant: str, package: str, query: str) -> str:
    """Brace-safe substitution: package text is corpus text and may contain braces."""
    t = VARIANTS[variant]
    return t.replace("{package}", package).replace("{query}", query)
