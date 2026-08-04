"""Track B — public benchmark loader (plan §5.1-B).

Tries candidate document-grounded QA datasets in preference order, mapping their gold
evidence to GoldSpan char offsets in the ORIGINAL document. If none load (no network /
`datasets` missing / schema drift), raises TrackUnavailable so run.py records it in
BLOCKERS.md and proceeds with Track A only (§0 rule 6, §12.3).

QASPER is attempted first: evidence paragraphs are located in the full paper text by
exact substring match to produce char spans.
"""
from __future__ import annotations

from src.datasets.base import Dataset, Document, GoldSpan, Query


class TrackUnavailable(RuntimeError):
    pass


def load(track_cfg: dict, seed: int) -> Dataset:
    params = track_cfg.get("params", track_cfg)
    candidates = params.get("candidates", ["qasper"])
    n_queries = params.get("n_queries", 150)
    max_docs = params.get("max_docs", 0)
    errors = []
    for name in candidates:
        try:
            if name == "qasper":
                return _load_qasper(n_queries, seed, max_docs)
            # Other candidates can be added here; report if attempted but unimplemented.
            errors.append(f"{name}: loader not implemented")
        except TrackUnavailable:
            raise
        except Exception as e:  # pragma: no cover - network/schema dependent
            errors.append(f"{name}: {type(e).__name__}: {str(e)[:160]}")
    raise TrackUnavailable("no public dataset loaded; tried -> " + " | ".join(errors))


def _load_qasper(n_queries: int, seed: int, max_docs: int = 0) -> Dataset:
    try:
        from datasets import load_dataset
    except Exception as e:  # pragma: no cover
        raise TrackUnavailable(f"`datasets` not importable: {e}")

    # QASPER ships a loading script; datasets>=3 dropped script support, datasets 2.x
    # needs trust_remote_code=True. Try both forms so either version works.
    ds = None
    last = None
    for kwargs in ({"trust_remote_code": True}, {}):
        try:
            ds = load_dataset("allenai/qasper", split="validation", **kwargs)
            break
        except Exception as e:  # pragma: no cover
            last = e
    if ds is None:
        raise TrackUnavailable(f"could not download QASPER: {str(last)[:180]}")

    import random
    rng = random.Random(seed)

    documents: list[Document] = []
    queries: list[Query] = []
    seen_docs: dict[str, Document] = {}

    for paper in ds:
        pid = paper.get("id") or paper.get("paper_id") or f"p{len(documents)}"
        # Reconstruct full text from title + abstract + section paragraphs.
        parts: list[str] = []
        title = paper.get("title", "")
        if title:
            parts.append(title)
        abstract = paper.get("abstract", "")
        if abstract:
            parts.append(abstract)
        ft = paper.get("full_text", {}) or {}
        sec_names = ft.get("section_name", []) or []
        paragraphs = ft.get("paragraphs", []) or []
        for name, paras in zip(sec_names, paragraphs):
            if name:
                parts.append(str(name))
            for para in paras:
                if para:
                    parts.append(str(para))
        text = "\n\n".join(parts)
        if not text.strip():
            continue
        doc = seen_docs.get(pid)
        if doc is None:
            doc = Document(doc_id=pid, text=text)
            seen_docs[pid] = doc
            documents.append(doc)

        qas = paper.get("qas", {}) or {}
        q_texts = qas.get("question", []) or []
        answers = qas.get("answers", []) or []
        for qi, qtext in enumerate(q_texts):
            evid_spans = _evidence_spans(doc, answers, qi)
            if not evid_spans:
                continue
            ref = _first_answer_text(answers, qi)
            queries.append(Query(
                query_id=f"{pid}::q{qi}",
                text=str(qtext),
                gold_spans=evid_spans,
                answer=ref,
                qtype="factual",
            ))

    if not queries:
        raise TrackUnavailable("QASPER loaded but no evidence spans could be mapped")

    rng.shuffle(queries)
    # Cap indexed documents to bound cost/memory (v1.1 B.yaml max_docs): keep queries
    # only from the first `max_docs` distinct documents encountered post-shuffle.
    if max_docs and max_docs > 0:
        keep_docs, kept = set(), []
        for q in queries:
            d = q.gold_spans[0].doc_id
            if d in keep_docs or len(keep_docs) < max_docs:
                keep_docs.add(d)
                kept.append(q)
        queries = kept
    queries = queries[:n_queries]
    used_ids = {g.doc_id for q in queries for g in q.gold_spans}
    documents = [d for d in documents if d.doc_id in used_ids]
    meta = {"track": "B", "dataset": "allenai/qasper", "split": "validation",
            "n_docs": len(documents), "n_queries": len(queries)}
    return Dataset(track_id="B", documents=documents, queries=queries, meta=meta)


