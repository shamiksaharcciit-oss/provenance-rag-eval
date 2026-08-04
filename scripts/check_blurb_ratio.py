"""Diagnose the C2 `blurb_to_child_ratio` anomaly (handoff 2026-07-29 §4).

Reported values do not scale with child size, and Track A INVERTS:

    Track A  @128 0.5669  ->  @256 0.9711   (nearly doubles; should roughly halve)
    Track B  @128 0.5609  ->  @256 0.5226   (falls 7%; should roughly halve)

The question that matters is whether the blurb is ATTACHED differently at the two child
sizes — if so, §2's "blurbs and best-child ranking are partial substitutes" reading is
measuring a harness artifact rather than a property of the corpus.

Runs CACHE-ONLY: `_call_provider` is replaced with a raiser, so this can consume no tokens
and cannot mint a blurb differing from the one the run used. A cache miss is a hard error,
not a silent live call.
"""
from __future__ import annotations

import os
import statistics
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
from src.datasets import load_track_dataset  # noqa: E402
from src.index.embed import Embedder  # noqa: E402
from src.llm.client import LLMClient, build_llm  # noqa: E402
from src.pipeline import build_units  # noqa: E402
from src.run import NO_SWEEP_PARAMS  # noqa: E402
from src.smalltobig.chunker import build_children  # noqa: E402

SIZES = (128, 256)


def _no_network(self, prompt, system):  # noqa: ANN001, ARG001
    raise RuntimeError("cache miss — this diagnostic is cache-only and must not call the API")


def ratios(children) -> dict:
    """Both estimators, plus the quantity that separates them."""
    pairs = [(c.meta.get("blurb_tokens", 0), c.meta.get("child_text_tokens", 0))
             for c in children]
    pairs = [(b, t) for b, t in pairs if t > 0]
    blurb = [b for b, _ in pairs]
    text = [t for _, t in pairs]
    return {
        "n_children": len(pairs),
        "mean_of_ratios": round(sum(b / t for b, t in pairs) / len(pairs), 4),
        "ratio_of_means": round(statistics.mean(blurb) / statistics.mean(text), 4),
        "mean_blurb_tokens": round(statistics.mean(blurb), 2),
        "mean_child_tokens": round(statistics.mean(text), 2),
        "min_child_tokens": min(text),
        "share_under_32_tokens": round(sum(t < 32 for t in text) / len(text), 4),
    }


def main() -> int:
    LLMClient._call_provider = _no_network
    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    cfg["llm"]["provider"] = "anthropic"

    cond_cfg = C.load_condition("C2")
    if "C2" in NO_SWEEP_PARAMS:
        cond_cfg["params"] = {**cond_cfg.get("params", {}), **NO_SWEEP_PARAMS["C2"]}

    verdicts = []
    for track in ("A", "B"):
        tcfg_raw = C.load_track(track)
        tm = tcfg_raw.get("params", {}).get("llm_model")
        tcfg = C.deep_merge(cfg, {"llm": {"model": tm}}) if tm else cfg
        dataset = load_track_dataset(tcfg_raw, tcfg["seed"])
        embedder = Embedder(tcfg, cache_root=tcfg["_cache_root"])
        ctx = ChunkContext(embedder=embedder, llm=build_llm(tcfg), config=tcfg)
        parents = build_units(build_chunker(cond_cfg, ctx), dataset)
        blurbs = {u.unit_id: u.meta.get("blurb", "") for u in parents if u.meta.get("blurb")}

        print(f"\n=== Track {track} — C2, {len(parents)} parents, {len(blurbs)} with blurbs ===")
        prev = None
        for size in SIZES:
            children, _ = build_children(parents, size, "C2", blurbs=blurbs or None)
            r = ratios(children)
            print(f"  @{size}: mean_of_ratios={r['mean_of_ratios']:.4f}  "
                  f"ratio_of_means={r['ratio_of_means']:.4f}  "
                  f"blurb={r['mean_blurb_tokens']:.1f}tok  child={r['mean_child_tokens']:.1f}tok  "
                  f"min_child={r['min_child_tokens']}  <32tok={r['share_under_32_tokens']:.1%}")
            # The attachment test is per PARENT, not per child: mean blurb tokens per child is
            # a weighted average over a child population that legitimately changes with size,
            # so comparing it answers a different question.
            by_parent = {}
            for c in children:
                by_parent.setdefault(c.meta["parent_id"], set()).add(c.meta["blurb_tokens"])
            multi = {p: v for p, v in by_parent.items() if len(v) > 1}
            assert not multi, f"a parent's children disagree on blurb length: {list(multi)[:3]}"
            attach = {p: next(iter(v)) for p, v in by_parent.items()}
            if prev:
                print(f"      128->256:  mean_of_ratios x{r['mean_of_ratios']/prev['mean_of_ratios']:.2f}"
                      f"   ratio_of_means x{r['ratio_of_means']/prev['ratio_of_means']:.2f}"
                      f"   (a length-invariant blurb predicts ~x0.5)")
                same = attach == prev_attach
                verdicts.append((track, same))
                print("      per-parent blurb IDENTICAL at both sizes -> attachment is invariant; "
                      "the anomaly is in the ESTIMATOR" if same else
                      "      !! BLURB ATTACHMENT DIFFERS BY CHILD SIZE — the substitutes reading "
                      "would be measuring a harness artifact")
            prev, prev_attach = r, attach

    ok = all(same for _, same in verdicts)
    print("\nCONCLUSION: " + ("attachment invariant on both tracks; `blurb_to_child_ratio` is a "
                              "mean-of-ratios and is dominated by short remainder children"
                              if ok else "ATTACHMENT VARIES BY CHILD SIZE — investigate before "
                              "any interpretation rests on C2"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
