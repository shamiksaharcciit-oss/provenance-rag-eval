"""C3 — Semantic formatter (treatment) (plan §6, §9).

A conservative, meaning-preserving editorial pass applied BEFORE indexing:
  (a) reference-resolution  — resolve dangling references (leading pronouns) to the
      document subject, curing context-starvation;
  (b) de-duplication        — drop restated copies of a fact;
  (c) right-sizing          — group to one idea against a soft token budget, placing
      machine-readable boundaries;
governed by ONE rule: edit structure and references, NEVER vocabulary. A verbatim
guardrail + diff gate reject any edit that drops/alters a protected token (identifier,
number, domain term). Each output Unit carries faithful provenance back to the original
character ranges it derived from (§6.3).

Boundary/edit flags (from the condition yaml) select the full pass or an ablation (§9):
  right_size|markers_only -> formatter boundary placement; else original paragraphs
  reference_resolution, dedup -> text edits (off for markers-only)

provider != none -> an LLM performs the pass (cached, temp 0), still gated by the diff
check. provider == none -> the deterministic rule-based pass below (labeled as a stub).
"""
from __future__ import annotations

import re

from src.chunkers.base import Chunker, ChunkContext, Unit
from src.chunkers.prompts import (
    PROMPTS_VERSION, formatter_system_prompt, formatter_user_prompt, number_sentences,
)
from src.datasets.base import Document
from src.textutil import count_tokens, merge_ranges, sentence_spans

__all__ = ["FormatterChunker", "PROMPTS_VERSION"]

# Leading dangling references we resolve to the document subject.
_PRONOUN_LEAD = re.compile(
    r"^(It|They|This system|The system|This component|This service|This)\b")

# A token is PROTECTED (must survive verbatim) if it carries a digit, is an all-caps
# acronym, is hyphenated alphanumeric, or is internally-capitalized (CamelCase).
_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-]*")


# Structural cross-reference placeholders (e.g. QASPER's FIGREF6/BIBREF9/TABREF3/SECREF2/
# EQREF1) are REFERENCES, not vocabulary — the formatter is licensed to edit references, so
# they must NOT count as preserved-term (vocabulary) failures.
_REF_PLACEHOLDER = re.compile(r"^(FIG|TAB|BIB|SEC|EQ|FLOAT|APP)REF\d*$", re.IGNORECASE)


def _is_protected(tok: str) -> bool:
    if _REF_PLACEHOLDER.match(tok):
        return False  # structural reference, not a vocabulary term
    if any(c.isdigit() for c in tok):
        return True
    if len(tok) >= 2 and tok.isupper():
        return True
    if "-" in tok and any(c.isalnum() for c in tok):
        return True
    if re.search(r"[a-z][A-Z]", tok) or re.search(r"[A-Z].*[A-Z]", tok):
        return True
    return False


def protected_tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text) if _is_protected(t)]


def diff_gate_ok(original: str, edited: str) -> bool:
    """Every protected token in the original must still be present in the edited text."""
    orig = protected_tokens(original)
    edited_toks = set(_TOKEN_RE.findall(edited))
    return all(t in edited_toks for t in orig)


# --- v1.2 document-identity injection helpers (identity-source guardrail, §1) ----------
_PROPER_RE = re.compile(r"\b[A-Z][A-Za-z0-9]+\b")
_COMMON_CAP = {"The", "This", "That", "These", "Those", "It", "A", "An", "In", "On", "For",
               "And", "Or", "Of", "To", "With", "By", "As", "At", "We", "Our", "Their",
               "Its", "There", "When", "Where", "Which", "However", "Thus", "Here", "They",
               "He", "She", "If", "Then", "But", "So", "Also", "Both", "Each", "Section",
               "Table", "Figure"}


def _proper_tokens(text: str) -> set[str]:
    """Proper-noun-like capitalized tokens (candidate identity tokens)."""
    return {t for t in _PROPER_RE.findall(text) if t not in _COMMON_CAP and len(t) >= 2}


