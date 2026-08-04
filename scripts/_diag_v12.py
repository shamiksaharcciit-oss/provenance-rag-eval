import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config as C
from src.chunkers.base import ChunkContext
from src.chunkers.formatter import FormatterChunker
from src.chunkers.prompts import formatter_system_prompt, formatter_user_prompt, number_sentences
from src.chunkers.formatter import _subject_phrase
from src.textutil import sentence_spans, count_tokens
from src.datasets import track_b_public as TB
from src.index.embed import Embedder
from src.llm.client import build_llm

cfg = C.load_default()
cfg["embedding"]["model"] = "all-MiniLM-L6-v2"
cfg["llm"]["provider"] = "anthropic"; cfg["llm"]["model"] = "claude-sonnet-5"
ds = TB.load_b2(seed=1337, new_seed=20272, n_queries=180)
emb = Embedder(cfg, cache_root=cfg["_cache_root"])
llm = build_llm(cfg)
ctx = ChunkContext(embedder=emb, llm=llm, config=cfg)

fmt = FormatterChunker({"reference_resolution": True, "dedup": True, "right_size": True,
                        "soft_target_tokens": 384, "identity_injection": True,
                        "verbatim_guardrail": True, "diff_gate": True}, ctx)

fell_back = 0; ok = 0; truncated = 0
for doc in ds.documents[:15]:
    spans = sentence_spans(doc.text)
    sents = [doc.text[s:e] for s, e in spans]
    subject = _subject_phrase(doc.text, spans)
    numbered = number_sentences(sents)
    sysp = formatter_system_prompt(True, True, True)
    raw = llm.complete(formatter_user_prompt(subject, numbered), system=sysp)  # cached
    # try the exact parse _chunk_llm uses
    try:
        data = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
        ok += 1
        nres = len(data.get("resolved", []))
    except Exception as e:
        fell_back += 1
        nres = -1
    # crude truncation check: does raw end mid-JSON (no closing brace after last '{')?
    tail = raw.strip()[-40:]
    is_trunc = not tail.rstrip().endswith("}")
    if is_trunc:
        truncated += 1
    print(f"doc {doc.doc_id[:14]:14s} sents={len(sents):3d} raw_len={len(raw):5d} "
          f"resolved={nres:3d} parse_ok={nres>=0} looks_truncated={is_trunc} tail={tail!r}")
print(f"\nSUMMARY (15 docs): parse_ok={ok} fell_back={fell_back} truncated_tail={truncated}")
print(f"client max_tokens={llm.max_tokens}")
