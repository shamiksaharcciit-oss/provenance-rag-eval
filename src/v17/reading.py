"""v1.7 E2 — the frozen prompt, the frozen normalisation, and the objective scorers (plan §3.2, §3.3).

Everything in this module is committed at Gate 0 and is part of the freeze. The prompt template
and `normalise` in particular: a normalisation settled after seeing answers is a free parameter
wearing the costume of a preprocessing step, which is what freezing it before any generation
prevents.

PROMPT_TEMPLATE — ONE DECLARED READING. Plan §3.2 prints the template inside a fenced block in a
document wrapped at 96 columns, so its first sentence carries a line break after "the". That
break is an artifact of the document's formatting, not a design choice: no one selects a newline
mid-sentence. The template is therefore stored UNWRAPPED, with the instruction as one logical
line. Everything else — the blank lines, the `Context:` and `Question:` labels, the exact string
`NOT FOUND` — is reproduced character for character. This is the one place where "frozen
verbatim" required interpreting the document rather than copying it, and it is flagged rather
than resolved silently.

The scorers are deterministic and model-free, so they are fully testable at Gate 0 with no spend.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

PROMPT_TEMPLATE = (
    "Answer the question using only the provided context. Quote the answer as exactly as the "
    "context allows. If the context does not contain the answer, reply exactly: NOT FOUND.\n"
    "\n"
    "Context:\n"
    "{package}\n"
    "\n"
    "Question: {query}\n"
)

NOT_FOUND = "NOT FOUND"

_WS = re.compile(r"\s+")


def render_prompt(package: str, query: str) -> str:
    """The only way a prompt is built. `str.format` is not used: package text may contain braces."""
    return PROMPT_TEMPLATE.replace("{package}", package).replace("{query}", query)


def normalise(text: str) -> str:
    """Lowercase; strip punctuation; collapse whitespace (plan §3.3).

    "Strip punctuation" is implemented as *remove every Unicode punctuation and symbol
    character*, by category rather than by an ASCII list, so a curly quote and a straight quote
    normalise alike. Removal replaces the character with a space rather than deleting it, so
    "state-of-the-art" becomes four tokens under both spellings instead of welding into one word
    in one arm and not the other — the formatter edits punctuation, so a normalisation that let
    punctuation change the token count would put the treatment inside the scorer.
    """
    out = []
    for ch in unicodedata.normalize("NFKC", text).lower():
        out.append(" " if unicodedata.category(ch)[0] in ("P", "S") else ch)
    return _WS.sub(" ", "".join(out)).strip()


def tokens(text: str) -> list[str]:
    return normalise(text).split()


def token_f1(answer: str, gold: str) -> float:
    """SQuAD-style token F1 between a generated answer and the gold text.

    Multiset overlap, so a term repeated in the gold must be repeated in the answer to earn its
    second point. Both empty scores 1.0; exactly one empty scores 0.0.
    """
    a, g = tokens(answer), tokens(gold)
    if not a and not g:
        return 1.0
    if not a or not g:
        return 0.0
    common = sum((Counter(a) & Counter(g)).values())
    if common == 0:
        return 0.0
    precision, recall = common / len(a), common / len(g)
    return 2 * precision * recall / (precision + recall)


def exact_containment(answer: str, gold: str) -> int:
    """1 iff the normalised gold text is a substring of the normalised answer (§3.3, secondary)."""
    g = normalise(gold)
    return 1 if g and g in normalise(answer) else 0


def gold_text(document_text: str, spans) -> str:
    """Gold span text concatenated in document order (§3.3, multi-span rule)."""
    return " ".join(document_text[s.start_char : s.end_char]
                    for s in sorted(spans, key=lambda s: s.start_char))


def is_not_found(answer: str) -> bool:
    """Did the generator use the declared abstention string?"""
    return answer.strip() == NOT_FOUND
