"""Unit dataclass + Chunker interface (plan §6.1, §6.2).

Every Unit produced by every chunker MUST carry provenance mapping it back to
original character ranges. A hit is judged against the ORIGINAL document span,
not a chunk id (§6).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict

from src.datasets.base import Document


@dataclass
class Unit:
    unit_id: str
    text: str  # text that gets embedded/indexed
    doc_id: str
    # char ranges in the ORIGINAL doc this unit derives from.
    # For C2, the prepended blurb has NO source range and is excluded here (§6.1).
    source_ranges: list[tuple[int, int]] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        for (s, e) in self.source_ranges:
            if s < 0 or e < s:
                raise ValueError(f"unit {self.unit_id}: invalid source_range ({s},{e})")

    def as_dict(self) -> dict:
        d = asdict(self)
        d["source_ranges"] = [list(r) for r in self.source_ranges]
        return d


class Chunker(ABC):
    """Pluggable chunker. All emit Unit(text, provenance)."""

    #: short id, e.g. "C0"
    condition_id: str = "?"

    def __init__(self, params: dict, ctx: "ChunkContext | None" = None) -> None:
        self.params = params or {}
        self.ctx = ctx

    @abstractmethod
    def chunk(self, doc: Document) -> list[Unit]:
        """Split one document into provenance-bearing Units."""
        raise NotImplementedError

    def chunk_all(self, docs: list[Document]) -> list[Unit]:
        units: list[Unit] = []
        for doc in docs:
            units.extend(self.chunk(doc))
        return units


@dataclass
class ChunkContext:
    """Shared services a chunker may need (embedder for C1, llm for C2/C3)."""
    embedder: object | None = None   # src.index.embed.Embedder
    llm: object | None = None        # src.llm.client.LLMClient
    config: dict = field(default_factory=dict)
