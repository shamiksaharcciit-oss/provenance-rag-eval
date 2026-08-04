"""v1.8 §1 — arms and the fixed-k retrieval frame.

ARM CONSTRUCTION IS IMPORTED, NOT COPIED, exactly as v1.7's sweep imports it: `build_arm` comes
from `scripts/segment_size_sweep.py`, so "constructed by importing the v1.6 build procedures"
(§1) is true by construction and cannot drift. v1.7 established the pattern and the freeze
report promoted it to an instruction; this is the same import, one experiment later.

What differs from v1.6 and v1.7, deliberately and only here: **retrieval is fixed k = 5, with no
budget matching anywhere** (§1). That is not an improvement on the matched-budget frame — it is
the field-standard frame this experiment exists to examine, confound included. The size confound
that v1.6 removed is present here on purpose, and `U768` is in the design to measure it.

Nothing in this module scores anything. It builds inventories and ranked contexts; the
instruments live in `instruments.py` and the judge is not involved at any point here.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from segment_size_sweep import build_arm  # noqa: E402  (v1.6 procedure, unchanged)

from src.retrieve.retriever import Retriever  # noqa: E402
from src.textutil import count_tokens  # noqa: E402

#: §1 — three arms. `U768` is load-bearing: it separates size from editing inside the RAGAS
#: frame, mirroring v1.6's decomposition.
ARMS = ("U256", "U768", "F768")

#: §1 — the field-standard configuration under examination.
FIXED_K = 5

#: §2 — the separator joining the k retrieved units into one context block. Declared here so it
#: is a frozen constant rather than an incidental `"\n\n".join(...)` buried in a runner.
CONTEXT_SEPARATOR = "\n\n"


def retrieve_fixed_k(units, queries, embedder, cfg, k: int = FIXED_K) -> list[dict]:
    """Rank once per query and keep the top `k` units, in rank order.

    Returns one record per query with the ranked unit ids, their texts and their token counts.
    No budget logic: at fixed k the arms hand the generator *different* token counts, and that
    inequality is the object of study rather than a defect to correct.
    """
    r = Retriever(units, embedder, cfg)
    out = []
    for q in queries:
        ranked = r.retrieve(q.text, k)["hybrid"]
        assert len(ranked) <= k, f"retriever returned {len(ranked)} > k={k}"
        texts = [u.text for u in ranked]
        out.append({
            "query_id": q.query_id,
            "unit_ids": [u.unit_id for u in ranked],
            "doc_ids": [u.doc_id for u in ranked],
            "contexts": texts,
            "context_tokens": [count_tokens(t) for t in texts],
            "package_tokens": count_tokens(CONTEXT_SEPARATOR.join(texts)),
            "realised_k": len(ranked),
        })
    return out


def inventory_diagnostics(units, dataset) -> dict:
    """Descriptive build diagnostics for an arm. Pre-freeze material, not a result."""
    toks = [count_tokens(u.text) for u in units]
    toks_sorted = sorted(toks)
    n = len(toks_sorted)
    return {
        "index_units": len(units),
        "units_per_doc": round(len(units) / len(dataset.documents), 4),
        "token_mean": round(sum(toks) / n, 2),
        "token_median": toks_sorted[n // 2],
        "token_min": toks_sorted[0],
        "token_max": toks_sorted[-1],
    }
