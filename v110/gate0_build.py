"""v1.10 Gate 0 (§6) — the census, against real inputs and real acceptors. NO FRESH LLM CALL.

The four-instance rule applied in full: every acceptor this experiment depends on is exercised
against the actual corpora rather than a synthetic stand-in, because this plan's author has been
wrong against an uncensused domain repeatedly.

  * C2 blurb cache coverage, per track, per chunk — a miss is a STOP, never a top-up;
  * blurb token-length distribution — the padding matcher's real domain;
  * the padding pool's content-word overlap against both corpora AND both query sets;
  * the base inventory identified and bound by content hash;
  * unattributed-range handling exercised against the REAL scorer on REAL C2 units;
  * all three arms built with `llm.calls == 0` asserted per stage.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "v110" / "results_gate0"
TRACKS = ("A", "B")
def _v16_u768(ds, ctx):
    """v1.6's U768 arm, rebuilt, to bind the base inventory by identity rather than by claim."""
    import sys as _s
    _s.path.insert(0, str(ROOT / "scripts"))
    from segment_size_sweep import build_arm
    return build_arm("U768", ds, ctx, ctx)[0]


C2_PARAMS = {"base": "naive", "chunk_tokens": 768, "overlap_frac": 0.0, "blurb_max_sentences": 2}


