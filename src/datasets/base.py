"""Canonical dataset schema (plan §5.1).

Gold is anchored to CHARACTER SPANS in the original document, never to a chunk.
This is what makes conditions with different chunk boundaries comparable (§6).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass(frozen=True)
class Document:
    doc_id: str
    text: str  # the ORIGINAL, unmodified source text


@dataclass(frozen=True)
class GoldSpan:
    doc_id: str
    start_char: int  # offsets into Document.text
    end_char: int

    def __post_init__(self) -> None:
        if self.start_char < 0 or self.end_char < self.start_char:
            raise ValueError(
                f"invalid GoldSpan ({self.doc_id}, {self.start_char}, {self.end_char})"
            )

    def as_dict(self) -> dict:
        return {"doc_id": self.doc_id, "start_char": self.start_char, "end_char": self.end_char}


QTYPES = ("factual", "multi_hop", "synthesis")


@dataclass
class Query:
    query_id: str
    text: str
    gold_spans: list[GoldSpan]  # >=1 answer-bearing span(s) in original docs
    answer: Optional[str] = None  # reference answer, for end-to-end faithfulness
    qtype: str = "factual"  # "factual" | "multi_hop" | "synthesis"

    def __post_init__(self) -> None:
        if self.qtype not in QTYPES:
            raise ValueError(f"unknown qtype {self.qtype!r}; expected one of {QTYPES}")
        if not self.gold_spans:
            raise ValueError(f"query {self.query_id} has no gold_spans")

    def as_dict(self) -> dict:
        d = asdict(self)
        d["gold_spans"] = [g.as_dict() for g in self.gold_spans]
        return d


@dataclass
class Dataset:
    """A loaded track: original documents + queries with gold spans."""
    track_id: str
    documents: list[Document] = field(default_factory=list)
    queries: list[Query] = field(default_factory=list)
    meta: dict = field(default_factory=dict)  # e.g. which public dataset was used

    def doc_by_id(self) -> dict[str, Document]:
        return {d.doc_id: d for d in self.documents}