def identity_source_tokens(doc_text: str, spans: list[tuple[int, int]], subject) -> set[str]:
    """Allowed identity tokens: the subject phrase + the document's title/first paragraph
    (the only places an injected identity may be drawn from, verbatim — §1)."""
    src: set[str] = set()
    if subject:
        src |= _proper_tokens(str(subject))
    for s, e in spans[:6]:  # title + heading + first-paragraph region
        src |= _proper_tokens(doc_text[s:e])
    return src


def _subject_phrase(text: str, spans: list[tuple[int, int]]) -> str | None:
    """Heuristic document subject from the first non-title sentence."""
    for s, e in spans:
        seg = text[s:e].lstrip("# ").strip()
        if not seg:
            continue
        m = re.match(r"(The\s+)?([A-Z][A-Za-z0-9]+(?:\s+[a-z]+){0,3})", seg)
        if m:
            phrase = m.group(0).strip()
            if not phrase.lower().startswith("the "):
                phrase = "The " + phrase
            return phrase
    return None


def _normalize_for_dedup(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"^(to recap,|in summary,|note that|again,)\s*", "", s)
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _parse_formatter_json(raw: str) -> dict:
    """Parse one-or-more concatenated top-level JSON objects and merge them.

    Sonnet-5 (thinking off) sometimes emits the formatter output as two separate
    objects -- {"resolved": [...]} then {"drop": [...]} -- instead of one combined
    object, and may wrap them in a ```json fence. A naive
    raw[index('{'):rindex('}')+1] slice then trips json.loads with 'Extra data'.
    Decode sequentially with raw_decode and merge: list keys concatenate, dict keys
    update, scalars take the last value. Fence text is skipped by seeking '{'.
    Raises (fail loud) if nothing parses -- never silently drops formatter output.
    """
    import json
    dec = json.JSONDecoder()
    merged: dict = {}
    i, n = 0, len(raw)
    while i < n:
        j = raw.find("{", i)
        if j < 0:
            break
        obj, end = dec.raw_decode(raw, j)  # may raise -> propagates (fail loud)
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, list) and isinstance(merged.get(k), list):
                    merged[k].extend(v)
                elif isinstance(v, dict) and isinstance(merged.get(k), dict):
                    merged[k].update(v)
                else:
                    merged[k] = v
        i = end
    if not merged:
        raise ValueError("no JSON object parsed from formatter output")
    return merged


class _Sentence:
    __slots__ = ("start", "end", "orig", "text", "kept", "absorbed")

    def __init__(self, start: int, end: int, orig: str) -> None:
        self.start, self.end, self.orig, self.text, self.kept = start, end, orig, orig, True
        # original-doc ranges of duplicate sentences this one absorbed (v1.1 §5.1):
        # the surviving unit must score a hit for gold anchored to a removed restatement.
        self.absorbed: list[tuple[int, int]] = []


