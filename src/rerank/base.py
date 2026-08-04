"""Reranker interface + provenance guard (amendment v1.3, M6).

A reranker REORDERS an already-retrieved candidate pool. It must never create, drop,
merge, split, or rewrite a Unit — the evaluation scores hits against ORIGINAL document
character ranges (plan §6), so a reranker that touched `text` or `source_ranges` would
silently invalidate every downstream metric.

That is not left to convention: `assert_permutation` enforces it on every call, and the
pipeline runs it in-band rather than as a test-only check.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from src.chunkers.base import Unit


class ProvenanceViolation(RuntimeError):
    """A reranker altered the candidate set rather than merely reordering it."""


def assert_permutation(before: list[Unit], after: list[Unit]) -> None:
    """Fail loud if `after` is not a pure reordering of `before`.

    Checks identity, multiplicity, text and provenance — a reranker may only permute.
    """
    if len(before) != len(after):
        raise ProvenanceViolation(
            f"reranker changed pool size: {len(before)} -> {len(after)}")

    def key(u: Unit) -> tuple:
        return (u.unit_id, u.doc_id, u.text, tuple(tuple(r) for r in u.source_ranges))

    b = sorted(key(u) for u in before)
    a = sorted(key(u) for u in after)
    if b != a:
        before_ids = {u.unit_id for u in before}
        after_ids = {u.unit_id for u in after}
        added = after_ids - before_ids
        dropped = before_ids - after_ids
        detail = ""
        if added or dropped:
            detail = f" added={sorted(added)[:3]} dropped={sorted(dropped)[:3]}"
        else:
            detail = " same unit_ids, but text or source_ranges were modified"
        raise ProvenanceViolation("reranker did not return a permutation of its input;" + detail)


class Reranker(ABC):
    """Reorders a candidate pool for one query. Pure permutation, no resizing."""

    #: short id recorded into results.json (§11 provenance of the run)
    name: str = "?"

    @abstractmethod
    def _order(self, query: str, units: list[Unit]) -> list[Unit]:
        """Return the units reordered best-first. Implemented by subclasses."""
        raise NotImplementedError

    def rerank(self, query: str, units: list[Unit]) -> list[Unit]:
        if not units:
            return []
        out = self._order(query, units)
        assert_permutation(units, out)
        return out

    def describe(self) -> dict:
        return {"name": self.name}


class NoopReranker(Reranker):
    """Identity reranker — the control. Used by smoke runs and by the parity test that
    confirms reranking-off reproduces the un-reranked ranking exactly."""

    name = "noop"

    def _order(self, query: str, units: list[Unit]) -> list[Unit]:
        return list(units)


def build_reranker(cfg: dict) -> Reranker | None:
    """Construct the configured reranker, or None when the axis is off.

    `rerank.enabled: false` (the default) returns None so every prior result reproduces
    byte-for-byte — the reranker is an ADDED axis, not a change to the existing pipeline.
    """
    rc = cfg.get("rerank", {}) or {}
    if not rc.get("enabled", False):
        return None
    kind = str(rc.get("backend", "cross_encoder")).lower()
    if kind in ("noop", "none"):
        return NoopReranker()
    if kind == "cross_encoder":
        from src.rerank.cross_encoder import CrossEncoderReranker

        return CrossEncoderReranker(
            model=rc.get("model", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
            revision=rc.get("revision", "main"),
            batch_size=int(rc.get("batch_size", 32)),
            device=rc.get("device", "cpu"),
            max_length=int(rc.get("max_length", 512)),
            threads=int(rc.get("threads", 0)),
        )
    raise ValueError(f"unknown rerank.backend: {kind!r}")
