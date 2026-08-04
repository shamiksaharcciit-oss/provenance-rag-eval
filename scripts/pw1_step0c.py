"""PW-1 step 0c — the asymmetry measurement, plus §4.4's redefined clean-gold retention.

Descriptive. No arm, no p-value, no classification. Cache-only for the LLM, no embeddings.

§3a — the statistic, stated precisely. Reported per corpus per track:

    width = (claimed original-document surface, in characters, unioned per unit and summed)
            / (the unit's own size)

with the denominator given BOTH ways, because the two answer different questions and the earlier
0a figure used the second:
    per token  — the quantity §3a names: claimed chars per indexed token
    per char   — claimed chars per character of the unit's own text

§3b — the same statistic for the UNFORMATTED corpus, and the ratio of the two. The ratio of
ratios is the asymmetry a paired formatted-minus-unformatted comparison can actually see.

§4.4 — clean-query retention under two definitions of D:
    narrow  D = union of absorbed ranges                (the original instruction)
    wide    D = union of (claimed \\ tight) ranges       (absorbed AND inherited)
A gold span is clean if it does not intersect D; a query is clean if all of its spans are.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
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
from src.datasets import load_track_dataset  # noqa: E402
from src.index.embed import Embedder  # noqa: E402
from src.llm.client import LLMClient, build_llm  # noqa: E402
from src.pipeline import build_units  # noqa: E402
from src.pw1.tight_provenance import build_tight_units, excess_ranges, surface  # noqa: E402
from src.run import split_dev_test  # noqa: E402
from src.textutil import count_tokens, merge_ranges  # noqa: E402

ORIG = {"id": "orig256", "chunker": "naive",
        "params": {"chunk_tokens": 256, "overlap_frac": 0.0}}
FMT = {"id": "fmt256", "chunker": "formatted_naive",
       "params": {"chunk_tokens": 256, "overlap_frac": 0.0,
                  "reference_resolution": True, "dedup": True,
                  "right_size": True, "soft_target_tokens": 384}}


def _no_network(self, prompt, system):  # noqa: ANN001, ARG001
    raise RuntimeError("cache miss — step 0 is cache-only and must not call the API")


def width_stats(units) -> dict:
    """§3a. THREE distinct width statistics, named, because they differ materially.

    W_index_char  aggregate: total claimed surface / total own indexed characters.
                  This is the §3a statistic and the basis of the ratio of ratios.
    W_index_token aggregate: total claimed surface / total own indexed tokens.
    W_index_mean  the per-UNIT mean of (claimed / own chars). A mean of ratios, so it is not
                  the aggregate and is reported separately rather than conflated with it.

    W_cover (claimed / tight) is a fourth quantity and is computed in main(), because it needs
    the tight ranges. Any statement of the form "the width is 2.3x" must name which of these it
    refers to; they range from 2.11 to 2.36 on these corpora.
    """
    claimed = sum(surface(u.source_ranges) for u in units)
    own_chars = sum(len(u.text) for u in units)
    own_tokens = sum(count_tokens(u.text) for u in units)
    per_unit = [surface(u.source_ranges) / max(1, len(u.text)) for u in units]
    ratios = sorted(((r, len(u.text)) for r, u in zip(per_unit, units)), key=lambda x: -x[0])
    dec = max(1, len(ratios) // 10)
    return {"n_units": len(units), "claimed_chars": claimed,
            "own_chars": own_chars, "own_tokens": own_tokens,
            # W_unit: mean claimed surface per unit, ABSOLUTE. The statistic that matches the
            # paper's section 11 mechanism — at fixed k, a unit's chance of overlapping gold
            # scales with the surface IT claims, not with a ratio to its own length.
            "W_unit": round(claimed / max(1, len(units)), 1),
            "own_chars_per_unit": round(own_chars / max(1, len(units)), 1),
            # Diagnostic for why W_index_mean is not the mechanism: it is dominated by tiny
            # trailing chunks that inherit a whole segment's ranges and are not preferentially
            # retrieved. Same mean-of-ratios pathology as blurb_to_child_ratio in v1.5.
            "top_decile_ratio_mean": round(sum(r for r, _ in ratios[:dec]) / dec, 2),
            "top_decile_own_chars_mean": round(sum(c for _, c in ratios[:dec]) / dec, 1),
            "W_index_char": round(claimed / max(1, own_chars), 4),
            "W_index_token": round(claimed / max(1, own_tokens), 4),
            "W_index_mean": round(sum(per_unit) / max(1, len(per_unit)), 4),
            "ranges_per_unit": round(sum(len(u.source_ranges) for u in units)
                                     / max(1, len(units)), 2)}


def clean_queries(queries, d_by_doc: dict[str, list[tuple[int, int]]]) -> tuple[int, int]:
    """(clean, total) — a query is clean iff none of its gold spans intersects D."""
    clean = 0
    for q in queries:
        ok = True
        for g in q.gold_spans:
            for s, e in d_by_doc.get(g.doc_id, ()):
                if min(e, g.end_char) > max(s, g.start_char):
                    ok = False
                    break
            if not ok:
                break
        clean += ok
    return clean, len(queries)


def main() -> int:
    LLMClient._call_provider = _no_network
    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    cfg["llm"]["provider"] = "anthropic"

    report = {"analysis": "PW-1 step 0c",
              "computed_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "kind": "descriptive — properties of the corpora and gold set; no outcome computed",
              "width_statistic": "union of a unit's source_ranges in original-document "
                                 "characters, summed over units, divided by the units' own size "
                                 "(reported per own token and per own char)",
              "tracks": {}}

    for track in ("A", "B"):
        tcfg_raw = C.load_track(track)
        tm = tcfg_raw.get("params", {}).get("llm_model")
        tcfg = C.deep_merge(cfg, {"llm": {"model": tm}}) if tm else cfg
        dataset = load_track_dataset(tcfg_raw, tcfg["seed"])
        dev_frac = tcfg_raw.get("params", {}).get("dev_fraction")
        dev_frac = dev_frac if dev_frac is not None else tcfg.get("sweep", {}).get("dev_fraction", 0.2)
        _dev, test_q = split_dev_test(dataset, dev_frac, tcfg["seed"])
        ctx = ChunkContext(embedder=Embedder(tcfg, cache_root=tcfg["_cache_root"]),
                           llm=build_llm(tcfg), config=tcfg)
        print(f"\n=== Track {track} — {len(dataset.documents)} docs, "
              f"{len(test_q)} test queries ===")

        # ---- §3a / §3b: width for both corpora, and the ratio of ratios ----
        w = {}
        for tag, cond in (("orig256", ORIG), ("fmt256", FMT)):
            w[tag] = width_stats(build_units(build_chunker(cond, ctx), dataset))
            s = w[tag]
            print(f"  {tag:8} units={s['n_units']:5}  claimed={s['claimed_chars']:,}  "
                  f"W_index_char={s['W_index_char']:.4f}  W_index_token={s['W_index_token']:.4f}  "
                  f"W_index_mean={s['W_index_mean']:.4f}  ranges/unit={s['ranges_per_unit']}")
        rr_tok = w["fmt256"]["W_index_token"] / w["orig256"]["W_index_token"]
        rr_chr = w["fmt256"]["W_index_char"] / w["orig256"]["W_index_char"]
        rr_mean = w["fmt256"]["W_index_mean"] / w["orig256"]["W_index_mean"]
        rr_unit = w["fmt256"]["W_unit"] / w["orig256"]["W_unit"]
        print(f"  RATIO OF RATIOS (fmt / orig):  W_unit {rr_unit:.4f} <- MECHANISM-MATCHED   "
              f"W_index_char {rr_chr:.4f}   W_index_token {rr_tok:.4f}   "
              f"W_index_mean {rr_mean:.4f}")
        print(f"    size-match holds: own chars per unit "
              f"{w['orig256']['own_chars_per_unit']:.1f} vs {w['fmt256']['own_chars_per_unit']:.1f} "
              f"({abs(w['fmt256']['own_chars_per_unit']-w['orig256']['own_chars_per_unit'])/w['orig256']['own_chars_per_unit']:.2%})")
        print(f"    W_index_mean is inflated by small units: fmt256 top decile mean ratio "
              f"{w['fmt256']['top_decile_ratio_mean']} on units of "
              f"{w['fmt256']['top_decile_own_chars_mean']:.0f} chars")

        # ---- tight provenance: decompose the excess ----
        tights = [tu for d in dataset.documents
                  for tu in build_tight_units(d, FMT["params"], ctx)]
        excess = {t.unit_id: excess_ranges(t.claimed, t.tight) for t in tights}
        # PER-CHUNK sums: the right denominator for a per-unit width statistic, but they
        # double-count any sentence a chunk boundary splits, so they are NOT corpus surface.
        per_chunk = {"claimed": sum(surface(t.claimed) for t in tights),
                     "tight": sum(surface(t.tight) for t in tights),
                     "absorbed": sum(surface(t.absorbed) for t in tights),
                     "excess": sum(surface(v) for v in excess.values())}
        # CORPUS-LEVEL unions: the canonical surface figures. Every character counted once.
        def _union(key):
            by: dict[str, list] = {}
            for t in tights:
                by.setdefault(t.doc_id, []).extend(
                    excess[t.unit_id] if key == "excess" else getattr(t, key))
            return sum(surface(v) for v in by.values())
        corpus = {k: _union(k) for k in ("claimed", "tight", "absorbed")}
        # NOTE ON DENOMINATORS. Width is a PER-UNIT property, so the decomposition is reported
        # per chunk. `excess` has no meaningful corpus-level union: a sentence that is excess for
        # chunk 1 is own text for chunk 2, so unioning excess across chunks approaches the whole
        # corpus (96.6% on Track A) and measures nothing. Absorbed IS a corpus-level surface and
        # is reported as a per-document union.
        inh = 1 - per_chunk["absorbed"] / max(1, per_chunk["excess"])
        print(f"  fmt256 over {len(tights)} chunks — per-chunk decomposition (width is per-unit)")
        print(f"    claimed {per_chunk['claimed']:,}   tight {per_chunk['tight']:,}   "
              f"excess {per_chunk['excess']:,} = "
              f"{per_chunk['excess']/max(1,per_chunk['claimed']):.2%} of claimed")
        print(f"    of that excess: absorbed {per_chunk['absorbed']:,} "
              f"({1-inh:.2%})  inheritance {inh:.2%}")
        print(f"    absorbed surface, corpus union (canonical): {corpus['absorbed']:,}")
        # W_cover: claimed surface per character of surface the unit ACTUALLY covers. This is
        # the quantity the excess share implies — 1/(1-excess_share) — and it is NOT W_index.
        w_cover = per_chunk["claimed"] / max(1, per_chunk["tight"])
        print(f"    W_cover (claimed / tight) = {w_cover:.4f}   "
              f"[= 1/(1-{per_chunk['excess']/max(1,per_chunk['claimed']):.4f}); "
              f"orig256 W_cover = 1.0000 by construction]")
        claimed_s, tight_s = per_chunk["claimed"], per_chunk["tight"]
        absorbed_s, excess_s = per_chunk["absorbed"], per_chunk["excess"]

        # ---- §4.4: clean-query retention under narrow and wide D ----
        narrow_d: dict[str, list] = {}
        wide_d: dict[str, list] = {}
        for t in tights:
            narrow_d.setdefault(t.doc_id, []).extend(t.absorbed)
            wide_d.setdefault(t.doc_id, []).extend(excess[t.unit_id])
        narrow_d = {k: merge_ranges(v) for k, v in narrow_d.items()}
        wide_d = {k: merge_ranges(v) for k, v in wide_d.items()}
        cn, tot = clean_queries(test_q, narrow_d)
        cw, _ = clean_queries(test_q, wide_d)
        print(f"  clean-query retention: narrow D (absorbed only) {cn}/{tot} = {cn/tot:.1%}"
              f"   {'PASS' if cn/tot >= 0.60 else 'BELOW 60% GATE'}")
        print(f"                         wide   D (absorbed+inherited) {cw}/{tot} = {cw/tot:.1%}"
              f"   {'PASS' if cw/tot >= 0.60 else 'BELOW 60% GATE'}")

        report["tracks"][track] = {
            "n_docs": len(dataset.documents), "n_test_queries": tot,
            "width": w,
            "ratio_of_ratios": {"W_unit_MECHANISM_MATCHED": round(rr_unit, 4),
                                "W_index_char": round(rr_chr, 4),
                                "W_index_token": round(rr_tok, 4),
                                "W_index_mean": round(rr_mean, 4),
                                "W_cover": round(w_cover, 4),
                                "_note": "orig256 has W_index_char = W_index_token/6.8877 = "
                                         "W_cover = 1.0000 by construction, so each ratio of "
                                         "ratios equals the fmt256 value itself"},
            "W_cover_fmt256": round(w_cover, 4),
            "fmt256_decomposition_per_chunk": {
                **per_chunk,
                "excess_share_of_claimed": round(excess_s / max(1, claimed_s), 4),
                "absorbed_share_of_excess": round(absorbed_s / max(1, excess_s), 4),
                "inheritance_share_of_excess": round(1 - absorbed_s / max(1, excess_s), 4),
                "_note": "per-chunk sums. Width is a per-unit property, so this is the correct "
                         "denominator. `excess` has NO meaningful corpus-level union: a sentence "
                         "that is excess for one chunk is own text for the next, so unioning it "
                         "approaches the whole corpus and measures nothing."},
            "absorbed_surface_corpus_union": {
                "absorbed": corpus["absorbed"], "claimed": corpus["claimed"],
                "tight": corpus["tight"],
                "_note": "per-document unions; the canonical absorbed surface figure"},
            "clean_query_retention": {
                "narrow_D_absorbed_only": {"clean": cn, "total": tot,
                                           "share": round(cn / tot, 4),
                                           "passes_60pct_gate": cn / tot >= 0.60},
                "wide_D_absorbed_plus_inherited": {"clean": cw, "total": tot,
                                                   "share": round(cw / tot, 4),
                                                   "passes_60pct_gate": cw / tot >= 0.60}},
        }

    out = ROOT / "results_pw1" / "step0.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
