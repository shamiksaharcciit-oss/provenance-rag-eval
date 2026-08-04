"""The equality claim behind `src/pw1/safe_encode.py`, tested rather than argued.

The module's justification is that replicating `encode`'s length sort and batch boundaries gives
every batch exactly the set it had in the monolithic call, and that process boundaries have no
numerical effect. That is a chain of reasoning about a third-party library's internals, so it is
asserted as BIT-IDENTITY — not closeness — against the monolithic path on MiniLM, which runs
both ways in this environment.

If these ever fail, the sharding has a numerical surface that has not been found. The correct
response is to investigate it, NOT to downgrade the assertion to a tolerance.
"""
from __future__ import annotations

import os

import numpy as np
import pytest

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

MODEL, REV = "all-MiniLM-L6-v2", "main"
pytest.importorskip("sentence_transformers")


def _texts(n: int, lo: int = 40, hi: int = 400) -> list[str]:
    """Widely varying lengths, so the length sort actually reorders and ties occur."""
    rng = np.random.default_rng(1337)
    out = []
    for i in range(n):
        w = int(rng.integers(lo, hi))
        out.append(f"doc {i} " + " ".join(f"token{j % 97}" for j in range(w)))
    out += [out[0], out[1]]            # exact-length ties, to pin tie handling
    return out


@pytest.fixture(scope="module")
def model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL, revision=REV, device="cpu")


def test_interleaving_is_off_for_this_model_on_cpu(model):
    """The sharding is only equivalent when encode() does NOT interleave. Asserted, not assumed —
    if a future version enables flattening on CPU, this fails before any number is produced."""
    from src.pw1.safe_encode import assert_no_interleave
    assert model._can_flatten_inputs() is False
    assert_no_interleave(model)


def test_sharded_encode_is_BIT_IDENTICAL_to_the_monolithic_path(model):
    """THE CLAIM. Not 'close' — identical."""
    from src.pw1.safe_encode import sharded_encode_st
    texts = _texts(70)                                  # >1 batch at 64
    mono = model.encode(texts, batch_size=64, convert_to_numpy=True,
                        show_progress_bar=False, normalize_embeddings=False)
    shard = sharded_encode_st(MODEL, REV, texts, batch_size=64)
    assert shard.shape == mono.shape
    assert np.array_equal(mono, shard), (
        f"NOT identical: max abs diff {np.abs(mono - shard).max():.3e}. The sharding has a "
        f"numerical surface — investigate it; do not relax this to a tolerance.")


def test_bit_identical_when_the_batch_boundary_splits_a_tie(model):
    """Ties in the length key are the case where a replicated argsort could diverge."""
    from src.pw1.safe_encode import sharded_encode_st
    texts = ["same length text here"] * 130            # every key identical
    mono = model.encode(texts, batch_size=64, convert_to_numpy=True,
                        show_progress_bar=False, normalize_embeddings=False)
    shard = sharded_encode_st(MODEL, REV, texts, batch_size=64)
    assert np.array_equal(mono, shard)


def test_bit_identical_for_a_single_partial_batch(model):
    from src.pw1.safe_encode import sharded_encode_st
    texts = _texts(9)
    mono = model.encode(texts, batch_size=64, convert_to_numpy=True,
                        show_progress_bar=False, normalize_embeddings=False)
    assert np.array_equal(mono, sharded_encode_st(MODEL, REV, texts, batch_size=64))


def test_row_order_is_the_callers_order_not_the_sorted_order(model):
    """The unsort must restore input order; a silent permutation would misalign every unit id
    against its embedding and would not show up as a crash."""
    from src.pw1.safe_encode import sharded_encode_st
    texts = _texts(70)
    shard = sharded_encode_st(MODEL, REV, texts, batch_size=64)
    single = model.encode([texts[5]], batch_size=1, convert_to_numpy=True,
                          show_progress_bar=False, normalize_embeddings=False)[0]
    assert np.allclose(shard[5], single, atol=1e-5)


def test_empty_input_is_handled(model):
    from src.pw1.safe_encode import sharded_encode_st
    assert sharded_encode_st(MODEL, REV, [], batch_size=64).shape[0] == 0
