"""Chunker registry / factory."""
from __future__ import annotations

from src.chunkers.base import ChunkContext, Chunker
from src.chunkers.naive import NaiveChunker
from src.chunkers.semantic import SemanticChunker
from src.chunkers.contextual import ContextualChunker
from src.chunkers.formatter import FormatterChunker
from src.chunkers.formatted import FormattedNaiveChunker, FormattedContextualChunker

_REGISTRY = {
    "naive": NaiveChunker,
    "semantic": SemanticChunker,
    "contextual": ContextualChunker,
    "formatter": FormatterChunker,
    "formatted_naive": FormattedNaiveChunker,        # C4
    "formatted_contextual": FormattedContextualChunker,  # C5
}


def build_chunker(condition_cfg: dict, ctx: ChunkContext | None = None) -> Chunker:
    name = condition_cfg["chunker"]
    if name not in _REGISTRY:
        raise ValueError(f"unknown chunker {name!r}; have {list(_REGISTRY)}")
    chunker = _REGISTRY[name](condition_cfg.get("params", {}), ctx)
    chunker.condition_id = condition_cfg.get("id", chunker.condition_id)
    return chunker
