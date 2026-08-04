"""LLM judges: end-to-end faithfulness (§7.6) and readability / H3 (§7.8).

provider != none -> pinned LLM at temp 0 scores a documented 1-5 rubric (cached).
provider == none -> deterministic rule-based stubs, clearly labeled in the `rubric`
field so headline claims are never silently based on a stub.
"""
from __future__ import annotations

import json
import re

from src.chunkers.formatter import protected_tokens

_FAITH_SYS = (
    "You are a strict RAG faithfulness judge. Given a QUESTION, a set of retrieved "
    "CONTEXT passages, and a REFERENCE answer, rate 1-5 whether the context supports "
    "the reference answer (5=fully grounded, 1=contradicted/absent). "
    'Return ONLY JSON: {"score": <1-5>, "grounded": <bool>}.'
)
_READ_SYS = (
    "You rate document readability for retrieval, 1-5 (clarity, faithful intent, no "
    "added or dropped meaning). Higher is better. "
    'Return ONLY JSON: {"score": <1-5>}.'
)


def faithfulness_eval(items: list[dict], llm, n: int, seed: int = 0) -> dict:
    """items: [{query_id, question, answer, contexts: [str,...]}].

    Returns {n, score_mean (0..1 normalized), score_mean_raw (1..5), rubric}.
    """
    subset = items[:n]
    if not subset:
        return {"n": 0, "score_mean": 0.0, "score_mean_raw": 0.0, "rubric": "no items"}
    scores: list[int] = []
    stub = llm is None or llm.is_none
    for it in subset:
        ctx = "\n\n".join(it.get("contexts", []))
        ans = (it.get("answer") or "").strip()
        if stub:
            # RULE-BASED STUB: grounded iff the reference answer appears verbatim in
            # the retrieved context. Deterministic proxy for grounding.
            scores.append(5 if ans and ans in ctx else 1)
        else:
            prompt = (f"QUESTION:\n{it['question']}\n\nCONTEXT:\n{ctx[:6000]}\n\n"
                      f"REFERENCE:\n{ans}\n")
            raw = llm.complete(prompt, system=_FAITH_SYS)
            scores.append(_parse_score(raw))
    raw_mean = sum(scores) / len(scores)
    return {
        "n": len(subset),
        "score_mean": (raw_mean - 1) / 4.0,  # normalize 1..5 -> 0..1
        "score_mean_raw": raw_mean,
        "rubric": ("STUB: answer-in-context grounding (provider=none)"
                   if stub else "LLM 1-5 grounding rubric, temp 0"),
    }


def readability_eval(pairs: list[dict], llm, n_docs: int) -> dict:
    """pairs: [{doc_id, original, formatted}]. H3: C3 as readable or better (§2.3).

    Returns c3_mean, original_mean (1..5), and preserved_term_failures across formatted
    text (a protected token present in the source but missing from the formatted doc).
    """
    subset = pairs[:n_docs]
    if not subset:
        return {"n_docs": 0, "c3_mean": 0.0, "original_mean": 0.0,
                "preserved_term_failures": 0, "rubric": "no docs"}
    stub = llm is None or llm.is_none
    c3_scores, orig_scores, term_failures = [], [], 0
    for p in subset:
        # preserved-term check is ALWAYS real (not a stub): every protected token in the
        # source must survive somewhere in the formatted document.
        src_terms = set(protected_tokens(p["original"]))
        fmt_tokens = set(re.findall(r"[A-Za-z0-9][A-Za-z0-9.\-]*", p["formatted"]))
        missing = [t for t in src_terms if t not in fmt_tokens]
        term_failures += len(missing)

        if stub:
            # STUB: base readability 4.0; C3 gets +0.5 for resolving references (fewer
            # dangling pronouns), minus penalty if any protected term was dropped.
            orig_pron = len(re.findall(r"(?m)^(It|This system|The system)\b", p["original"]))
            fmt_pron = len(re.findall(r"(?m)^(It|This system|The system)\b", p["formatted"]))
            base = 4.0
            c3 = base + (0.5 if fmt_pron < orig_pron else 0.0) - (1.0 if missing else 0.0)
            orig_scores.append(base)
            c3_scores.append(max(1.0, min(5.0, c3)))
        else:
            orig_scores.append(_parse_score(llm.complete(
                f"DOCUMENT:\n{p['original'][:6000]}", system=_READ_SYS)))
            c3_scores.append(_parse_score(llm.complete(
                f"DOCUMENT:\n{p['formatted'][:6000]}", system=_READ_SYS)))
    return {
        "n_docs": len(subset),
        "c3_mean": sum(c3_scores) / len(c3_scores),
        "original_mean": sum(orig_scores) / len(orig_scores),
        "preserved_term_failures": term_failures,
        "rubric": ("STUB: heuristic clarity + real preserved-term check (provider=none)"
                   if stub else "LLM 1-5 readability rubric, temp 0 + preserved-term check"),
    }


def _parse_score(raw: str) -> int:
    try:
        data = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
        return int(max(1, min(5, round(float(data.get("score", 1))))))
    except Exception:
        m = re.search(r"[1-5]", raw)
        return int(m.group(0)) if m else 1