class FormatterChunker(Chunker):
    condition_id = "C3"

    def __init__(self, params: dict, ctx: ChunkContext | None = None) -> None:
        super().__init__(params, ctx)
        self.llm = ctx.llm if ctx else None
        # v1.2 identity-injection accounting (populated only when identity_injection=True).
        self.identity_stats = {"stamps_total": 0, "stamps_per_doc": [], "source_violations": 0}
        # Per-doc formatter-failure accounting. A failure is COUNTED and REPORTED
        # (never silent) — this is the correction to the original bug, where a silent
        # fallback masked a SYSTEMIC failure (every doc fell back, stamps_total=0).
        # A high fallback rate is a hard validity failure, caught by the guard in
        # run_v12; a handful of malformed-JSON docs is a transparent, bounded deviation.
        self.fmt_llm_docs = 0
        self.fmt_fallback_ids: list[str] = []

    def chunk(self, doc: Document) -> list[Unit]:
        p = self.params
        if self.llm is not None and not self.llm.is_none and not p.get("markers_only"):
            self.fmt_llm_docs += 1
            try:
                return self._chunk_llm(doc)
            except Exception as e:
                # Per-doc formatter failure (malformed JSON from the model, or a
                # truncated/empty completion). NOT silent: recorded here and surfaced
                # per-condition; a high rate flips the run to INVALID in run_v12's
                # validity guard. Fall back to the deterministic pass for THIS doc only.
                self.fmt_fallback_ids.append(f"{getattr(doc, 'doc_id', '?')}:{type(e).__name__}")
        return self._chunk_rulebased(doc)

    # -- deterministic rule-based pass (provider=none) ----------------------
    def _chunk_rulebased(self, doc: Document) -> list[Unit]:
        spans = sentence_spans(doc.text)
        if not spans:
            return []
        sents = [_Sentence(s, e, doc.text[s:e]) for s, e in spans]
        subject = _subject_phrase(doc.text, spans)

        do_ref = self.params.get("reference_resolution", True) and not self.params.get("markers_only")
        do_dedup = self.params.get("dedup", True) and not self.params.get("markers_only")
        do_guard = self.params.get("verbatim_guardrail", True)
        do_gate = self.params.get("diff_gate", True)

        # (a) reference resolution: resolve leading dangling pronoun to subject.
        if do_ref and subject:
            for st in sents:
                # skip title lines
                if st.orig.startswith("#"):
                    continue
                m = _PRONOUN_LEAD.match(st.orig)
                if m:
                    edited = subject + st.orig[m.end():]
                    if not (do_guard and do_gate) or diff_gate_ok(st.orig, edited):
                        st.text = edited

        # (b) de-duplication: drop restated copies (keep first occurrence). The kept
        # canonical sentence ABSORBS the dropped copy's original range so provenance is
        # preserved (v1.1 §5.1).
        if do_dedup:
            canonical: dict[str, _Sentence] = {}
            for st in sents:
                norm = _normalize_for_dedup(st.orig)
                if not norm:
                    continue
                if norm in canonical:
                    canonical[norm].absorbed.append((st.start, st.end))
                    st.kept = False
                else:
                    canonical[norm] = st

        kept = [st for st in sents if st.kept]
        if not kept:
            kept = sents

        return self._emit(doc, self._place_boundaries(doc, kept))

    def _place_boundaries(self, doc: Document, kept: list[_Sentence]) -> list[list[_Sentence]]:
        if self.params.get("right_size", True) or self.params.get("markers_only"):
            groups = self._right_size(kept)
        else:  # C3-nosize: keep original paragraph grouping
            groups = self._paragraph_groups(doc.text, kept)
        # v1.1 §8c: enforce a minimum unit size so an ablation measures sizing skill,
        # not degeneracy (Track A nosize produced 5,143 ~10-token micro-units).
        min_tok = self.params.get("min_unit_tokens", 0)
        if min_tok > 0:
            groups = self._merge_small_groups(groups, min_tok)
        return groups

    @staticmethod
    def _merge_small_groups(groups: list[list["_Sentence"]], min_tok: int) -> list[list["_Sentence"]]:
        """Merge any group under `min_tok` tokens into its previous (else next) group."""
        merged: list[list[_Sentence]] = []
        for g in groups:
            if merged and sum(count_tokens(s.text) for s in merged[-1]) < min_tok:
                merged[-1].extend(g)
            else:
                merged.append(list(g))
        # a trailing small group folds back into its predecessor
        if len(merged) >= 2 and sum(count_tokens(s.text) for s in merged[-1]) < min_tok:
            merged[-2].extend(merged.pop())
        return merged

    def _right_size(self, kept: list[_Sentence]) -> list[list[_Sentence]]:
        soft = self.params.get("soft_target_tokens", 384)
        groups: list[list[_Sentence]] = []
        cur: list[_Sentence] = []
        cur_tok = 0
        for st in kept:
            t = count_tokens(st.text)
            if cur and cur_tok + t > soft:
                groups.append(cur)
                cur, cur_tok = [], 0
            cur.append(st)
            cur_tok += t
        if cur:
            groups.append(cur)
        return groups

    def _paragraph_groups(self, text: str, kept: list[_Sentence]) -> list[list[_Sentence]]:
        # group consecutive kept sentences separated by <2 newlines into a paragraph
        groups: list[list[_Sentence]] = []
        cur: list[_Sentence] = []
        prev_end = None
        for st in kept:
            if prev_end is not None:
                gap = text[prev_end:st.start]
                if gap.count("\n") >= 2 and cur:
                    groups.append(cur)
                    cur = []
            cur.append(st)
            prev_end = st.end
        if cur:
            groups.append(cur)
        return groups

    def _emit(self, doc: Document, groups: list[list[_Sentence]]) -> list[Unit]:
        units: list[Unit] = []
        for gi, g in enumerate(groups):
            text = " ".join(st.text for st in g)
            raw = [(st.start, st.end) for st in g]
            for st in g:  # include absorbed duplicate ranges (v1.1 §5.1)
                raw.extend(st.absorbed)
            ranges = merge_ranges(raw)
            units.append(Unit(
                unit_id=f"{self.condition_id}:{doc.doc_id}:{gi}",
                text=text,
                doc_id=doc.doc_id,
                source_ranges=ranges,
                meta={"edited": any(st.text != st.orig for st in g)},
            ))
        return units

    # -- LLM pass (provider=anthropic) -------------------------------------
    def _chunk_llm(self, doc: Document) -> list[Unit]:
        """LLM proposes the LINGUISTIC edits (reference resolution + which sentences are
        exact restatements); the harness applies the diff gate and does the SAME
        deterministic right-sizing as the rule-based path. This keeps provenance exact
        (edits map to their source sentence), unit counts sane, and ablation flags
        authoritative (§6.3, §9) — the LLM never controls grouping.
        """
        import json

        spans = sentence_spans(doc.text)
        if not spans:
            return []
        sents = [_Sentence(s, e, doc.text[s:e]) for s, e in spans]
        subject = _subject_phrase(doc.text, spans)

        do_ref = self.params.get("reference_resolution", True)
        do_dedup = self.params.get("dedup", True)
        do_guard = self.params.get("verbatim_guardrail", True)
        do_gate = self.params.get("diff_gate", True)
        do_identity = self.params.get("identity_injection", False)  # v1.2 treatment op

        # Prompts come from the canonical single source (prompts.py). identity_injection
        # False reproduces the v1.1 strings byte-for-byte (baselines / cache replay).
        numbered = number_sentences([st.orig for st in sents])
        sys = formatter_system_prompt(do_ref, do_dedup, do_identity)
        prompt = formatter_user_prompt(subject, numbered)
        raw = self.llm.complete(prompt, system=sys)
        data = _parse_formatter_json(raw)

        src_ident = identity_source_tokens(doc.text, spans, subject) if do_identity else set()
        doc_stamps = 0
        if (do_ref or do_identity) and subject:
            for r in data.get("resolved", []):
                i = r.get("i")
                if not (isinstance(i, int) and 0 <= i < len(sents)) or sents[i].orig.startswith("#"):
                    continue
                edited = r.get("text", sents[i].orig)
                if (do_guard and do_gate) and not diff_gate_ok(sents[i].orig, edited):
                    continue  # verbatim-vocabulary guardrail blocked this edit
                if do_identity:
                    # identity-source guardrail: any proper token the edit ADDS must be drawn
                    # verbatim from the document's title/headings/first paragraph (§1).
                    added = _proper_tokens(edited) - _proper_tokens(sents[i].orig)
                    if added and not (added <= src_ident):
                        self.identity_stats["source_violations"] += 1
                        continue  # hallucinated identity -> blocked, not applied
                    if added:
                        self.identity_stats["stamps_total"] += 1
                        doc_stamps += 1
                sents[i].text = edited
        if do_identity:
            self.identity_stats["stamps_per_doc"].append(doc_stamps)
        if do_dedup:
            # attach each dropped duplicate's range to its canonical (earliest same-text)
            by_norm: dict[str, _Sentence] = {}
            for st in sents:
                by_norm.setdefault(_normalize_for_dedup(st.orig), st)
            for i in data.get("drop", []):
                if isinstance(i, int) and 0 <= i < len(sents):
                    canon = by_norm.get(_normalize_for_dedup(sents[i].orig))
                    if canon is not None and canon is not sents[i]:
                        canon.absorbed.append((sents[i].start, sents[i].end))
                    sents[i].kept = False

        kept = [st for st in sents if st.kept] or sents
        # SAME deterministic boundary placement as the rule-based path (harness-controlled).
        units = self._emit(doc, self._place_boundaries(doc, kept))
        for u in units:
            u.meta["via"] = "llm"
        return units
