"""C2 — Contextual retrieval (plan §5.2). Strong baseline.

Naive base chunks, each PREPENDED with a short (1-2 sentence) document-context blurb
(Anthropic-style). The blurb is embedded/indexed with the chunk but has NO source
range — it is excluded from provenance (§6.1). Only the underlying chunk offsets count.

provider != none -> LLM generates the blurb (cached, temp 0).
provider == none -> deterministic rule-based blurb from the document's title/intro,
clearly labeled as a stub.
"""
from __future__ import annotations

from src.chunkers.base import Chunker, ChunkContext, Unit
from src.chunkers.naive import fixed_size_units
from src.datasets.base import Document
from src.textutil import sentence_spans

_SYS = ("You situate a chunk within its document for retrieval. Output ONE or TWO "
        "short sentences of context (who/what the chunk is about, its place in the "
        "document). Do not add facts not present. Output only the context sentences.")


class ContextualChunker(Chunker):
    condition_id = "C2"

    def __init__(self, params: dict, ctx: ChunkContext | None = None) -> None:
        super().__init__(params, ctx)
        self.llm = ctx.llm if ctx else None

    def chunk(self, doc: Document) -> list[Unit]:
        base = fixed_size_units(
            doc,
            chunk_tokens=self.params.get("chunk_tokens", 384),
            overlap_frac=self.params.get("overlap_frac", 0.1),
            condition_id=self.condition_id,
        )
        doc_summary = self._doc_summary(doc)
        out: list[Unit] = []
        for u in base:
            blurb = self._blurb(doc, u.text, doc_summary)
            # blurb prepended to indexed text, but NOT part of source_ranges (§6.1)
            u.text = f"{blurb}\n\n{u.text}"
            u.meta["blurb"] = blurb
            out.append(u)
        return out

    def _doc_summary(self, doc: Document) -> str:
        spans = sentence_spans(doc.text)
        head = " ".join(doc.text[s:e] for s, e in spans[:2])
        return head[:400]

    def _blurb(self, doc: Document, chunk_text: str, doc_summary: str) -> str:
        if self.llm is None or self.llm.is_none:
            # RULE-BASED STUB (provider=none): use the document's opening as context.
            title = doc_summary.split("\n")[0].lstrip("# ").strip()
            first = doc_summary.replace("\n", " ").strip()
            return f"[stub-context] This passage is from the document about {title}. {first}"[:300]
        prompt = (f"<document>\n{doc_summary}\n</document>\n\n"
                  f"<chunk>\n{chunk_text[:1500]}\n</chunk>\n\n"
                  "Give the situating context for this chunk.")
        return self.llm.complete(prompt, system=_SYS).strip()
