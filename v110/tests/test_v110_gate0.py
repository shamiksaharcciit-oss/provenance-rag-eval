"""v1.10 Gate 0 unit tests (§6): lattice identity, crossing-unit-with-blurb accounting,
padding-truncation roundtrip, and the §2 charged-but-cannot-score contract.

No model is called and no corpus is loaded here; the census (`v110/gate0_build.py`) is what
meets the real inputs. These pin behaviour.
"""
from __future__ import annotations

import pytest

from src.chunkers.base import Unit
from src.datasets.base import GoldSpan, Query
from src.score.provenance import ANY, is_hit
from src.textutil import count_tokens
from src.v17.e1 import units_at_budget
from v110.arms import (FreshCallAttempted, assert_prepended_text_is_unattributed, build_padded,
                       inventory_hash, no_fresh_calls)
from v110.padding import content_words, filler_for, pool_hash, truncate_to_tokens

D = "doc1"


def base_unit(i, n=100):
    return Unit(unit_id=f"u{i}", text=" ".join([f"w{i}"] * n), doc_id=D,
                source_ranges=[(i * 100, i * 100 + 100)])


def ctx_unit(i, blurb_tokens, n=100):
    blurb = " ".join(["ctx"] * blurb_tokens)
    b = base_unit(i, n)
    return Unit(unit_id=f"u{i}", text=f"{blurb}\n\n{b.text}", doc_id=D,
                source_ranges=list(b.source_ranges), meta={"blurb": blurb})


# ---------------------------------------------------------------- padding roundtrip

def test_filler_is_exactly_the_target_length():
    for n in (1, 5, 29, 48, 77, 86, 200):
        assert count_tokens(filler_for("u0", n)) == n


def test_filler_is_deterministic_for_a_unit_id():
    assert filler_for("u7", 40) == filler_for("u7", 40)


def test_filler_differs_between_units():
    assert filler_for("u1", 40) != filler_for("u2", 40)


def test_filler_keys_on_unit_id_not_position():
    """Rebuilding the inventory in another order must not shift the assignment."""
    a = {u: filler_for(u, 30) for u in ("u1", "u2", "u3")}
    b = {u: filler_for(u, 30) for u in ("u3", "u1", "u2")}
    assert a == b


def test_zero_length_filler_is_empty():
    assert filler_for("u0", 0) == ""


def test_truncation_lands_on_a_token_boundary():
    text = " ".join(f"w{i}" for i in range(50))
    for k in (1, 13, 49):
        assert count_tokens(truncate_to_tokens(text, k)) == k


def test_pool_hash_is_stable_within_a_run():
    assert pool_hash() == pool_hash() and len(pool_hash()) == 64


def test_content_words_exclude_function_words_and_short_tokens():
    cw = content_words("The cat sat on a very old mat by it")
    assert "cat" in cw and "old" in cw and "mat" in cw
    for w in ("the", "on", "a", "very", "by", "it"):
        assert w not in cw


# ---------------------------------------------------------------- §2 charged but cannot score

def test_prepended_text_is_charged_to_the_budget_and_cannot_score():
    base = [base_unit(i) for i in range(3)]
    ctx = [ctx_unit(i, 40) for i in range(3)]
    rec = assert_prepended_text_is_unattributed(base, ctx, "C")
    assert rec["prepended_tokens_min"] == rec["prepended_tokens_max"] == 40
    assert rec["n_units"] == 3


def test_a_unit_that_widened_its_ranges_is_rejected():
    base = [base_unit(0)]
    bad = [Unit(unit_id="u0", text="x " * 200, doc_id=D, source_ranges=[(0, 500)])]
    with pytest.raises(AssertionError, match="able to score"):
        assert_prepended_text_is_unattributed(base, bad, "bad")


def test_prepended_text_earns_no_provenance_hit():
    """The scorer must see exactly the base chunk's coverage, blurb or no blurb."""
    q = Query(query_id="q", text="?", gold_spans=[GoldSpan(doc_id=D, start_char=10, end_char=20)])
    assert is_hit(base_unit(0), q, variant=ANY) == is_hit(ctx_unit(0, 40), q, variant=ANY) is True
    far = Query(query_id="q2", text="?",
                gold_spans=[GoldSpan(doc_id=D, start_char=9000, end_char=9010)])
    assert is_hit(ctx_unit(0, 40), far, variant=ANY) is False


def test_padded_arm_matches_the_blurb_length_per_chunk():
    base = [base_unit(i) for i in range(4)]
    ctx = [ctx_unit(i, 20 + i * 7) for i in range(4)]
    pad = build_padded(base, ctx)
    for c, p in zip(ctx, pad):
        assert count_tokens(p.text) == count_tokens(c.text), "P and C must be length-matched"


