"""v1.10 §1 — the `P` arm's neutral padding, specified and frozen here.

`P` prepends, to each base chunk, filler of **exactly the token length of that chunk's real
blurb**. If `P` and `C` differ in package length the comparison is not matched, so the length
match is an assertion, not an intention.

Filler is drawn from a fixed pool committed as `v110/filler_pool.txt` and bound by content hash,
assigned per chunk by seed 1337, and truncated on a token boundary to the target length.

DECLARED LIMITATION, frozen with the plan: **no filler is perfectly inert for a dense encoder.**
`P`'s reading rests on *lexical* neutrality, which `vocabulary_overlap` checks against both
corpora and both query sets, and NOT on embedding neutrality, which cannot be established. A
reader must take `D_pad = P − U` as "added length of lexically-foreign text", not as "added
length of nothing".
"""
from __future__ import annotations

import hashlib
import random
import re
from pathlib import Path

from src.textutil import _TOKEN_RE, count_tokens

POOL_PATH = Path(__file__).resolve().parent / "filler_pool.txt"
SEED = 1337

#: Function words are excluded from the overlap check: they are unavoidable in any English
#: sentence and carry no domain signal. Overlap that matters is CONTENT-word overlap.
_STOP = frozenset("""
a about above after again against all am an and any are as at be because been before being
below between both but by can cannot could did do does doing down during each few for from
further had has have having he her here hers herself him himself his how i if in into is it
its itself just me more most my myself no nor not now of off on once only or other our ours
ourselves out over own same she should so some such than that the their theirs them themselves
then there these they this those through to too under until up very was we were what when
where which while who whom why will with you your yours yourself yourselves
""".split())

_WORD = re.compile(r"[a-z][a-z'-]*")


def pool_text() -> str:
    return POOL_PATH.read_text(encoding="utf-8")


def pool_hash() -> str:
    return hashlib.sha256(POOL_PATH.read_bytes()).hexdigest()


def pool_sentences() -> list[str]:
    return [ln.strip() for ln in pool_text().splitlines() if ln.strip()]


def content_words(text: str) -> set[str]:
    """Lowercased alphabetic words of length >= 3 that are not function words."""
    return {w for w in _WORD.findall(text.lower()) if len(w) >= 3 and w not in _STOP}


def truncate_to_tokens(text: str, n: int) -> str:
    """Cut `text` to exactly `n` tokens on a token boundary, using `count_tokens`' own regex."""
    if n <= 0:
        return ""
    spans = [(m.start(), m.end()) for m in _TOKEN_RE.finditer(text)]
    if n >= len(spans):
        return text
    return text[: spans[n - 1][1]]


def filler_for(unit_id: str, target_tokens: int, seed: int = SEED) -> str:
    """Deterministic filler of exactly `target_tokens` tokens for `unit_id`.

    Keyed on the unit id rather than on position, so the assignment does not shift if the
    inventory is rebuilt in a different order. Sentences are drawn repeatedly and concatenated
    until the target is reached, then truncated.
    """
    if target_tokens <= 0:
        return ""
    sents = pool_sentences()
    rng = random.Random(f"{seed}:{unit_id}")
    parts: list[str] = []
    total = 0
    while total < target_tokens:
        s = sents[rng.randrange(len(sents))]
        parts.append(s)
        total += count_tokens(s)
    out = truncate_to_tokens(" ".join(parts), target_tokens)
    assert count_tokens(out) == target_tokens, (
        f"filler for {unit_id} is {count_tokens(out)} tokens, expected {target_tokens}")
    return out


def vocabulary_overlap(corpus_texts: list[str], query_texts: list[str]) -> dict:
    """Executed check (§1): does the pool share content words with corpus or queries?

    Returns the overlap sets rather than a verdict. Gate 0 reports the real numbers; whether a
    non-empty overlap is acceptable is a ruling, not something this function decides.
    """
    pool = content_words(pool_text())
    corpus = set()
    for t in corpus_texts:
        corpus |= content_words(t)
    queries = set()
    for t in query_texts:
        queries |= content_words(t)
    return {"pool_content_words": len(pool),
            "corpus_content_words": len(corpus),
            "query_content_words": len(queries),
            "overlap_with_corpus": sorted(pool & corpus),
            "overlap_with_queries": sorted(pool & queries),
            "n_overlap_corpus": len(pool & corpus),
            "n_overlap_queries": len(pool & queries),
            "pool_sha256": pool_hash()}


class PoolNotAtFixedPoint(AssertionError):
    """The pool still shares a content word with some query. Edit and re-run the FULL check."""


def assert_pool_fixed_point(corpus_texts: list[str], query_texts: list[str]) -> dict:
    """Census to fixed point (plan section 1, PF-G1).

    A complete pass must be clean: zero query-vocabulary overlap. Corpus overlap is returned
    for reporting and is NOT a failure condition -- it cannot be driven to zero and the plan no
    longer asks it to be. The procedure exists because the first Gate 0 fix introduced a second
    overlap that only a full re-run caught; one clean pass over the whole check is the only
    evidence that editing has converged.
    """
    r = vocabulary_overlap(corpus_texts, query_texts)
    if r["n_overlap_queries"]:
        raise PoolNotAtFixedPoint(
            f"pool shares {r['n_overlap_queries']} content word(s) with the query sets: "
            f"{r['overlap_with_queries']}. Edit the pool and re-run the FULL check; a partial "
            f"re-check is what let 'another' through at Gate 0.")
    return r