def _evidence_spans(doc: Document, answers, qi: int) -> list[GoldSpan]:
    spans: list[GoldSpan] = []
    try:
        ans_list = answers[qi]["answer"]
    except Exception:
        return spans
    for a in ans_list:
        for ev in (a.get("evidence", []) or []):
            ev = str(ev).strip()
            if len(ev) < 15:
                continue
            pos = doc.text.find(ev)
            if pos >= 0:
                spans.append(GoldSpan(doc.doc_id, pos, pos + len(ev)))
    # dedup
    uniq = {(s.start_char, s.end_char): s for s in spans}
    return list(uniq.values())


# --------------------------------------------------------------------------
# v1.2 Track B2: fresh held-out queries + identity tagging (§3)
# --------------------------------------------------------------------------
def v11_exclusion_ids(seed: int) -> set[str]:
    """The exact v1.1 B-150 query_ids (seed 1337, max_docs 60, n_queries 150)."""
    ds = load({"params": {"candidates": ["qasper"], "n_queries": 150, "max_docs": 60}}, seed)
    return {q.query_id for q in ds.queries}


def _doc_identity_tokens(doc: Document) -> set[str]:
    """Proper-noun tokens from the document's title + abstract region (its identity)."""
    from src.chunkers.formatter import _proper_tokens
    return _proper_tokens(doc.text[:1500])


def tag_identity(query: Query, doc: Document) -> str:
    """`identity_rich` if the query text shares >=1 proper-noun token with the gold doc's
    title/abstract (it already names the subject), else `identity_poor`. Deterministic,
    no LLM. Threshold = 1 shared title/abstract entity (documented in the prereg §3.2)."""
    from src.chunkers.formatter import _proper_tokens
    shared = _proper_tokens(query.text) & _doc_identity_tokens(doc)
    return "identity_rich" if len(shared) >= 1 else "identity_poor"


def load_b2(seed: int, new_seed: int, n_queries: int = 180) -> Dataset:
    """Draw a fresh B2 sample (no overlap with the v1.1 B-150), corpus = its gold docs,
    each query tagged identity_poor|rich BEFORE any retrieval (§3.1-3.2)."""
    import random
    full = load({"params": {"candidates": ["qasper"], "n_queries": 100000, "max_docs": 0}}, seed)
    excl = v11_exclusion_ids(seed)
    fresh = [q for q in full.queries if q.query_id not in excl]
    rng = random.Random(new_seed)
    rng.shuffle(fresh)
    take = fresh[:n_queries]
    assert not ({q.query_id for q in take} & excl), "B2 overlaps the v1.1 exclusion list"

    used = {q.gold_spans[0].doc_id for q in take}
    documents = [d for d in full.documents if d.doc_id in used]
    doc_by_id = {d.doc_id: d for d in documents}
    tags = {q.query_id: tag_identity(q, doc_by_id[q.gold_spans[0].doc_id]) for q in take}
    n_poor = sum(1 for t in tags.values() if t == "identity_poor")

    meta = {
        "track": "B2", "dataset": "allenai/qasper", "split": "validation",
        "n_docs": len(documents), "n_queries": len(take), "new_seed": new_seed,
        "tags": tags, "doc_ids": sorted(used),
        "exclusion_ids": sorted(excl), "tag_threshold": 1,
        "n_identity_poor": n_poor, "n_identity_rich": len(take) - n_poor,
    }
    return Dataset(track_id="B2", documents=documents, queries=take, meta=meta)


def _first_answer_text(answers, qi: int) -> str | None:
    try:
        for a in answers[qi]["answer"]:
            if a.get("free_form_answer"):
                return str(a["free_form_answer"])
            if a.get("extractive_spans"):
                return "; ".join(a["extractive_spans"])
    except Exception:
        return None
    return None