def test_padded_arm_refuses_misaligned_inventories():
    with pytest.raises(AssertionError, match="not aligned"):
        build_padded([base_unit(0)], [ctx_unit(1, 10)])


def test_padded_arm_refuses_different_sized_inventories():
    with pytest.raises(AssertionError, match="arm inventories differ"):
        build_padded([base_unit(0)], [ctx_unit(0, 10), ctx_unit(1, 10)])


# ---------------------------------------------------------------- crossing unit with blurb

def test_crossing_unit_is_included_and_its_blurb_counts_toward_the_budget():
    """The unit that crosses B is taken and its FULL length, blurb included, is charged."""
    ranked = ["u0", "u1", "u2", "u3"]
    with_blurb = {u: 800 for u in ranked}          # 760 chunk + 40 blurb
    without = {u: 760 for u in ranked}
    assert units_at_budget(ranked, with_blurb, 1920) == ["u0", "u1", "u2"]   # 2400 >= 1920
    assert units_at_budget(ranked, without, 1920) == ["u0", "u1", "u2"]      # 2280 >= 1920


def test_blurbs_can_change_how_many_units_fit_in_the_budget():
    """The whole point of §2: paying for prepended tokens can cost an arm a retrieved unit."""
    ranked = ["u0", "u1", "u2", "u3", "u4"]
    assert units_at_budget(ranked, {u: 500 for u in ranked}, 1920) == ["u0", "u1", "u2", "u3"]
    assert units_at_budget(ranked, {u: 700 for u in ranked}, 1920) == ["u0", "u1", "u2"]


# ---------------------------------------------------------------- lattice identity

def test_decomposition_is_exact_on_integer_numerators():
    """D_pad + D_info == D_total, always, on the k/n lattice."""
    from src.v17.e1 import contrast

    n = 12
    U = [1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0]
    P = [1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0]
    Cc = [1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 0]
    d_pad = contrast(P, U, n, 200, 1337)
    d_info = contrast(Cc, P, n, 200, 1337)
    d_total = contrast(Cc, U, n, 200, 1337)
    assert d_pad["numerator"] + d_info["numerator"] == d_total["numerator"]
    assert d_total["delta_exact"] == "2/12"


# ---------------------------------------------------------------- the zero-spend guard

def test_no_fresh_calls_blocks_the_provider():
    from src.llm.client import LLMClient

    c = LLMClient(provider="anthropic")
    with no_fresh_calls():
        with pytest.raises(FreshCallAttempted, match="spends nothing"):
            c._call_provider("p", "s")


def test_no_fresh_calls_restores_the_original_afterwards():
    import src.llm.client as LC

    before = LC.LLMClient._call_provider
    with no_fresh_calls():
        pass
    assert LC.LLMClient._call_provider is before


# ---------------------------------------------------------------- inventory binding

def test_inventory_hash_binds_ids_docs_and_ranges():
    a = [base_unit(0), base_unit(1)]
    assert inventory_hash(a) == inventory_hash([base_unit(0), base_unit(1)])
    moved = [base_unit(0), Unit(unit_id="u1", text="x", doc_id=D, source_ranges=[(999, 1099)])]
    assert inventory_hash(a) != inventory_hash(moved)


def test_inventory_hash_is_order_sensitive():
    assert inventory_hash([base_unit(0), base_unit(1)]) != inventory_hash([base_unit(1), base_unit(0)])


# ---------------------------------------------------------------- census to fixed point (PF-G1)

def test_fixed_point_passes_when_no_query_word_is_shared():
    from v110.padding import assert_pool_fixed_point

    r = assert_pool_fixed_point(["the quantum flux capacitor subsystem"], ["what is the flux"])
    assert r["n_overlap_queries"] == 0


def test_fixed_point_raises_when_a_query_word_is_shared():
    """The 'another' case: one shared content word must fail the whole pass."""
    from v110.padding import PoolNotAtFixedPoint, assert_pool_fixed_point, pool_sentences

    word = sorted(content_words(" ".join(pool_sentences())))[0]
    with pytest.raises(PoolNotAtFixedPoint, match="re-run the FULL check"):
        assert_pool_fixed_point(["irrelevant corpus"], [f"a query mentioning {word}"])


def test_corpus_overlap_alone_is_not_a_failure():
    """Corpus overlap is quantified, not eliminated -- it must not raise."""
    from v110.padding import assert_pool_fixed_point, pool_sentences

    r = assert_pool_fixed_point([" ".join(pool_sentences())], ["zzz unrelated"])
    assert r["n_overlap_corpus"] > 0 and r["n_overlap_queries"] == 0
