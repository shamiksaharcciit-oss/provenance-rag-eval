"""v1.9 §1 — arm inventories, by IMPORT rather than transcription.

Identity over assertion: `build_arm` is the same function object v1.6 ran and v1.7 re-ran.
`assert_builder_identity` checks that at runtime, so a future refactor that copies the builder
into a second place fails here instead of drifting quietly.

No embedder, no index, no encode anywhere in v1.9 (§1). Inventories are built with a null LLM
context for the deterministic arms and a cached LLM context for `F768`, exactly as v1.7 did;
`F768`'s formatter calls are served from `cache/llm` and a miss is a hard failure, not a spend.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

#: The primary pair plus the descriptive third (§1). Order is presentation order.
ARMS = ("F768", "U768", "U256")
PRIMARY_PAIR = ("F768", "U768")


def _v16_build_arm():
    from segment_size_sweep import build_arm
    return build_arm


def assert_builder_identity() -> None:
    """The builder v1.9 uses IS v1.6's, not a copy that happens to agree."""
    import segment_size_sweep as v16
    from v19 import arms as here

    assert here._v16_build_arm() is v16.build_arm, (
        "v1.9's arm builder is not the v1.6 object — a transcribed copy would be a second "
        "procedure for one quantity (A5b) and would drift the moment either file was touched")


class FormatterCacheMiss(RuntimeError):
    """A formatter LLM call was not served from cache. v1.9 spends nothing on inventories."""


def build_inventories(track: str, forbid_llm_spend: bool = True):
    """Return `{arm: (units, rungs, diag)}` for `ARMS` on `track`.

    With `forbid_llm_spend`, any formatter call that would reach the provider raises rather than
    spending. Inventory construction is not part of v1.9's call budget and must cost nothing.
    """
    from src import config as C
    from src.chunkers.base import ChunkContext
    from src.datasets import load_track_dataset
    from src.llm.client import LLMClient, build_llm
    import src.llm.client as LC

    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    cfg["llm"]["provider"] = "anthropic"
    traw = C.load_track(track)
    tm = traw.get("params", {}).get("llm_model")
    tcfg = C.deep_merge(cfg, {"llm": {"model": tm}}) if tm else cfg
    ds = load_track_dataset(traw, tcfg["seed"])
    llm = build_llm(tcfg)

    original = LC.LLMClient._call_provider
    if forbid_llm_spend:
        def _refuse(self, prompt, system):
            raise FormatterCacheMiss(
                "formatter LLM call missed the cache; v1.9 builds inventories from cache only")
        LC.LLMClient._call_provider = _refuse
    try:
        ctx_full = ChunkContext(embedder=None, llm=llm, config=tcfg)
        ctx_det = ChunkContext(embedder=None, llm=LLMClient(provider="none"), config=tcfg)
        build_arm = _v16_build_arm()
        return ds, tcfg, {a: build_arm(a, ds, ctx_full, ctx_det) for a in ARMS}
    finally:
        LC.LLMClient._call_provider = original


def test_queries(ds, tcfg, track: str):
    """The frozen test split — the same expression v1.6 and v1.7 used.

    Written with an explicit `is None` sentinel: Track B declares `dev_fraction = 0.0`, and a
    falsy-or default silently turns that into 0.2 and the split into 120 queries (v1.7 F5).
    """
    from src import config as C
    from src.run import split_dev_test

    traw = C.load_track(track)
    dev_frac = traw.get("params", {}).get("dev_fraction")
    if dev_frac is None:
        dev_frac = tcfg.get("sweep", {}).get("dev_fraction", 0.2)
    dev, test = split_dev_test(ds, dev_frac, tcfg["seed"])
    return dev, test
