"""Track C gold-drafting helper (plan §5.1-C).

Samples passages from a user-supplied corpus and uses the LLM to DRAFT candidate
(question, evidence-span) pairs for HUMAN verification. It NEVER auto-accepts LLM gold —
output is written to `candidates.jsonl` with a `verified: false` flag; a human must
review, correct offsets, and set `verified: true` before the pairs are used as gold.

Usage:
  python scripts/build_gold.py --data-dir data/internal --n 40 --provider anthropic
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as C
from src.datasets.track_c_internal import _read_text_file
from src.llm.client import build_llm

_SYS = ("You draft ONE evaluation question answerable ONLY from the given passage, plus "
        "the minimal exact evidence substring. Return JSON: "
        '{"question": "...", "evidence": "<verbatim substring of the passage>"}.')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/internal")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--provider", default="anthropic")
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--out", default="data/internal/candidates.jsonl")
    args = ap.parse_args()

    cfg = C.load_default()
    cfg["llm"]["provider"] = args.provider
    llm = build_llm(cfg)
    if llm.is_none:
        print("provider=none: cannot draft candidates; set --provider anthropic")
        return 1

    root = Path(args.data_dir)
    docs = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in (".md", ".txt", ".html", ".htm", ".pdf"):
            text = _read_text_file(p)
            if text.strip():
                docs.append((str(p.relative_to(root)), text))
    if not docs:
        print(f"no documents under {root}")
        return 1

    rng = random.Random(args.seed)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for i in range(args.n):
            doc_id, text = rng.choice(docs)
            if len(text) < 200:
                continue
            start = rng.randint(0, max(0, len(text) - 800))
            passage = text[start:start + 800]
            try:
                raw = llm.complete(f"PASSAGE:\n{passage}", system=_SYS)
                data = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
            except Exception as e:
                print(f"  skip {doc_id}: {e}")
                continue
            evidence = data.get("evidence", "")
            pos = text.find(evidence)
            rec = {
                "query_id": f"cand-{i:03d}", "text": data.get("question", ""),
                "answer": None, "qtype": "factual", "verified": False,
                "gold_spans": ([{"doc_id": doc_id, "start_char": pos,
                                 "end_char": pos + len(evidence)}] if pos >= 0 else []),
                "_note": "HUMAN MUST VERIFY question + offsets before use as gold",
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            written += 1
    print(f"wrote {written} UNVERIFIED candidates -> {out_path}")
    print("Review each, fix offsets, set verified=true, then save as queries.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
