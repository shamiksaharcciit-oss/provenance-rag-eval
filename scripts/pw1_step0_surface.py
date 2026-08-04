"""PW-1 step 0a — how much provenance-width inflation actually exists.

Descriptive only. No arms, no decisions, no outcome computed. Cache-only for the LLM
(`_call_provider` raised), so this cannot cost tokens or mint a corpus that differs from the
one the published runs used.

Measures, per track, for the size-matched control's two arms (naive-256 on the ORIGINAL corpus
vs naive-256 on the FORMATTED corpus):

  claimed surface   union of a unit's source_ranges, in original-document characters
  own text          len(unit.text) — what the unit actually holds
  width ratio       claimed / own — surface claimed per indexed character

For the original arm the ratio is 1.0 by construction (`source_ranges` is the substring's own
span). Anything above 1.0 on the formatted arm is the channel the white paper's §11 threats
paragraph describes.

It also decomposes the formatted arm's inflation into its TWO sources, which matters because
the PW-1 instructions only name the first:

  absorbed        original ranges of duplicate sentences the canonical sentence absorbed
  inheritance     a naive chunk inherits the WHOLE source_ranges of every formatter segment it
                  overlaps, even when it contains only part of that segment's text
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src import config as C  # noqa: E402
from src.chunkers import build_chunker  # noqa: E402
from src.chunkers.base import ChunkContext  # noqa: E402
from src.chunkers.formatted import _formatter_params  # noqa: E402
from src.chunkers.formatter import FormatterChunker, _normalize_for_dedup  # noqa: E402
from src.datasets import load_track_dataset  # noqa: E402
from src.index.embed import Embedder  # noqa: E402
from src.llm.client import LLMClient, build_llm  # noqa: E402
from src.pipeline import build_units  # noqa: E402
from src.textutil import merge_ranges, sentence_spans  # noqa: E402

ORIG = {"id": "orig256", "chunker": "naive",
        "params": {"chunk_tokens": 256, "overlap_frac": 0.0}}
FMT = {"id": "fmt256", "chunker": "formatted_naive",
       "params": {"chunk_tokens": 256, "overlap_frac": 0.0,
                  "reference_resolution": True, "dedup": True,
                  "right_size": True, "soft_target_tokens": 384}}


def _no_network(self, prompt, system):  # noqa: ANN001, ARG001
    raise RuntimeError("cache miss — step 0 is cache-only and must not call the API")


def span_chars(ranges) -> int:
    return sum(e - s for s, e in merge_ranges(list(ranges)))


def rule_based_dedup_estimate(dataset) -> tuple[int, int]:
    """(kept, absorbed) if dedup were decided by TEXT NORMALIZATION over every sentence.

    **This is NOT what the formatter does on the paths that produced the published numbers.**
    With `provider=anthropic` the drop set comes from the model's `drop` list, which is far more
    close to but not identical with it: the rule predicts 12,591 absorbed characters on Track A
    against the formatter's actual 12,019, and 2,919 against 2,887 on Track B.

    Retained, relabelled, and reported beside the actual figure because the first release of
    step 0a quoted this number AS the absorbed surface. It is a normalization-rule proxy, not
    the formatter's behaviour. Use `actual_absorbed_surface`.
    """
    own = absorbed = 0
    for doc in dataset.documents:
        spans = sentence_spans(doc.text)
        seen: dict[str, bool] = {}
        for s, e in spans:
            norm = _normalize_for_dedup(doc.text[s:e])
            if not norm:
                own += e - s
                continue
            if norm in seen:
                absorbed += e - s
            else:
                seen[norm] = True
                own += e - s
    return own, absorbed


def actual_absorbed_surface(dataset, ctx) -> tuple[int, int]:
    """(absorbed, total sentence surface) as the FORMATTER actually produced them.

    Captured at `_emit`, so it reflects whichever path ran — the LLM `drop` list under
    `provider=anthropic`, which is what the published numbers used. Corpus-level UNION, so no
    sentence is counted twice; the per-chunk sums reported by step 0c are a different quantity
    and are labelled as such there.
    """
    # Ranges MUST be unioned per document. Merging across documents treats two docs' offsets
    # as one coordinate space and silently collapses unrelated intervals — it under-counted
    # Track A by 2.1x before this was caught.
    absorbed: dict[str, list] = {}
    f = FormatterChunker(_formatter_params(FMT["params"]), ctx)
    original = f._emit

    def emit(doc, groups):
        for g in groups:
            for st in g:
                absorbed.setdefault(doc.doc_id, []).extend(st.absorbed)
        return original(doc, groups)

    f._emit = emit          # type: ignore[method-assign]
    try:
        for d in dataset.documents:
            f.chunk(d)
    finally:
        f._emit = original   # type: ignore[method-assign]
    total = sum(e - s for doc in dataset.documents
                for s, e in merge_ranges(sentence_spans(doc.text)))
    return sum(span_chars(v) for v in absorbed.values()), total


def main() -> int:
    LLMClient._call_provider = _no_network
    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    cfg["llm"]["provider"] = "anthropic"

    for track in ("A", "B"):
        tcfg_raw = C.load_track(track)
        tm = tcfg_raw.get("params", {}).get("llm_model")
        tcfg = C.deep_merge(cfg, {"llm": {"model": tm}}) if tm else cfg
        dataset = load_track_dataset(tcfg_raw, tcfg["seed"])
        ctx = ChunkContext(embedder=Embedder(tcfg, cache_root=tcfg["_cache_root"]),
                           llm=build_llm(tcfg), config=tcfg)
        doc_chars = sum(len(d.text) for d in dataset.documents)
        print(f"\n=== Track {track} — {len(dataset.documents)} docs, {doc_chars:,} chars ===")

        # CANONICAL: what the formatter actually absorbed, corpus-level union.
        act_abs, sent_total = actual_absorbed_surface(dataset, ctx)
        print(f"  sentence surface total {sent_total:,}   ACTUAL absorbed {act_abs:,} = "
              f"{act_abs / max(1, sent_total):.2%}")
        # For the record only: the normalization rule the LLM path does not use.
        rule_kept, rule_abs = rule_based_dedup_estimate(dataset)
        print(f"    (rule-based normalization estimate, NOT the formatter's behaviour: "
              f"{rule_abs:,} = {rule_abs / max(1, rule_kept + rule_abs):.2%} — "
              f"over-predicts by {rule_abs / max(1, act_abs):.2f}x)")

        # C3 formatter units: claimed should equal own ∪ absorbed exactly.
        c3 = FormatterChunker(_formatter_params(FMT["params"]), ctx)
        c3_units = [u for d in dataset.documents for u in c3.chunk(d)]
        c3_claimed = sum(span_chars(u.source_ranges) for u in c3_units)
        print(f"  C3 formatter units: {len(c3_units)}  claimed surface {c3_claimed:,}")

        for tag, cond in (("orig256", ORIG), ("fmt256", FMT)):
            units = build_units(build_chunker(cond, ctx), dataset)
            claimed = sum(span_chars(u.source_ranges) for u in units)
            own = sum(len(u.text) for u in units)
            n_ranges = sum(len(u.source_ranges) for u in units)
            print(f"  {tag:8} units={len(units):5}  own_text={own:,}  claimed={claimed:,}  "
                  f"width_ratio={claimed / max(1, own):.3f}  "
                  f"ranges/unit={n_ranges / max(1, len(units)):.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
