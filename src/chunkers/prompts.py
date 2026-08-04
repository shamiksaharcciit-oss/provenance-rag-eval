"""Canonical semantic-formatter prompts (single source of truth).

These strings are the prompts EXACTLY as they executed in the published evaluation run
`run-20260724-135411`. They are BYTE-PRESERVING extractions from the former inline
construction in `formatter.py::_chunk_llm` — do not reword, reflow, or restructure any
literal, or the LLM cache key changes and the published-results lineage breaks.

The Forge app's `formatter/prompts.ts` is a synced copy of this module and carries the
same PROMPTS_VERSION; a byte-equality test on both sides asserts they cannot drift.
"""
from __future__ import annotations

PROMPTS_VERSION = "eval-run-20260724-135411"
# v1.2: adds ONE operation (document-identity injection). v1.1 prompts stay byte-frozen
# under PROMPTS_VERSION for the baselines; only the treatment (C4i) uses this version.
PROMPTS_VERSION_V12 = "v1.2-identity"

# The single added operation (v1.2 §1). Appended AFTER the v1.1 ops so the v1.1 strings
# stay byte-identical (identity_injection defaults False everywhere the baselines run).
_IDENTITY_OP = ("where a sentence's subject is only implicit, prepend the document's "
                "identity taken VERBATIM from the <subject> hint (the document's title or "
                "leading named entity) to make it explicit — at most once per section, and "
                "never where the subject is already named")


def prompts_version(identity_injection: bool = False) -> str:
    return PROMPTS_VERSION_V12 if identity_injection else PROMPTS_VERSION


def number_sentences(orig_texts: list[str]) -> str:
    """Render the numbered source-sentence block: `[i] <sentence>` per line."""
    return "\n".join(f"[{i}] {t}" for i, t in enumerate(orig_texts))


def formatter_system_prompt(do_ref: bool, do_dedup: bool,
                            identity_injection: bool = False) -> str:
    """The formatter system prompt. `ops` are gated by the active operations (§9).

    identity_injection=False reproduces the v1.1 string BYTE-FOR-BYTE (baselines / cache
    replay); =True appends the single v1.2 identity operation (treatment C4i).
    """
    ops: list[str] = []
    if do_ref:
        ops.append("resolve leading dangling references (pronouns such as 'It', "
                   "'This system') to the document subject, editing ONLY the reference")
    if do_dedup:
        ops.append("identify sentences that are exact restatements of an earlier sentence")
    if identity_injection:
        ops.append(_IDENTITY_OP)
    return (
        "You are a conservative semantic formatter for RAG indexing. "
        f"Tasks: {'; '.join(ops) if ops else 'none'}. "
        "NEVER change domain terms, identifiers, or numbers (keep them verbatim). "
        "Do NOT split, merge, or reorder sentences. Return ONLY JSON of the form "
        '{"resolved":[{"i":<index>,"text":"<edited sentence>"}],"drop":[<indices>]}. '
        "Put a sentence in 'resolved' ONLY if you changed its wording; put an index in "
        "'drop' ONLY if that sentence is an exact restatement of an earlier one."
    )


def formatter_user_prompt(subject, numbered: str) -> str:
    """The formatter user prompt: subject hint + numbered sentences."""
    return f"<subject>{subject}</subject>\n{numbered}"