def census(track: str) -> dict:
    import src.llm.client as LC
    from src import config as C
    from src.chunkers.base import ChunkContext
    from src.datasets import load_track_dataset
    from src.llm.client import build_llm
    from src.run import split_dev_test
    from src.score.provenance import ANY, is_hit
    from src.textutil import count_tokens
    from v110.arms import (assert_prepended_text_is_unattributed, build_base, build_contextual,
                           build_padded, inventory_hash, provenance_hash)

    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    cfg["llm"]["provider"] = "anthropic"
    traw = C.load_track(track)
    tm = traw.get("params", {}).get("llm_model")
    tcfg = C.deep_merge(cfg, {"llm": {"model": tm}}) if tm else cfg
    ds = load_track_dataset(traw, tcfg["seed"])
    llm = build_llm(tcfg)
    ctx = ChunkContext(embedder=None, llm=llm, config=tcfg)

    dev_frac = traw.get("params", {}).get("dev_fraction")
    if dev_frac is None:
        dev_frac = tcfg.get("sweep", {}).get("dev_fraction", 0.2)
    _dev, test = split_dev_test(ds, dev_frac, tcfg["seed"])

    calls_before = llm.calls
    U = build_base(ds, ctx)
    Cc = build_contextual(ds, ctx, C2_PARAMS)      # raises on any cache miss
    P = build_padded(U, Cc)
    fresh = llm.calls - calls_before
    assert fresh == 0, f"§0 VIOLATED: {fresh} fresh LLM calls during arm construction"

    blurbs = [count_tokens(u.meta["blurb"]) for u in Cc]
    rec_c = assert_prepended_text_is_unattributed(U, Cc, "C")
    rec_p = assert_prepended_text_is_unattributed(U, P, "P")

    # length match between P and C, per chunk — P is meaningless without it
    mismatch = [(a.unit_id, count_tokens(a.text), count_tokens(b.text))
                for a, b in zip(P, Cc) if count_tokens(a.text) != count_tokens(b.text)]

    # unattributed-range handling on REAL C2 units against the REAL scorer
    agree = disagree = 0
    by_doc: dict[str, list] = {}
    for u in U:
        by_doc.setdefault(u.doc_id, []).append(u)
    for q in test:
        for ub, uc, up in zip(U, Cc, P):
            hb = is_hit(ub, q, variant=ANY, min_overlap=1)
            hc = is_hit(uc, q, variant=ANY, min_overlap=1)
            hp = is_hit(up, q, variant=ANY, min_overlap=1)
            if hb == hc == hp:
                agree += 1
            else:
                disagree += 1

    return {"track": track, "n_docs": len(ds.documents), "n_test_queries": len(test),
            "fresh_llm_calls": fresh,
            "blurb_cache": {"units": len(Cc), "misses": 0, "cache_hits": llm.cache_hits,
                            "complete": True},
            "blurb_tokens": {"min": min(blurbs), "median": sorted(blurbs)[len(blurbs) // 2],
                             "max": max(blurbs), "total": sum(blurbs)},
            "base_inventory": {"units": len(U), "sha256": inventory_hash(U),
                               "provenance_sha256": provenance_hash(U),
                               "matches_v16_U768": provenance_hash(U) == provenance_hash(_v16_u768(ds, ctx)),
                               "identified_as": "naive chunk_tokens=768 overlap_frac=0.0 "
                                                "(C2's declared base; equals the C0 inventory)"},
            "contextual_provenance_sha256": provenance_hash(Cc),
            "padded_provenance_sha256": provenance_hash(P),
            "arms_share_one_segmentation": (provenance_hash(U) == provenance_hash(Cc)
                                            == provenance_hash(P)),
            "prepended": {"C": rec_c, "P": rec_p},
            "P_C_length_mismatches": mismatch,
            "unit_token_median": {
                "U": sorted(count_tokens(u.text) for u in U)[len(U) // 2],
                "P": sorted(count_tokens(u.text) for u in P)[len(P) // 2],
                "C": sorted(count_tokens(u.text) for u in Cc)[len(Cc) // 2]},
            "scorer_agreement": {"unit_query_pairs_agreeing": agree, "disagreeing": disagree,
                                 "_note": "U, P and C must score identically: prepended text "
                                          "carries no source_ranges (§2)"},
            "_corpus_texts": [d.text for d in ds.documents],
            "_query_texts": [q.text for q in ds.queries]}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    from v110.padding import assert_pool_fixed_point, pool_hash, pool_sentences

    cens = [census(t) for t in TRACKS]
    docs, qs = [], []
    for c in cens:
        docs += c.pop("_corpus_texts")
        qs += c.pop("_query_texts")
    vocab = assert_pool_fixed_point(docs, qs)   # PF-G1: a complete pass must be clean

    report = {"experiment": "v1.10-context-budget", "tracks": cens,
              "padding_pool": {"path": "v110/filler_pool.txt", "sha256": pool_hash(),
                               "n_sentences": len(pool_sentences()), **vocab},
              "total_fresh_llm_calls": sum(c["fresh_llm_calls"] for c in cens)}
    (OUT / "gate0_census.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    for c in cens:
        print(f"\n=== track {c['track']} ===")
        print(f"  docs {c['n_docs']}  test queries {c['n_test_queries']}  "
              f"FRESH LLM CALLS {c['fresh_llm_calls']}")
        print(f"  blurb cache: {c['blurb_cache']['units']} units, "
              f"{c['blurb_cache']['misses']} misses, complete={c['blurb_cache']['complete']}")
        print(f"  blurb tokens min/median/max: {c['blurb_tokens']['min']}/"
              f"{c['blurb_tokens']['median']}/{c['blurb_tokens']['max']}")
        print(f"  base inventory {c['base_inventory']['units']} units, "
              f"sha256 {c['base_inventory']['sha256'][:16]}")
        print(f"  arms share one segmentation (provenance hash): "
              f"{c['arms_share_one_segmentation']}")
        print(f"  base inventory == v1.6's U768 arm: {c['base_inventory']['matches_v16_U768']}")
        print(f"  unit tokens median U/P/C: {c['unit_token_median']['U']}/"
              f"{c['unit_token_median']['P']}/{c['unit_token_median']['C']}")
        print(f"  P vs C length mismatches: {len(c['P_C_length_mismatches'])}")
        print(f"  scorer agreement U=P=C: {c['scorer_agreement']['unit_query_pairs_agreeing']} "
              f"agree, {c['scorer_agreement']['disagreeing']} disagree")
    v = report["padding_pool"]
    print(f"\n=== padding pool ===")
    print(f"  sha256 {v['sha256'][:16]}  sentences {v['n_sentences']}  content words {v['pool_content_words']}")
    print(f"  QUERY-vocabulary overlap:  {v['n_overlap_queries']}  {v['overlap_with_queries']}")
    print(f"  CORPUS-vocabulary overlap: {v['n_overlap_corpus']} of {v['pool_content_words']} "
          f"(corpus has {v['corpus_content_words']} content words)")
    print(f"\nTOTAL FRESH LLM CALLS: {report['total_fresh_llm_calls']}")
    print(f"wrote {OUT/'gate0_census.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
