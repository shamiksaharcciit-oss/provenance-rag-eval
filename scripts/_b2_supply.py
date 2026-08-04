"""B2 query-supply check (v1.2 §3, option b). Determines how many FRESH QASPER queries
exist (excluding the v1.1 B-150) and how many documents a fresh sample of 150 / 180 spans.
Outcome is recorded in preregistration.json before any B2 metric is computed."""
import os
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
import sys, random, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config as C
from src.datasets import track_b_public as B

cfg = C.load_default()
seed = cfg["seed"]  # 1337

# Full QASPER pool (no doc cap, take everything).
full = B.load({"params": {"candidates": ["qasper"], "n_queries": 100000, "max_docs": 0}}, seed=seed)
full_ids = [q.query_id for q in full.queries]
docs_by_id = {d.doc_id: d for d in full.documents}
print(f"FULL pool: {len(full.queries)} queries over {len(full.documents)} docs")

# v1.1 exclusion list: the exact B-150 (seed 1337, max_docs 60, n_queries 150).
excl = B.load({"params": {"candidates": ["qasper"], "n_queries": 150, "max_docs": 60}}, seed=seed)
excl_ids = {q.query_id for q in excl.queries}
print(f"v1.1 exclusion (B-150): {len(excl_ids)} query_ids over {len(excl.documents)} docs")

fresh = [q for q in full.queries if q.query_id not in excl_ids]
print(f"FRESH (non-excluded) queries available: {len(fresh)}")

def sample_docs(n, new_seed):
    rng = random.Random(new_seed)
    pool = list(fresh)
    rng.shuffle(pool)
    take = pool[:n]
    docs = sorted({q.gold_spans[0].doc_id for q in take})
    overlap = len({q.query_id for q in take} & excl_ids)
    return take, docs, overlap

for n in (150, 180):
    take, docs, overlap = sample_docs(n, new_seed=20272)
    print(f"  B2 n={len(take)}: spans {len(docs)} docs | overlap-with-exclusion={overlap}")

# doc-list hash for the n=180 stretch target (the frozen corpus if we take 180)
take180, docs180, _ = sample_docs(180, new_seed=20272)
doc_hash = hashlib.sha256("\n".join(docs180).encode()).hexdigest()
new_docs = [d for d in docs180 if d not in {x.doc_id for x in excl.documents}]
print(f"n=180 corpus: {len(docs180)} docs, of which {len(new_docs)} are NEW (not in v1.1 60) -> fresh baseline LLM")
print(f"doc-list hash (n=180): {doc_hash[:16]}...")
