"""Re-run the common-size control and compute paired-bootstrap CIs (handoff item 1b).

The control (§5.2) compares naive 256-token chunking on the ORIGINAL corpus against the same
chunking on the FORMATTED corpus, isolating text quality from unit-count effects. `run.py`
stores only the two point estimates in `tracks_meta[].common_size` and discards the per-query
vectors, so no CI can be recomputed from any existing artifact — the control has to be re-run
with the vectors retained. That is what this does.

It reproduces run_track's split exactly (per-track dev_fraction, same seed) so the query set
matches the published runs.

`--embedding-model` matters: v1.1 (`run-20260724-135411`, `run-20260724-174208`) used the
speed fallback `all-MiniLM-L6-v2`, while v1.3 used the config default `BAAI/bge-base-en-v1.5`.
Absolute levels are not comparable across the two, so the CI must be attributed to a named
embedder.

    python scripts/common_size_ci.py --track A --embedding-model all-MiniLM-L6-v2
    python scripts/common_size_ci.py --track A,B --embedding-model BAAI/bge-base-en-v1.5
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src import config as C  # noqa: E402
from src.chunkers import build_chunker  # noqa: E402
from src.chunkers.base import ChunkContext  # noqa: E402
from src.datasets import load_track_dataset  # noqa: E402
from src.index.embed import Embedder  # noqa: E402
from src.llm.client import build_llm  # noqa: E402
from src.pipeline import build_units, evaluate  # noqa: E402
from src.run import split_dev_test  # noqa: E402
from src.stats.tests import paired_bootstrap_diff, paired_permutation_p  # noqa: E402

ORIG = {"id": "orig256", "chunker": "naive",
        "params": {"chunk_tokens": 256, "overlap_frac": 0.0}}
FMT = {"id": "fmt256", "chunker": "formatted_naive",
       "params": {"chunk_tokens": 256, "overlap_frac": 0.0,
                  "reference_resolution": True, "dedup": True,
                  "right_size": True, "soft_target_tokens": 384}}


def _environment() -> dict:
    """Pin what the re-run actually ran under (PW-1 check section 6).

    A guard-1 re-run's evidential value depends entirely on the environment matching the one that
    produced the published numbers, and 'it reproduced' without 'under what' is not a record.
    Embedding models are not bit-identical across torch versions or across CPU/GPU, and a recall
    metric on 176 queries can absorb a small numerical difference without moving - which is
    exactly the case where the record matters most, because the result cannot reveal it.
    """
    import importlib
    import os
    import platform
    env = {"python": platform.python_version(), "platform": platform.platform()}
    # The published runs recorded python, os, embedder, llm, faiss and seed -- and NONE of the
    # native stack. When bge began segfaulting there was nothing to diff against, and (c)
    # "restore the pinned environment" was unavailable because no pin existed. Everything that
    # could produce a native access violation is recorded here.
    for mod in ("torch", "sentence_transformers", "transformers", "tokenizers", "numpy",
                "faiss", "rank_bm25", "scipy", "safetensors", "huggingface_hub"):
        try:
            m = importlib.import_module(mod)
            env[mod] = getattr(m, "__version__", "unknown")
        except Exception:
            env[mod] = "not installed"
    try:
        import torch
        env["device"] = "cuda" if torch.cuda.is_available() else "cpu"
        env["torch_num_threads"] = torch.get_num_threads()
    except Exception:
        env["device"] = "unknown"
    # Threading/allocator runtime: the layer the access violation lives in.
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "KMP_DUPLICATE_LIB_OK", "OMP_STACKSIZE",
                "OPENBLAS_NUM_THREADS", "TOKENIZERS_PARALLELISM"):
        env[f"env:{var}"] = os.environ.get(var, "<unset>")
    try:
        import torch
        cfg = torch.__config__.parallel_info()
        env["torch_parallel_info"] = " | ".join(x.strip() for x in cfg.splitlines() if x.strip())
    except Exception:
        env["torch_parallel_info"] = "unavailable"
    return env


args_sharded = False


def run_track_control(track_id: str, cfg: dict, k: int, iters: int) -> dict:
    track_cfg = C.load_track(track_id)
    track_model = track_cfg.get("params", {}).get("llm_model")
    tcfg = C.deep_merge(cfg, {"llm": {"model": track_model}}) if track_model else cfg
    dataset = load_track_dataset(track_cfg, tcfg["seed"])

    # Identical split logic to run_track.
    track_dev = track_cfg.get("params", {}).get("dev_fraction")
    dev_frac = track_dev if track_dev is not None else tcfg.get("sweep", {}).get("dev_fraction", 0.2)
    _dev, test_q = split_dev_test(dataset, dev_frac, tcfg["seed"])

    embedder = Embedder(tcfg, cache_root=tcfg["_cache_root"])
    ctx = ChunkContext(embedder=embedder, llm=build_llm(tcfg), config=tcfg)
    n_docs = len(dataset.documents)
    print(f"  track {track_id}: {n_docs} docs, {len(test_q)} test queries "
          f"(dev_fraction={dev_frac})")

    out = {}
    vecs = {}
    arm_inputs: dict = {}
    for tag, cond in (("original_256", ORIG), ("formatted_256", FMT)):
        units = build_units(build_chunker(cond, ctx), dataset)
        res = evaluate(cond["id"], units, embedder, tcfg, test_q, n_docs)
        # PERSIST WHAT THE ARMS NEED. Nothing ever persisted orig256/fmt256 retrieval, which is
        # exactly why these cells had to be re-run instead of re-scored. Capturing it at the
        # moment it exists is the corollary of template A2: an expensive result must be written
        # when it is produced, because the second chance costs the same as the first. With this,
        # S1/S2/S3 re-score with NO encoding.
        arm_inputs[tag] = {
            "per_query": res.per_query,
            "units": [{"unit_id": u.unit_id, "doc_id": u.doc_id,
                       "source_ranges": [list(r) for r in u.source_ranges]} for u in units]}
        m = res.metrics["hybrid"]["any"]
        vecs[tag] = m["_per_query"]["recall_at_k"][k]
        out[tag] = round(m["recall_at_k"][k], 4)
        out[f"{tag}_units"] = res.chunk_stats["index_units"]
        print(f"    {tag}: recall@{k}={out[tag]:.4f}  units={out[f'{tag}_units']}")

    out["_vectors"] = {"formatted_256": list(map(int, vecs["formatted_256"])),
                       "original_256": list(map(int, vecs["original_256"]))}
    out["_arm_inputs"] = arm_inputs
    a, b = vecs["formatted_256"], vecs["original_256"]
    assert len(a) == len(b) == len(test_q), "paired vectors must align with the test split"
    d = paired_bootstrap_diff(a, b, iters, tcfg["seed"], 0.95)
    p = paired_permutation_p(a, b, iters, tcfg["seed"])
    out.update({
        "track": track_id,
        "n_queries": len(test_q),
        "metric": f"recall@{k}",
        "delta": round(d["mean_diff"], 4),
        "ci95": [round(x, 4) for x in d["ci95"]],
        "p_value": round(p, 5),
        "significant_ci": d["significant_ci"],
        "embedding_model": tcfg["embedding"]["model"],
        "environment": _environment(),
        "sharded_encode": bool(args_sharded),
    })
    print(f"    delta={out['delta']:+.4f}  95% CI [{out['ci95'][0]:+.4f}, {out['ci95'][1]:+.4f}]"
          f"  p={out['p_value']:.5f}  {'SIGNIFICANT' if out['significant_ci'] else 'n.s.'}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default="A")
    ap.add_argument("--embedding-model", default=None)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--iters", type=int, default=10000)
    ap.add_argument("--out", default=None, help="write JSON here")
    ap.add_argument("--sharded-encode", action="store_true",
                    help="encode each batch in a fresh process (src/pw1/safe_encode.py). "
                         "BIT-IDENTICAL to the monolithic path -- proven in "
                         "tests/test_pw1_safe_encode.py -- so this is NOT a declared deviation. "
                         "Needed because bge segfaults mid-corpus in this environment.")
    args = ap.parse_args()

    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    cfg["llm"]["provider"] = "anthropic"          # cache-served; fails loud on a miss
    if args.embedding_model:
        cfg["embedding"]["model"] = args.embedding_model
    print(f"common-size control · embedder={cfg['embedding']['model']} · "
          f"{args.iters} bootstrap iters")

    global args_sharded
    args_sharded = args.sharded_encode
    if args.sharded_encode:
        from src.index.embed import Embedder as _E
        from src.pw1.safe_encode import sharded_encode_st
        def _sharded(self, texts):
            return sharded_encode_st(self.model_name, self.revision, list(texts),
                                     self.batch_size, device=self.device, verbose=True)
        _E._encode_st = _sharded
        print("  sharded encoding ON (bit-identical; see tests/test_pw1_safe_encode.py)")

    results = [run_track_control(t.strip(), cfg, args.k, args.iters)
               for t in args.track.split(",") if t.strip()]
    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
