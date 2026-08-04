"""Track C — real internal corpus loader (plan §5.1-C, optional).

Consumes a directory of exported documents (Markdown/HTML/PDF->text) plus a
queries.jsonl with human-verified gold_spans. If data is absent, raises
TrackUnavailable so run.py skips cleanly and notes it (§12.4).

NEVER auto-accept LLM-generated gold. `scripts/build_gold.py` drafts candidates for
HUMAN verification only.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.datasets.base import Dataset, Document, GoldSpan, Query
from src.datasets.track_b_public import TrackUnavailable


def _read_text_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".md", ".txt", ".html", ".htm"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if suffix in (".html", ".htm"):
            import re
            text = re.sub(r"<[^>]+>", " ", text)
        return text
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except Exception:
            return ""
        try:
            reader = PdfReader(str(path))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""
    return ""


def load(track_cfg: dict, seed: int) -> Dataset:
    params = track_cfg.get("params", track_cfg)
    root = Path(params.get("data_dir", "data/internal"))
    qfile = Path(params.get("queries_file", str(root / "queries.jsonl")))

    if not root.exists():
        raise TrackUnavailable(f"internal data dir not found: {root}")
    if not qfile.exists():
        raise TrackUnavailable(f"human-verified queries file not found: {qfile}")

    documents: list[Document] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in (".md", ".txt", ".html", ".htm", ".pdf"):
            if path.samefile(qfile) if qfile.exists() else False:
                continue
            text = _read_text_file(path)
            if text.strip():
                documents.append(Document(doc_id=str(path.relative_to(root)), text=text))
    if not documents:
        raise TrackUnavailable(f"no readable documents under {root}")

    queries: list[Query] = []
    with open(qfile, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            gold = [GoldSpan(g["doc_id"], int(g["start_char"]), int(g["end_char"]))
                    for g in rec["gold_spans"]]
            queries.append(Query(
                query_id=rec["query_id"], text=rec["text"], gold_spans=gold,
                answer=rec.get("answer"), qtype=rec.get("qtype", "factual")))
    if not queries:
        raise TrackUnavailable(f"{qfile} contained no queries")

    meta = {"track": "C", "n_docs": len(documents), "source": str(root)}
    return Dataset(track_id="C", documents=documents, queries=queries, meta=meta)
