"""v1.2 identity-injection: prompt versioning, identity-source guardrail, stamp tracking,
and the deterministic identity tagger (§1, §3.2, §8.2)."""
from __future__ import annotations

from src.chunkers.prompts import (
    PROMPTS_VERSION, PROMPTS_VERSION_V12, prompts_version, formatter_system_prompt,
)
from src.chunkers.formatter import (
    FormatterChunker, ChunkContext, _proper_tokens, identity_source_tokens,
)
from src.chunkers.base import ChunkContext as _CC  # noqa: F401
from src.datasets.base import Document
from src.textutil import sentence_spans


class _StubLLM:
    """Provider stub returning a fixed formatter response (resolved/drop)."""
    provider = "anthropic"
    is_none = False

    def __init__(self, raw: str):
        self.raw = raw

    def complete(self, prompt: str, system: str = "") -> str:
        return self.raw


# ---- prompt versioning ----------------------------------------------------
def test_v11_prompt_byte_frozen_when_identity_off():
    a = formatter_system_prompt(True, True)
    b = formatter_system_prompt(True, True, identity_injection=False)
    assert a == b  # default False reproduces v1.1 exactly


def test_v12_prompt_adds_identity_op_and_versions():
    base = formatter_system_prompt(True, True)
    v12 = formatter_system_prompt(True, True, identity_injection=True)
    assert v12 != base and "identity" in v12.lower()
    assert base in v12 or v12.startswith(base[:40])  # same shell, extra op
    assert prompts_version(False) == PROMPTS_VERSION
    assert prompts_version(True) == PROMPTS_VERSION_V12 == "v1.2-identity"


# ---- identity-source guardrail --------------------------------------------
_DOC = Document("d1", (
    "# Marlin planner\n\n"
    "The Marlin planner is a distributed scheduler used in production.\n\n"
    "The retry policy is 3 attempts.\n\n"
    "Latency budgets are enforced per stage."
))


def _ctx(raw):
    return ChunkContext(embedder=None, llm=_StubLLM(raw), config={})


def test_identity_stamp_from_source_is_applied_and_counted():
    # LLM stamps the real document identity ("Marlin planner") — allowed.
    raw = '{"resolved":[{"i":2,"text":"The Marlin planner\'s retry policy is 3 attempts."}],"drop":[]}'
    ch = FormatterChunker({"reference_resolution": True, "dedup": True, "right_size": True,
                           "soft_target_tokens": 512, "identity_injection": True}, _ctx(raw))
    units = ch.chunk(_DOC)
    joined = " ".join(u.text for u in units)
    assert "Marlin planner's retry policy is 3 attempts" in joined
    assert ch.identity_stats["stamps_total"] == 1
    assert ch.identity_stats["source_violations"] == 0


def test_hallucinated_identity_is_blocked_and_counted():
    # LLM invents an identity ("Falcon router") NOT in the document -> blocked, reverted.
    raw = '{"resolved":[{"i":2,"text":"The Falcon router\'s retry policy is 3 attempts."}],"drop":[]}'
    ch = FormatterChunker({"reference_resolution": True, "dedup": True, "right_size": True,
                           "soft_target_tokens": 512, "identity_injection": True}, _ctx(raw))
    units = ch.chunk(_DOC)
    joined = " ".join(u.text for u in units)
    assert "Falcon router" not in joined              # not applied
    assert "The retry policy is 3 attempts." in joined  # reverted to original
    assert ch.identity_stats["source_violations"] == 1
    assert ch.identity_stats["stamps_total"] == 0


def test_source_tokens_and_proper_tokens():
    spans = sentence_spans(_DOC.text)
    src = identity_source_tokens(_DOC.text, spans, "The Marlin planner")
    assert "Marlin" in src
    assert _proper_tokens("The Marlin planner's retry policy") == {"Marlin"}


# ---- identity tagger ------------------------------------------------------
def test_identity_tagger_poor_vs_rich():
    from src.datasets.base import Query, GoldSpan
    from src.datasets.track_b_public import tag_identity
    doc = Document("p1", "Marlin: A Distributed Planner\n\nWe present Marlin, a scheduler.")
    rich = Query("q1", "How does Marlin handle retries?", [GoldSpan("p1", 0, 10)])
    poor = Query("q2", "What is the default retry count?", [GoldSpan("p1", 0, 10)])
    assert tag_identity(rich, doc) == "identity_rich"
    assert tag_identity(poor, doc) == "identity_poor"
