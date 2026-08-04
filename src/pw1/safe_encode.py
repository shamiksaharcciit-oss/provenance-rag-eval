"""Per-batch process-isolated encoding that is BIT-IDENTICAL to the monolithic path.

`BAAI/bge-base-en-v1.5` segfaults in this environment (Windows access violation 0xC0000005)
partway through encoding a corpus. The fault is cumulative across BATCHES — a batch that crashes
encodes cleanly when it is the first work a fresh process does — and a single monolithic
`encode` call is enough to trigger it, so isolating calls does not help. Isolating each BATCH
does.

**Why this changes no number.** `SentenceTransformer.encode` sorts inputs by descending
`_input_length` (character count for strings), then encodes contiguous slices of that order at
`batch_size`, then unsorts. Padding is set by the longest member of a batch — a property of the
SET, not of the order within it — and a transformer forward pass has no reduction across the
batch dimension, so rows are independent. Replicating the same sort and the same batch boundaries
therefore gives every batch exactly the set it had in the monolithic call. Process boundaries have
no numerical effect at all.

That is an argument, so it is also a test: `tests/test_pw1_safe_encode.py` asserts BIT-IDENTITY
against the monolithic path on MiniLM, where both run. Not "close" — identical. If that ever
fails, this module has a numerical surface that has not been found and must not be used.

Two caveats the implementation handles explicitly:
  * `_interleave_sorted_indices` reorders when `_can_flatten_inputs()` is true (flash-attention
    flattening). It is False for these models on CPU, and this module ASSERTS that rather than
    assuming it.
  * the sort key is taken from the installed `SentenceTransformer._input_length`, not
    reimplemented, because it has changed across releases.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]

MAX_BATCH_ATTEMPTS = 8
CHECKPOINT_DIR = ROOT / "cache" / "pw1_encode"
# Every crashed attempt is recorded here so the fault's frequency is reportable rather than
# absorbed by the retry. A silent retry would turn an intermittent hardware-or-runtime fault
# into an invisible one.
CRASH_LOG: list[dict] = []


class FlattenInputsUnsupported(AssertionError):
    """`_can_flatten_inputs()` is true, so encode() interleaves and this sharding is wrong."""


def _worker_env() -> dict:
    env = dict(os.environ)
    env.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    env.setdefault("OMP_NUM_THREADS", "1")
    env.setdefault("TOKENIZERS_PARALLELISM", "false")
    env.setdefault("OMP_STACKSIZE", "64M")   # cheap, no numerical effect; see the errata
    # Each batch is a fresh process, so each would otherwise re-contact the HF Hub to revalidate
    # the snapshot. The weights are already local and pinned by revision; going offline removes
    # a network round-trip per batch and cannot change what is loaded.
    env.setdefault("HF_HUB_OFFLINE", "1")
    env.setdefault("TRANSFORMERS_OFFLINE", "1")
    return env


def sharded_encode_st(model_name: str, revision: str, texts: list[str], batch_size: int,
                      device: str = "cpu", verbose: bool = False) -> np.ndarray:
    """Equivalent of `SentenceTransformer(model).encode(texts, batch_size, normalize=False)`.

    Each batch is encoded by a fresh subprocess. Returns rows in the caller's input order.
    """
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)

    from sentence_transformers import SentenceTransformer

    # SINGLE-BATCH FAST PATH. The fault needs at least two batches inside one process — the
    # 64-longest-texts experiment showed one fresh-process batch survives — so an input that
    # fits in a single batch does not need isolating. It is also bit-identical for the same
    # reason the sharding is: one batch, one set, rows independent.
    #
    # This matters enormously in practice: the retriever encodes ONE QUERY PER CALL, so without
    # this every query spawned a subprocess and a full model load. The first attempt at bge/A
    # was observed doing exactly that ("batch 1/1 ok (1 texts)" per query) and would have taken
    # hours.
    if len(texts) <= batch_size:
        from sentence_transformers import SentenceTransformer
        m = _cached_model(model_name, revision, device)
        return np.asarray(m.encode(texts, batch_size=batch_size, convert_to_numpy=True,
                                   show_progress_bar=False, normalize_embeddings=False))

    order = _length_order(model_name, revision, texts, device)
    ordered = [texts[i] for i in order]

    # RESUMABLE. Without checkpointing, a crash loses the whole run and a complete encode needs
    # a lucky uninterrupted session — which on a machine that sometimes fails 8/8 may never
    # arrive. With it, the requirement changes from "every batch must succeed in one session" to
    # "each batch must succeed ONCE, EVER", across retries, restarts and days. Eight batches at
    # 64 covers both family-1 conditions on Track A.
    #
    # The key is the batch's content hash plus model and revision and batch size, so a resumed
    # run cannot splice batches encoded under a different state.
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    out_parts: list[np.ndarray] = []
    with tempfile.TemporaryDirectory(prefix="pw1_enc_") as td:
        tmp = Path(td)
        n_batches = (len(ordered) + batch_size - 1) // batch_size
        for b, start in enumerate(range(0, len(ordered), batch_size)):
            chunk = ordered[start:start + batch_size]
            ck = _checkpoint_path(model_name, revision, batch_size, chunk)
            if ck.is_file():
                out_parts.append(np.load(ck))
                if verbose:
                    print(f"    batch {b + 1}/{n_batches} restored from checkpoint", flush=True)
                continue
            fin, fout = tmp / f"in_{b}.json", tmp / f"out_{b}.npy"
            fin.write_text(json.dumps(chunk), encoding="utf-8")
            # BOUNDED RETRY. The fault is INTERMITTENT, not a deterministic property of an
            # input: the exact operation that survived once (fresh process, 64 longest texts,
            # batch 64) crashed on a later attempt with the same 0xC0000005. Retrying a crashed
            # batch changes no number -- a successful encode is a successful encode, and
            # `tests/test_pw1_safe_encode.py` pins that successful encodes are bit-identical to
            # the monolithic path. What retry buys is completion; what it must NOT do is hide
            # how often the fault fires, so every attempt is counted and reported.
            data, crashes = None, 0
            for attempt in range(1, MAX_BATCH_ATTEMPTS + 1):
                if fout.is_file():
                    fout.unlink()
                proc = subprocess.run(
                    [sys.executable, "-m", "src.pw1.safe_encode", model_name, revision,
                     str(fin), str(fout), str(batch_size), device],
                    cwd=str(ROOT), env=_worker_env(), capture_output=True)
                if proc.returncode == 0 and fout.is_file():
                    data = np.load(fout)
                    break
                crashes += 1
                CRASH_LOG.append({"batch": b, "attempt": attempt,
                                  "returncode": proc.returncode,
                                  "n_texts": len(chunk)})
                if verbose:
                    print(f"    batch {b + 1}/{n_batches} attempt {attempt} FAILED "
                          f"(exit {proc.returncode}); retrying", flush=True)
            if data is None:
                raise RuntimeError(
                    f"batch {b + 1}/{n_batches} failed {MAX_BATCH_ATTEMPTS} times "
                    f"(last exit {proc.returncode}); stderr tail: "
                    f"{proc.stderr.decode('utf-8', 'replace')[-400:]}")
            np.save(ck, data)
            out_parts.append(data)
            if verbose:
                print(f"    batch {b + 1}/{n_batches} ok ({len(chunk)} texts"
                      f"{f', {crashes} crash(es)' if crashes else ''})", flush=True)

    # Fail loudly rather than returning a short or misordered matrix from a partial resume.
    if len(out_parts) != n_batches:
        raise RuntimeError(f"resume produced {len(out_parts)} batches, expected {n_batches}")
    stacked = np.vstack(out_parts)
    if stacked.shape[0] != len(texts):
        raise RuntimeError(f"reassembled {stacked.shape[0]} rows, expected {len(texts)}")
    return stacked[np.argsort(order)]


def _checkpoint_path(model_name: str, revision: str, batch_size: int,
                     chunk: list[str]) -> Path:
    h = hashlib.sha256()
    h.update(f"{model_name}|{revision}|{batch_size}|".encode("utf-8"))
    for t in chunk:                      # order matters: it is the batch's identity
        h.update(t.encode("utf-8"))
        h.update(b"|")
    return CHECKPOINT_DIR / f"{h.hexdigest()}.npy"


_MODEL_CACHE: dict = {}


def _cached_model(model_name: str, revision: str, device: str):
    """One in-process model for the single-batch path; reloading per call would dominate."""
    key = (model_name, revision, device)
    if key not in _MODEL_CACHE:
        from sentence_transformers import SentenceTransformer
        m = SentenceTransformer(model_name, revision=revision, device=device)
        assert_no_interleave(m)
        _MODEL_CACHE[key] = m
    return _MODEL_CACHE[key]


def _length_order(model_name: str, revision: str, texts: list[str], device: str) -> np.ndarray:
    """The installed encode()'s own sort, replicated exactly — not reimplemented."""
    from sentence_transformers import SentenceTransformer
    key = SentenceTransformer._input_length
    return np.argsort([-key(t) for t in texts])


def assert_no_interleave(model) -> None:
    """The sharding is only equivalent when encode() does NOT interleave the sorted order."""
    if model._can_flatten_inputs():
        raise FlattenInputsUnsupported(
            "_can_flatten_inputs() is True, so encode() interleaves the length-sorted indices "
            "and contiguous sharding no longer reproduces its batches. Do not use this module.")


def _main(argv: list[str]) -> int:
    """Worker: encode ONE batch in a fresh process and write it to .npy."""
    model_name, revision, fin, fout, batch_size, device = argv
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    from sentence_transformers import SentenceTransformer
    texts = json.loads(Path(fin).read_text(encoding="utf-8"))
    m = SentenceTransformer(model_name, revision=revision, device=device)
    assert_no_interleave(m)
    v = m.encode(texts, batch_size=int(batch_size), convert_to_numpy=True,
                 show_progress_bar=False, normalize_embeddings=False)
    np.save(fout, np.asarray(v))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
